import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


def generate_order_token():
    """Random, unguessable id used in the order URL (keeps orders private)."""
    return secrets.token_urlsafe(16)


def unique_slug(instance, name):
    """Slug from name; adds -2, -3… if another row already uses it."""
    base = slugify(name)
    slug, n = base, 2
    others = type(instance).objects.exclude(pk=instance.pk)
    while others.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Category(models.Model):
    """A curated collection, e.g. Modern/Casual, Classic Silk, Festive/CNY."""
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    tagline = models.CharField(max_length=120, blank=True,
                               help_text="Short line shown on the collection card.")
    # Use an uploaded image OR paste an external URL (handy for demo photos).
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    image_url = models.URLField(blank=True,
                                help_text="Used only if no image is uploaded.")
    order = models.PositiveIntegerField(default=0, help_text="Lower shows first.")

    class Meta:
        verbose_name_plural = "categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('shop:collection', args=[self.slug])

    @property
    def cover(self):
        if self.image:
            return self.image.url
        return self.image_url


class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products',
                                 on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2,
                                help_text="Price in MYR.")
    compare_at_price = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True,
        help_text="Optional 'was' price to show a discount.")
    description = models.TextField(blank=True)
    # Comma-separated sizes, e.g. "XS,S,M,L". Simple and easy to edit.
    sizes = models.CharField(max_length=60, default="XS,S,M,L",
                             help_text="Comma separated, e.g. XS,S,M,L")
    # Two images give the homepage hover image-swap effect.
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_url = models.URLField(blank=True, help_text="Main image (if not uploaded).")
    hover_image_url = models.URLField(blank=True, help_text="Second image shown on hover.")
    is_bestseller = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(
        default=10, help_text="Pieces available. 0 shows Sold Out.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('shop:product', args=[self.slug])

    @property
    def cover(self):
        if self.image:
            return self.image.url
        return self.image_url

    @property
    def hover(self):
        return self.hover_image_url or self.cover

    @property
    def size_list(self):
        return [s.strip() for s in self.sizes.split(',') if s.strip()]

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def low_stock(self):
        return 0 < self.stock <= 3

    @property
    def on_sale(self):
        return self.compare_at_price and self.compare_at_price > self.price

    @property
    def discount_percent(self):
        if not self.on_sale:
            return 0
        return round((1 - self.price / self.compare_at_price) * 100)


class ProductImage(models.Model):
    """Extra gallery images for the product detail page."""
    product = models.ForeignKey(Product, related_name='gallery',
                                on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_url = models.URLField(blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"

    @property
    def src(self):
        if self.image:
            return self.image.url
        return self.image_url


class Order(models.Model):
    REGION_CHOICES = [
        ('west', 'West Malaysia'),
        ('east', 'East Malaysia (Sabah & Sarawak)'),
    ]
    PAYMENT_CHOICES = [
        ('fpx', 'FPX Online Banking'),
        ('grabpay', 'GrabPay'),
        ('card', 'Credit / Debit Card'),
        ('transfer', 'Bank Transfer (WhatsApp)'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending payment'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('cancelled', 'Cancelled'),
    ]

    # Secret URL id so customers can't read other orders by guessing a number.
    token = models.CharField(max_length=32, unique=True,
                             default=generate_order_token, editable=False)
    # Optional link to a customer account (guest orders stay None).
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             related_name='orders', on_delete=models.SET_NULL)

    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.TextField()
    city = models.CharField(max_length=80)
    postcode = models.CharField(max_length=12)
    state = models.CharField(max_length=60)
    region = models.CharField(max_length=4, choices=REGION_CHOICES, default='west')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='fpx')

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=20, blank=True)
    shipping = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    # Payment gateway bill code (toyyibPay), empty for demo orders.
    payment_ref = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.pk} — {self.full_name}"


class Coupon(models.Model):
    """Discount code, e.g. CNY10. Managed in the admin."""
    KIND_CHOICES = [
        ('percent', 'Percent off (%)'),
        ('fixed', 'Amount off (RM)'),
    ]

    code = models.CharField(max_length=20, unique=True,
                            help_text="Customers type this at the cart, e.g. CNY10.")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default='percent')
    value = models.DecimalField(max_digits=6, decimal_places=2,
                                help_text="Percent (e.g. 10) or RM amount (e.g. 30).")
    min_subtotal = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Minimum bag subtotal (RM) to use this code.")
    active = models.BooleanField(default=True)
    valid_until = models.DateField(
        null=True, blank=True, help_text="Last valid day. Empty = no expiry.")

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def check_valid(self, subtotal):
        """Return (ok, reason). reason is a customer-friendly message."""
        from django.utils import timezone
        if not self.active:
            return False, "This code is no longer active."
        if self.valid_until and timezone.localdate() > self.valid_until:
            return False, "This code has expired."
        if subtotal < self.min_subtotal:
            return False, f"This code needs a minimum of RM {self.min_subtotal:.2f}."
        return True, ""

    def discount_for(self, subtotal):
        if self.kind == 'percent':
            amount = subtotal * self.value / Decimal('100')
        else:
            amount = self.value
        return min(amount, subtotal).quantize(Decimal('0.01'))


class Review(models.Model):
    """Customer review. Hidden until the owner approves it in the admin."""
    product = models.ForeignKey(Product, related_name='reviews',
                                on_delete=models.CASCADE)
    name = models.CharField(max_length=60)
    rating = models.PositiveSmallIntegerField(
        choices=[(i, f"{i} star{'s' if i > 1 else ''}") for i in range(1, 6)])
    comment = models.TextField()
    approved = models.BooleanField(default=False,
                                   help_text="Only approved reviews show on the site.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}★ {self.product.name} — {self.name}"


class Subscriber(models.Model):
    """Newsletter signup from the footer."""
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class WishlistItem(models.Model):
    """Wishlist saved to a customer account (guests use the session)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             related_name='wishlist_items',
                             on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='wishlisted_by',
                                on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'product')]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} ♡ {self.product.name}"


class StockAlert(models.Model):
    """'Email me when it's back' request left on a sold-out product page."""
    product = models.ForeignKey(Product, related_name='stock_alerts',
                                on_delete=models.CASCADE)
    email = models.EmailField()
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('product', 'email')]

    def __str__(self):
        return f"{self.email} → {self.product.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=120)        # snapshot, in case product changes
    price = models.DecimalField(max_digits=8, decimal_places=2)
    size = models.CharField(max_length=10, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} × {self.name} ({self.size})"

    @property
    def line_total(self):
        return self.price * self.quantity
