from decimal import Decimal
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db.models import Avg, Count, F, Q
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import payments
from .cart import Cart
from .emails import send_order_confirmation, send_order_received
from .forms import CheckoutForm, RegisterForm
from .models import (Category, Coupon, Product, Order, OrderItem,
                     Review, StockAlert, Subscriber, WishlistItem)


def _safe_next(request):
    """Return the POSTed 'next' path only if it points to our own site."""
    nxt = request.POST.get('next', '')
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return None


def home(request):
    categories = Category.objects.all()
    bestsellers = Product.objects.filter(is_active=True, is_bestseller=True)[:8]
    if not bestsellers:
        bestsellers = Product.objects.filter(is_active=True)[:8]
    return render(request, 'shop/home.html', {
        'categories': categories,
        'bestsellers': bestsellers,
    })


SORTS = {
    'price': ('price',),
    '-price': ('-price',),
    'new': ('-created_at',),
    'featured': ('-is_bestseller', '-created_at'),
}


def collection(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(is_active=True)

    sort = request.GET.get('sort', 'featured')
    if sort not in SORTS:
        sort = 'featured'
    products = products.order_by(*SORTS[sort])

    size = request.GET.get('size', '')
    if size:
        products = [p for p in products if size in p.size_list]

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    params = {'sort': sort}
    if size:
        params['size'] = size

    return render(request, 'shop/collection.html', {
        'category': category,
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'total_count': paginator.count,
        'base_qs': urlencode(params) + '&',
        'sort': sort,
        'size': size,
        'all_sizes': ['XS', 'S', 'M', 'L', 'XL'],
    })


def search(request):
    query = request.GET.get('q', '').strip()
    products = []
    if query:
        products = (Product.objects.filter(is_active=True)
                    .select_related('category')   # cards show the category name
                    .filter(Q(name__icontains=query) |
                            Q(description__icontains=query) |
                            Q(category__name__icontains=query)))
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'shop/search.html', {
        'query': query,
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'total_count': paginator.count,
        'base_qs': (urlencode({'q': query}) + '&') if query else '',
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related = (Product.objects.filter(category=product.category, is_active=True)
               .exclude(id=product.id)[:4])

    reviews = product.reviews.filter(approved=True)
    agg = reviews.aggregate(avg=Avg('rating'), n=Count('id'))

    # Recently viewed: show the previous ones, then remember this visit.
    recent_ids = [pid for pid in request.session.get('recent', [])
                  if pid != product.id]
    recent_map = {p.id: p for p in
                  Product.objects.filter(id__in=recent_ids, is_active=True)}
    recent = [recent_map[pid] for pid in recent_ids if pid in recent_map][:6]
    request.session['recent'] = ([product.id] + recent_ids)[:7]
    request.session.modified = True

    return render(request, 'shop/product.html', {
        'product': product,
        'related': related,
        'reviews': reviews,
        'avg_rating': agg['avg'] or 0,
        'avg_int': round(agg['avg']) if agg['avg'] else 0,
        'review_count': agg['n'],
        'recent': recent,
    })


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    size = request.POST.get('size') or (product.size_list[0] if product.size_list else '')
    try:
        quantity = max(1, int(request.POST.get('quantity', 1)))
    except (TypeError, ValueError):
        quantity = 1
    cart = Cart(request)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    # Stock check: what's already in the bag counts too.
    in_bag = sum(v['quantity'] for k, v in cart.cart.items()
                 if v['product_id'] == product.id)
    available = product.stock - in_bag
    if available <= 0:
        error = (f"“{product.name}” is sold out." if product.stock == 0
                 else f"All available pieces of “{product.name}” are already in your bag.")
        if is_ajax:
            return JsonResponse({'error': error}, status=400)
        messages.error(request, error)
        return redirect(product.get_absolute_url())
    if quantity > available:
        quantity = available
        messages.info(request, f"Only {available} left — we added all of them.")

    cart.add(product, size, quantity)
    if is_ajax:
        return JsonResponse({'count': len(cart), 'name': product.name, 'size': size})
    messages.success(request, f"Added “{product.name}” ({size}) to your bag.")
    if request.POST.get('next') == 'cart':
        return redirect('shop:cart')
    return redirect(product.get_absolute_url())


@require_POST
def cart_update(request, key):
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1
    cart = Cart(request)
    # Cap at the product's stock.
    item = cart.cart.get(key)
    if item and quantity > 0:
        product = Product.objects.filter(id=item['product_id']).first()
        if product and quantity > product.stock:
            quantity = product.stock
            messages.info(request, f"Only {product.stock} left of “{product.name}”.")
    cart.set_quantity(key, quantity)
    return redirect('shop:cart')


@require_POST
def cart_remove(request, key):
    Cart(request).remove(key)
    return redirect('shop:cart')


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'shop/cart.html', {
        'cart': cart,
        'free_threshold': settings.FREE_SHIPPING_THRESHOLD,
    })


def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.info(request, "Your bag is empty.")
        return redirect('shop:cart')

    region = request.POST.get('region', 'west') if request.method == 'POST' else 'west'

    # Logged-in customer: pre-fill from her latest order (saved address).
    initial = {}
    if request.method != 'POST' and request.user.is_authenticated:
        last = Order.objects.filter(user=request.user).first()
        if last:
            initial = {f: getattr(last, f) for f in
                       ('full_name', 'email', 'phone', 'address', 'city',
                        'postcode', 'state', 'region')}
            region = last.region
        else:
            initial = {'email': request.user.email}
    form = CheckoutForm(request.POST or None, initial=initial)

    if request.method == 'POST':
        if form.is_valid():
            # Last stock check — someone may have bought the piece meanwhile.
            for row in cart:
                if row['quantity'] > row['product'].stock:
                    messages.error(
                        request,
                        f"Sorry — only {row['product'].stock} of "
                        f"“{row['product'].name}” left. Please adjust your bag.")
                    return redirect('shop:cart')

            coupon = cart.coupon
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.subtotal = cart.subtotal
            order.discount = cart.discount
            order.coupon_code = coupon.code if coupon else ''
            order.shipping = cart.shipping(order.region)
            order.total = cart.total(order.region)
            order.status = 'pending'
            order.save()
            for row in cart:
                OrderItem.objects.create(
                    order=order,
                    product=row['product'],
                    name=row['product'].name,
                    price=row['price'],
                    size=row['size'],
                    quantity=row['quantity'],
                )
                # Reduce stock (F() avoids race conditions). Reserved even
                # while payment is pending; admin can cancel + restock.
                Product.objects.filter(id=row['product'].id).update(
                    stock=F('stock') - row['quantity'])
            cart.remove_coupon()
            cart.clear()

            if payments.enabled():
                url, billcode = payments.create_bill(order)
                if url:
                    order.payment_ref = billcode
                    order.save()
                    return redirect(url)   # customer pays on the gateway page
                messages.error(request, "We couldn't reach the payment gateway. "
                                        "Your order is saved — press Pay Now to try again.")
                return redirect('shop:order_done', token=order.token)

            # Bank-transfer mode: keep the order Pending, email how to pay.
            # The owner marks it PAID in the admin once the money arrives.
            if payments.manual_mode():
                send_order_received(order)
                return redirect('shop:order_done', token=order.token)

            # Demo mode (no gateway keys set): mark paid straight away.
            _mark_paid(order)
            return redirect('shop:order_done', token=order.token)
        messages.error(request, "Please check the highlighted fields below.")

    return render(request, 'shop/checkout.html', {
        'cart': cart,
        'form': form,
        'region': region,
        'shipping': cart.shipping(region),
        'total': cart.total(region),
        'payment_choices': [c for c in Order.PAYMENT_CHOICES
                            if c[0] != 'transfer'],
        'shipping_west': settings.SHIPPING_WEST,
        'shipping_east': settings.SHIPPING_EAST,
        'payments_enabled': payments.enabled(),
        'manual_payment': payments.manual_mode(),
    })


def _mark_paid(order):
    """Set the order to paid (once) and send the confirmation email."""
    if order.status == 'paid':
        return
    order.status = 'paid'
    order.save()
    send_order_confirmation(order)


def order_done(request, token):
    order = get_object_or_404(Order, token=token)
    return render(request, 'shop/order_done.html', {
        'order': order,
        'payments_enabled': payments.enabled(),
        'manual_payment': payments.manual_mode(),
    })


@require_POST
def payment_start(request, token):
    """Pay Now (retry) for a pending order — creates a fresh gateway bill."""
    order = get_object_or_404(Order, token=token, status='pending')
    url, billcode = payments.create_bill(order)
    if url:
        order.payment_ref = billcode
        order.save()
        return redirect(url)
    messages.error(request, "Payment gateway unreachable — please try again in a moment.")
    return redirect('shop:order_done', token=order.token)


def payment_return(request):
    """Customer lands here after the gateway page. Verify, then show the order."""
    order = get_object_or_404(Order, token=request.GET.get('order_id', ''))
    if (order.status == 'pending' and request.GET.get('status_id') == '1'
            and payments.bill_paid(order.payment_ref)):
        _mark_paid(order)
    return redirect('shop:order_done', token=order.token)


@csrf_exempt
@require_POST
def payment_callback(request):
    """Server-to-server notification from toyyibPay (works even if the
    customer closes the browser). CSRF exempt: the gateway can't send a token;
    we authenticate by matching our secret order token + bill code instead."""
    try:
        order = Order.objects.get(token=request.POST.get('order_id', ''),
                                  payment_ref=request.POST.get('billcode', ''))
    except Order.DoesNotExist:
        return HttpResponse('not found', status=404)
    # Never trust the POSTed status alone — confirm with toyyibPay's API,
    # otherwise a customer could forge this call and skip paying.
    if (request.POST.get('status') == '1' and order.status == 'pending'
            and payments.bill_paid(order.payment_ref)):
        _mark_paid(order)
    return HttpResponse('OK')


@require_POST
def coupon_apply(request):
    code = request.POST.get('code', '').strip().upper()
    cart = Cart(request)
    if not code:
        messages.error(request, "Please type a discount code.")
        return redirect('shop:cart')
    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        messages.error(request, f"Code “{code}” was not found.")
        return redirect('shop:cart')
    ok, reason = coupon.check_valid(cart.subtotal)
    if not ok:
        messages.error(request, reason)
        return redirect('shop:cart')
    cart.set_coupon(coupon.code)
    messages.success(request, f"Code {coupon.code} applied — you save "
                              f"RM {coupon.discount_for(cart.subtotal):.2f}.")
    return redirect('shop:cart')


@require_POST
def coupon_remove(request):
    Cart(request).remove_coupon()
    messages.info(request, "Discount code removed.")
    return redirect('shop:cart')


def track(request):
    """Find an order by number + email. POST keeps the email out of the URL."""
    error = None
    if request.method == 'POST':
        number = request.POST.get('number', '').strip().lstrip('#')
        email = request.POST.get('email', '').strip()
        try:
            order = Order.objects.get(id=int(number), email__iexact=email)
            return redirect('shop:order_done', token=order.token)
        except (ValueError, Order.DoesNotExist):
            error = ("No order found with that number and email. "
                     "Please check both and try again.")
    return render(request, 'shop/track.html', {'error': error})


def info_shipping(request):
    return render(request, 'shop/info_shipping.html', {
        'shipping_west': settings.SHIPPING_WEST,
        'shipping_east': settings.SHIPPING_EAST,
    })


def info_size_guide(request):
    return render(request, 'shop/info_size_guide.html')


def info_about(request):
    return render(request, 'shop/info_about.html')


def info_privacy(request):
    return render(request, 'shop/info_privacy.html')


def robots_txt(request):
    """Tell search engines what to index (and where the sitemap is)."""
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /cart/",
        "Disallow: /checkout/",
        "Disallow: /order/",
        "Disallow: /payment/",
        "Disallow: /coupon/",
        "Disallow: /wishlist/",
        "Disallow: /search/",
        f"Sitemap: {settings.SITE_URL.rstrip('/')}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@require_POST
def review_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    # Honeypot: real customers never fill this hidden field — bots do.
    if request.POST.get('website'):
        return redirect(product.get_absolute_url())
    name = request.POST.get('name', '').strip()
    comment = request.POST.get('comment', '').strip()
    try:
        rating = int(request.POST.get('rating', 0))
    except (TypeError, ValueError):
        rating = 0
    if not name or not comment or rating not in range(1, 6):
        messages.error(request, "Please fill in your name, a rating, and your review.")
    else:
        Review.objects.create(product=product, name=name,
                              rating=rating, comment=comment)
        messages.success(request, "Thank you! Your review will appear "
                                  "once we've approved it.")
    return redirect(product.get_absolute_url())


@require_POST
def wishlist_toggle(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    if request.user.is_authenticated:
        # Saved to the account — survives any browser or device.
        item, created = WishlistItem.objects.get_or_create(
            user=request.user, product=product)
        if not created:
            item.delete()
        added = created
        count = WishlistItem.objects.filter(user=request.user).count()
    else:
        wishlist = request.session.get('wishlist', [])
        if product.id in wishlist:
            wishlist.remove(product.id)
            added = False
        else:
            wishlist.append(product.id)
            added = True
        request.session['wishlist'] = wishlist
        count = len(wishlist)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'added': added, 'count': count,
                             'name': product.name})
    messages.success(request, f"“{product.name}” "
                              f"{'saved to' if added else 'removed from'} your wishlist.")
    return redirect(_safe_next(request) or product.get_absolute_url())


def wishlist_page(request):
    if request.user.is_authenticated:
        products = [i.product for i in
                    WishlistItem.objects.filter(user=request.user,
                                                product__is_active=True)
                                        .select_related('product__category')]
    else:
        ids = request.session.get('wishlist', [])
        found = {p.id: p for p in
                 Product.objects.filter(id__in=ids, is_active=True)
                                .select_related('category')}
        products = [found[pid] for pid in ids if pid in found]
    return render(request, 'shop/wishlist.html', {'products': products})


def _merge_session_wishlist(request, user):
    """Move the guest (session) wishlist into the account after login."""
    ids = request.session.pop('wishlist', [])
    for product in Product.objects.filter(id__in=ids, is_active=True):
        WishlistItem.objects.get_or_create(user=user, product=product)


def register(request):
    if request.user.is_authenticated:
        return redirect('shop:account')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        user = User.objects.create_user(username=email, email=email,
                                        password=form.cleaned_data['password1'])
        auth_login(request, user)
        _merge_session_wishlist(request, user)
        messages.success(request, "Welcome to Méiyì! Your account is ready.")
        return redirect(_safe_next(request) or 'shop:account')
    return render(request, 'shop/register.html', {'form': form})


class MeiyiLoginView(LoginView):
    template_name = 'shop/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        _merge_session_wishlist(self.request, self.request.user)
        return response


@login_required
def account(request):
    orders = (Order.objects.filter(user=request.user)
                           .prefetch_related('items'))
    return render(request, 'shop/account.html', {'orders': orders})


@require_POST
def order_cancel(request, token):
    """Customer cancels her own order while it is still Pending (unpaid)."""
    order = get_object_or_404(Order, token=token)
    if order.status == 'pending':
        for item in order.items.all():
            if item.product_id:
                Product.objects.filter(id=item.product_id).update(
                    stock=F('stock') + item.quantity)
        order.status = 'cancelled'
        order.save()
        messages.success(request, "Your order was cancelled — nothing to pay.")
    return redirect('shop:order_done', token=order.token)


@require_POST
def stock_notify(request, product_id):
    """'Email me when it's back' form on a sold-out product page."""
    if request.POST.get('website'):          # honeypot — bots fill this
        return redirect('shop:home')
    product = get_object_or_404(Product, id=product_id, is_active=True)
    email = request.POST.get('email', '').strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Please enter a valid email address.")
        return redirect(product.get_absolute_url())
    StockAlert.objects.get_or_create(product=product, email=email)
    messages.success(request, "Noted! We'll email you the moment it's back. 🌸")
    return redirect(product.get_absolute_url())


@require_POST
def newsletter_signup(request):
    # Honeypot: silently drop bot submissions.
    if request.POST.get('website'):
        return redirect('shop:home')
    email = request.POST.get('email', '').strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Please enter a valid email address.")
    else:
        _, created = Subscriber.objects.get_or_create(email=email)
        messages.success(request, "Welcome to the Méiyì list! 🌸" if created
                         else "You're already on our list — thank you!")
    nxt = _safe_next(request)
    return redirect(nxt) if nxt else redirect('shop:home')
