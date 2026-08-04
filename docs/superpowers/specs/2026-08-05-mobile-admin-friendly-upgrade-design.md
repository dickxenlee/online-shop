# Méiyì Mobile + Admin Friendly Upgrade

## Goal

Make the shop easier to buy from on a phone, easier to manage from the admin
page, and clearer when installed as the Méiyì PWA.

## Scope

### 1. Mobile customer shopping

- Keep the existing phone-only sticky **Add to Bag** bar and product details
  accordions unchanged; they already use the normal product form and preserve
  stock and size validation.
- Add a mobile bottom navigation for Home, Search, Wishlist, Bag, and Account.
  It appears only on shop pages, never in checkout, payment, order, or admin.

### 2. Admin control room

- Add a clear **Today’s work** area to the current dashboard: Quick Add
  Product, Products, Orders to Ship, Low Stock, and Reviews.
- Add a compact stock status filter and keep the direct **Add product** link
  in the product list. Existing Django edit and bulk tools remain available.
- Keep the existing Quick Add form's bound-field behaviour, which already
  preserves the selected category and choices after a validation error.
- Do not add a second product database or duplicate order workflow.

### 3. Installed PWA experience

- Add a small first-visit install help card on the homepage. It explains the
  Android install button and iPhone Safari Share → Add to Home Screen steps.
- Remember when the card is dismissed in the browser; it never blocks shopping.
- Add a friendly offline page only for public browsing. Admin, account,
  checkout, order, and payment pages stay network-only and are never cached.

## Design direction

Use the current jade, champagne, maroon, and ink palette. The mobile shop
stays calm and premium: large touch targets, short labels, and no crowded
floating controls. Admin remains Django admin, but its urgent actions are
grouped at the top so the owner can act quickly from a phone.

## Safety and data rules

- All product and order changes continue to use Django permissions and Neon.
- Images remain uploaded through admin/Quick Add and use Cloudinary when its
  Render environment variable is set.
- The PWA caches only public static assets, the public homepage shell, and the
  public offline page. It never caches private or payment routes.

## Verification

- Tests cover mobile-only page controls, staff dashboard links, stock filters,
  install-help dismissal markup, and offline/private service-worker rules.
- Check the home, collection, product, cart, checkout, account, admin, and
  Quick Add pages at 360px, 390px, 768px, and laptop widths.
- Run Django checks, the full test suite, and production static-file build
  before pushing `main` for Render to deploy.
