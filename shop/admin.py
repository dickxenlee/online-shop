import csv

from django.contrib import admin
from django.db.models import Count, F
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from .emails import send_back_in_stock, send_shipping_update
from .models import (Category, Coupon, Product, ProductImage, Order,
                     OrderItem, Review, StockAlert, Subscriber)

admin.site.site_header = "Méiyì — Store Management"
admin.site.site_title = "Méiyì Admin"
admin.site.index_title = "Today at your boutique"


def _csv_response(filename):
    """Start a CSV download; the BOM makes Excel show accents correctly."""
    stamp = timezone.localdate().strftime('%Y-%m-%d')
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="{filename}-{stamp}.csv"')
    response.write(chr(0xFEFF))
    return response


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'product_count')
    list_editable = ('order',)
    prepopulated_fields = {'slug': ('name',)}

    def get_queryset(self, request):
        # One query with a count, instead of one count query per row.
        return super().get_queryset(request).annotate(_product_count=Count('products'))

    def product_count(self, obj):
        return obj._product_count
    product_count.short_description = "Products"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 2


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('thumb', 'name', 'category', 'price', 'stock',
                    'stock_alert', 'is_bestseller', 'is_active')
    list_display_links = ('thumb', 'name')
    list_filter = ('category', 'is_bestseller', 'is_active')
    list_editable = ('stock', 'is_bestseller', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]

    def thumb(self, obj):
        if obj.cover:
            return format_html('<img src="{}" style="height:46px;width:38px;'
                               'object-fit:cover;border-radius:3px" />', obj.cover)
        return "—"
    thumb.short_description = ""

    def stock_alert(self, obj):
        if obj.stock == 0:
            return format_html('<b style="color:#b91c1c">SOLD OUT</b>')
        if obj.stock <= 3:
            return format_html('<b style="color:#d97706">LOW</b>')
        return "—"
    stock_alert.short_description = "Alert"

    def save_model(self, request, obj, form, change):
        """Restocking a sold-out piece emails everyone who asked to be told."""
        was_sold_out = False
        if change:
            old_stock = (Product.objects.filter(pk=obj.pk)
                         .values_list('stock', flat=True).first())
            was_sold_out = (old_stock == 0)
        super().save_model(request, obj, form, change)
        if was_sold_out and obj.stock > 0:
            waiting = obj.stock_alerts.filter(notified=False)
            for alert in waiting:
                send_back_in_stock(obj, alert.email)
            count = waiting.update(notified=True)
            if count and request:
                self.message_user(request,
                                  f"Back-in-stock email sent to {count} customer(s).")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'name', 'price', 'size', 'quantity', 'line_total')
    can_delete = False

    def line_total(self, obj):
        return obj.line_total


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'full_name', 'phone', 'rm_total',
                    'region', 'status_badge')
    list_filter = ('status', 'region', 'payment_method', 'created_at')
    date_hierarchy = 'created_at'
    search_fields = ('full_name', 'email', 'phone', 'token')
    readonly_fields = ('subtotal', 'discount', 'coupon_code', 'shipping',
                       'total', 'payment_ref', 'created_at')
    inlines = [OrderItemInline]
    actions = ['mark_paid', 'mark_shipped', 'cancel_and_restock', 'export_csv']

    STATUS_COLORS = {'pending': '#b45309', 'paid': '#15803d',
                     'shipped': '#1d4ed8', 'cancelled': '#6b7280'}

    def rm_total(self, obj):
        return f"RM {obj.total:,.2f}"
    rm_total.short_description = "Total"
    rm_total.admin_order_field = 'total'

    def status_badge(self, obj):
        color = self.STATUS_COLORS.get(obj.status, '#6b7280')
        return format_html(
            '<b style="color:{};background:{}1a;padding:2px 9px;'
            'border-radius:9px;font-size:11px">{}</b>',
            color, color, obj.get_status_display())
    status_badge.short_description = "Status"
    status_badge.admin_order_field = 'status'

    def save_model(self, request, obj, form, change):
        """Email the customer when the order is switched to Shipped."""
        just_shipped = (change and 'status' in form.changed_data
                        and obj.status == 'shipped')
        super().save_model(request, obj, form, change)
        if just_shipped:
            send_shipping_update(obj)

    @admin.action(description="Mark as PAID + email receipt (bank transfer)")
    def mark_paid(self, request, queryset):
        from .views import _mark_paid
        count = 0
        for order in queryset.filter(status='pending'):
            _mark_paid(order)
            count += 1
        self.message_user(request, f"{count} order(s) marked paid, "
                                   "receipt emailed to the customer.")

    @admin.action(description="Mark as SHIPPED + email the customer")
    def mark_shipped(self, request, queryset):
        count = 0
        for order in queryset.filter(status='paid'):
            order.status = 'shipped'
            order.save()
            send_shipping_update(order)
            count += 1
        self.message_user(request, f"{count} order(s) marked shipped, "
                                   "customer emailed.")

    @admin.action(description="Cancel unpaid order(s) + return stock")
    def cancel_and_restock(self, request, queryset):
        count = 0
        for order in queryset.filter(status='pending'):
            for item in order.items.all():
                if item.product_id:
                    Product.objects.filter(id=item.product_id).update(
                        stock=F('stock') + item.quantity)
            order.status = 'cancelled'
            order.save()
            count += 1
        self.message_user(request, f"{count} order(s) cancelled, stock returned.")

    @admin.action(description="Download as CSV for Excel")
    def export_csv(self, request, queryset):
        response = _csv_response('meiyi-orders')
        writer = csv.writer(response)
        writer.writerow(['Order', 'Date', 'Status', 'Name', 'Email', 'Phone',
                         'Address', 'City', 'Postcode', 'State', 'Region',
                         'Items', 'Subtotal', 'Discount', 'Coupon', 'Shipping',
                         'Total', 'Payment ref'])
        for o in queryset.prefetch_related('items'):
            items = '; '.join(f"{i.quantity}x {i.name} ({i.size})"
                              for i in o.items.all())
            writer.writerow([
                o.pk, timezone.localtime(o.created_at).strftime('%Y-%m-%d %H:%M'),
                o.get_status_display(), o.full_name, o.email, o.phone,
                o.address, o.city, o.postcode, o.state, o.get_region_display(),
                items, o.subtotal, o.discount, o.coupon_code, o.shipping,
                o.total, o.payment_ref])
        return response


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'kind', 'value', 'min_subtotal', 'active',
                    'valid_until', 'used_count')
    list_editable = ('active',)
    list_filter = ('active', 'kind')
    search_fields = ('code',)

    def used_count(self, obj):
        # A handful of coupons at most, so one small query per row is fine.
        return Order.objects.filter(coupon_code=obj.code).count()
    used_count.short_description = "Times used"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'rating', 'approved', 'created_at')
    list_editable = ('approved',)
    list_filter = ('approved', 'rating')
    search_fields = ('name', 'comment', 'product__name')
    actions = ['approve_reviews']

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f"{updated} review(s) approved.")


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'email', 'notified', 'created_at')
    list_filter = ('notified',)
    search_fields = ('email', 'product__name')


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')
    search_fields = ('email',)
    actions = ['export_csv']

    @admin.action(description="Download emails as CSV for Excel")
    def export_csv(self, request, queryset):
        response = _csv_response('meiyi-subscribers')
        writer = csv.writer(response)
        writer.writerow(['Email', 'Signed up'])
        for s in queryset:
            writer.writerow([s.email,
                             timezone.localtime(s.created_at).strftime('%Y-%m-%d')])
        return response
