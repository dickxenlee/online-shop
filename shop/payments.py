"""toyyibPay integration (FPX / card payments for Malaysia).

Demo mode: if the keys in settings are empty, checkout skips the gateway
and marks orders paid straight away (no money moves). Add your keys to go live
— see the comments in meiyi/settings.py.
"""
import requests
from django.conf import settings


def enabled():
    return bool(settings.TOYYIBPAY_SECRET_KEY and settings.TOYYIBPAY_CATEGORY_CODE)


def manual_mode():
    """Bank-transfer mode (no gateway): orders stay Pending, the customer is
    told how to pay on WhatsApp, and the owner marks them PAID in the admin."""
    return not enabled() and settings.MANUAL_PAYMENT


def create_bill(order):
    """Create a payment bill. Returns (payment_url, billcode) or (None, None)."""
    site = settings.SITE_URL.rstrip('/')
    data = {
        'userSecretKey': settings.TOYYIBPAY_SECRET_KEY,
        'categoryCode': settings.TOYYIBPAY_CATEGORY_CODE,
        # toyyibPay allows only letters/numbers/spaces here, max 30 chars.
        'billName': f'Meiyi Order {order.id}'[:30],
        'billDescription': 'Meiyi cheongsam order',
        'billPriceSetting': 1,          # fixed amount
        'billPayorInfo': 1,             # we pass the customer's details
        'billAmount': int(order.total * 100),   # in sen
        'billReturnUrl': f'{site}/payment/return/',
        'billCallbackUrl': f'{site}/payment/callback/',
        'billExternalReferenceNo': order.token,
        'billTo': order.full_name,
        'billEmail': order.email,
        'billPhone': order.phone,
    }
    try:
        r = requests.post(f'{settings.TOYYIBPAY_BASE_URL}/index.php/api/createBill',
                          data=data, timeout=15)
        billcode = r.json()[0]['BillCode']
        return f'{settings.TOYYIBPAY_BASE_URL}/{billcode}', billcode
    except Exception:
        return None, None


def bill_paid(billcode):
    """Ask toyyibPay whether this bill has a successful payment."""
    if not billcode:
        return False
    try:
        r = requests.post(
            f'{settings.TOYYIBPAY_BASE_URL}/index.php/api/getBillTransactions',
            data={'billCode': billcode, 'billpaymentStatus': '1'}, timeout=15)
        return bool(r.json())
    except Exception:
        return False
