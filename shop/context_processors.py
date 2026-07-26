from django.conf import settings
from .cart import Cart
from .models import Category, WishlistItem


def cart_summary(request):
    """Globals available in every template (navbar + footer)."""
    cart = Cart(request)
    if request.user.is_authenticated:
        wishlist_ids = list(WishlistItem.objects.filter(user=request.user)
                                        .values_list('product_id', flat=True))
    else:
        wishlist_ids = request.session.get('wishlist', [])
    return {
        'cart_count': len(cart),
        'cart_subtotal': cart.subtotal,
        'categories': Category.objects.all(),
        'FREE_SHIPPING_THRESHOLD': settings.FREE_SHIPPING_THRESHOLD,
        'WHATSAPP_NUMBER': settings.WHATSAPP_NUMBER,
        'wishlist_ids': wishlist_ids,
        'wishlist_count': len(wishlist_ids),
    }
