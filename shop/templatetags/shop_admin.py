"""Template tag that feeds the little dashboard on the admin home page."""
from django import template
from django.db.models import Sum
from django.utils import timezone

from ..models import Order, Product, Review, Subscriber

register = template.Library()

# Money already received (or received and sent out).
REVENUE_STATUSES = ('paid', 'shipped')


@register.inclusion_tag('admin/meiyi_stats.html')
def meiyi_dashboard():
    today = timezone.localdate()
    revenue = Order.objects.filter(status__in=REVENUE_STATUSES)
    return {
        'today_sales': revenue.filter(created_at__date=today)
                              .aggregate(s=Sum('total'))['s'] or 0,
        'month_sales': revenue.filter(created_at__year=today.year,
                                      created_at__month=today.month)
                              .aggregate(s=Sum('total'))['s'] or 0,
        'month_name': today.strftime('%B'),
        'to_ship': Order.objects.filter(status='paid').count(),
        'awaiting_payment': Order.objects.filter(status='pending').count(),
        'pending_reviews': Review.objects.filter(approved=False).count(),
        'subscribers': Subscriber.objects.count(),
        'low_stock': Product.objects.filter(is_active=True, stock__lte=3)
                                    .order_by('stock')[:5],
        'recent_orders': Order.objects.order_by('-created_at')[:5],
    }
