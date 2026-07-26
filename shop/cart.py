"""Simple session-based cart. No login needed to shop."""
from decimal import Decimal
from django.conf import settings
from .models import Product

CART_SESSION_KEY = 'cart'
COUPON_SESSION_KEY = 'coupon'


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_KEY)
        if cart is None:
            cart = self.session[CART_SESSION_KEY] = {}
        self.cart = cart

    def _key(self, product_id, size):
        # One line per product+size combination.
        return f"{product_id}:{size}"

    def add(self, product, size, quantity=1):
        key = self._key(product.id, size)
        if key in self.cart:
            self.cart[key]['quantity'] += quantity
        else:
            self.cart[key] = {
                'product_id': product.id,
                'size': size,
                'quantity': quantity,
                'price': str(product.price),
            }
        self.save()

    def set_quantity(self, key, quantity):
        if key in self.cart:
            if quantity > 0:
                self.cart[key]['quantity'] = quantity
            else:
                self.remove(key)
            self.save()

    def remove(self, key):
        if key in self.cart:
            del self.cart[key]
            self.save()

    def clear(self):
        self.session[CART_SESSION_KEY] = {}
        self.cart = self.session[CART_SESSION_KEY]
        self.save()

    def save(self):
        self.session.modified = True

    def __iter__(self):
        """Yield rich rows joined with live Product data."""
        product_ids = [v['product_id'] for v in self.cart.values()]
        products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
        for key, item in self.cart.items():
            product = products.get(item['product_id'])
            if not product:
                continue
            price = Decimal(item['price'])
            yield {
                'key': key,
                'product': product,
                'size': item['size'],
                'quantity': item['quantity'],
                'price': price,
                'line_total': price * item['quantity'],
            }

    def __len__(self):
        return sum(v['quantity'] for v in self.cart.values())

    @property
    def subtotal(self):
        return sum((Decimal(v['price']) * v['quantity'] for v in self.cart.values()),
                   Decimal('0'))

    @property
    def coupon(self):
        """The applied Coupon, or None if missing/invalid for this bag."""
        code = self.session.get(COUPON_SESSION_KEY)
        if not code:
            return None
        from .models import Coupon
        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return None
        ok, _ = coupon.check_valid(self.subtotal)
        return coupon if ok else None

    def set_coupon(self, code):
        self.session[COUPON_SESSION_KEY] = code
        self.save()

    def remove_coupon(self):
        self.session.pop(COUPON_SESSION_KEY, None)
        self.save()

    @property
    def discount(self):
        coupon = self.coupon
        return coupon.discount_for(self.subtotal) if coupon else Decimal('0')

    def shipping(self, region='west'):
        if self.subtotal >= settings.FREE_SHIPPING_THRESHOLD or self.subtotal == 0:
            return Decimal('0')
        return Decimal(settings.SHIPPING_EAST if region == 'east' else settings.SHIPPING_WEST)

    def total(self, region='west'):
        return self.subtotal - self.discount + self.shipping(region)

    @property
    def amount_to_free_shipping(self):
        gap = Decimal(settings.FREE_SHIPPING_THRESHOLD) - self.subtotal
        return gap if gap > 0 else Decimal('0')
