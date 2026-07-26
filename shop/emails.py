"""Customer emails. Plain text, sent on order paid and order shipped."""
from django.conf import settings
from django.core.mail import send_mail


def send_order_confirmation(order):
    lines = [
        f"Hi {order.full_name},",
        "",
        f"Thank you for your order! Order #{order.id} is confirmed.",
        "",
        "Your pieces:",
    ]
    for item in order.items.all():
        lines.append(f"  {item.quantity} x {item.name} ({item.size}) — "
                     f"RM {item.line_total:.2f}")
    lines += [
        "",
        f"Subtotal:  RM {order.subtotal:.2f}",
    ]
    if order.discount:
        lines.append(f"Discount:  -RM {order.discount:.2f}"
                     + (f" ({order.coupon_code})" if order.coupon_code else ""))
    lines += [
        f"Shipping:  RM {order.shipping:.2f}" if order.shipping else "Shipping:  Free",
        f"Total:     RM {order.total:.2f}",
        "",
        f"Delivery to: {order.address}, {order.postcode} {order.city}, {order.state}",
        f"({order.get_region_display()})",
        "",
        f"Track your order anytime: {settings.SITE_URL.rstrip('/')}/order/{order.token}/",
        "",
        "With love from Kuala Lumpur,",
        "Méiyì — Women's Cheongsam Atelier",
    ]
    send_mail(
        subject=f"Méiyì — Order #{order.id} confirmed",
        message="\n".join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        fail_silently=True,   # an email problem must never break checkout
    )


def send_order_received(order):
    """Bank-transfer mode: the order is reserved; tell the customer how to pay."""
    lines = [
        f"Hi {order.full_name},",
        "",
        f"Thank you! We received your order #{order.id} and reserved your pieces.",
        "It will ship as soon as your payment is confirmed.",
        "",
        "HOW TO PAY (bank transfer):",
        f"WhatsApp us at https://wa.me/{settings.WHATSAPP_NUMBER} with your "
        f"order number #{order.id} and we'll reply with our bank details.",
        "",
        "Your pieces:",
    ]
    for item in order.items.all():
        lines.append(f"  {item.quantity} x {item.name} ({item.size}) — "
                     f"RM {item.line_total:.2f}")
    lines += [
        "",
        f"Total to pay: RM {order.total:.2f}",
        "",
        f"Check your order anytime: {settings.SITE_URL.rstrip('/')}/order/{order.token}/",
        "",
        "With love from Kuala Lumpur,",
        "Méiyì — Women's Cheongsam Atelier",
    ]
    send_mail(
        subject=f"Méiyì — Order #{order.id} received · how to pay",
        message="\n".join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        fail_silently=True,
    )


def send_back_in_stock(product, email):
    """Sent (one by one) to everyone waiting when a product is restocked."""
    lines = [
        "Good news! 🌸",
        "",
        f"“{product.name}” is back in stock at Méiyì.",
        f"RM {product.price:.2f} — sizes {product.sizes}.",
        "",
        "It sold out once already, so don't wait too long:",
        f"{settings.SITE_URL.rstrip('/')}{product.get_absolute_url()}",
        "",
        "With love from Kuala Lumpur,",
        "Méiyì — Women's Cheongsam Atelier",
    ]
    send_mail(
        subject=f"Méiyì — “{product.name}” is back in stock",
        message="\n".join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )


def send_shipping_update(order):
    """Sent when the owner marks the order as Shipped in the admin."""
    days = "2–4" if order.region == 'west' else "4–7"
    lines = [
        f"Hi {order.full_name},",
        "",
        f"Good news — your order #{order.id} is on its way! 🚚",
        "",
        f"Delivery to: {order.address}, {order.postcode} {order.city}, {order.state}",
        f"Estimated arrival: {days} working days ({order.get_region_display()}).",
        "",
        f"Check your order anytime: {settings.SITE_URL.rstrip('/')}/order/{order.token}/",
        "",
        "Thank you for supporting Malaysian craft,",
        "Méiyì — Women's Cheongsam Atelier",
    ]
    send_mail(
        subject=f"Méiyì — Order #{order.id} is on its way",
        message="\n".join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        fail_silently=True,
    )
