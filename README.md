# Méiyì — Women's Modern Cheongsam Atelier 🌸

An online boutique for women's cheongsam, designed and tailored in Malaysia.
Built with Django. Feature-complete, tested, and deploy-ready.

## Features

**Storefront**
- Editorial homepage, collections with sort + size filter, product search
- Product pages: gallery zoom, size guide with a fit calculator, reviews
  with star ratings, details accordion, recently-viewed strip
- Wishlist (♡ on every card), session cart with quantity steppers,
  free-shipping progress bar, discount codes, mobile sticky buy bar
- Optional customer accounts: My Orders history, saved delivery address
  (checkout auto-fill), account wishlist, password reset — guest checkout
  always stays available
- Back-in-stock email alerts on sold-out pieces; customers can cancel their
  own order while it is still pending
- Order tracking page, trust pages (shipping/returns, size guide, about,
  privacy/PDPA), WhatsApp chat button, newsletter signup

**Business**
- Stock control: Sold Out / "Only X left", auto stock count-down on orders,
  low-stock alerts in admin, cancel-and-restock action
- Discount codes: percent or RM off, minimum spend, expiry, on/off
- Payments: toyyibPay (FPX + cards, Malaysia) with verified callbacks and
  Pay Now retry — or bank-transfer mode (auto on a live site without keys):
  orders stay Pending, customer gets WhatsApp/email pay instructions,
  owner marks PAID in admin
- Emails: order confirmation on payment, shipping notification on dispatch
- Review moderation, newsletter subscriber list — all managed in Django admin

**Engineering**
- 34 automated tests (`python manage.py test shop`)
- Order privacy via unguessable tokens (no order-ID guessing)
- Malaysian phone/postcode validation, honeypot spam protection,
  safe-redirect checks, branded 404/500 pages
- Production security headers, WhiteNoise static files, Postgres-ready,
  sitemap.xml + robots.txt for SEO
- One-click Render blueprint (`render.yaml`) — see `DEPLOY.md`

## Quick start (local)

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed          # demo products, coupon WELCOME10, reviews
python manage.py runserver
```

Open http://127.0.0.1:8000/ — admin at `/admin/`
(create a login with `python manage.py createsuperuser`).

## Tests

```bash
python manage.py test shop
```

## Going live

Follow `DEPLOY.md` — a step-by-step guide (hosting, payments, emails, domain).

---
Made with love in Kuala Lumpur. 美衣 — beautiful clothing.
