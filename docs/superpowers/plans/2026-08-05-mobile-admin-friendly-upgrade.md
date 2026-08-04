# Mobile + Admin Friendly Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Méiyì easier on a phone, faster to manage in Django admin, and clearer when installed as a PWA.

**Architecture:** Reuse existing Django templates, session cart, admin, and service worker. Add a mobile-only shared navigation, extend the admin product/dashboard views, and add one public offline route. No data models or migrations change.

**Tech Stack:** Django 5.2, Django templates/admin, vanilla JavaScript, Tailwind CDN, service worker.

## Global Constraints

- Keep existing sticky Add to Bag and product form unchanged.
- Never show mobile navigation on checkout, payment, order, or admin pages.
- Cache only public home/static/offline content; private and payment routes stay network-only.
- Keep jade `#1F4A40`, champagne `#EFE6D9`, maroon `#5C1F25`, and ink `#262220`.
- Never stage `AGENTS.md`, database files, media, staticfiles, or secrets.

---

### Task 1: Phone bottom navigation

**Files:** Modify `shop/templates/shop/base.html`; test `shop/tests.py`.

**Interfaces:** Produce `#mobileBottomNav` and `#mobileSearchBtn`. Reuse `shop:home`, `shop:wishlist`, `shop:cart`, account/login URLs, and existing `#searchBtn`.

- [ ] Write this failing test in `PwaTests`:

```python
def test_home_has_mobile_bottom_navigation(self):
    response = self.client.get(reverse('shop:home'))
    self.assertContains(response, 'id="mobileBottomNav"')
    self.assertContains(response, 'id="mobileSearchBtn"')
    self.assertContains(response, 'Wishlist')
```

- [ ] Run `python manage.py test shop.tests.PwaTests.test_home_has_mobile_bottom_navigation --verbosity=1`; it must fail because navigation is absent.

- [ ] Add a `md:hidden` bottom navigation after normal content. Use five 44px targets: Home, Search, Wishlist, Bag, Account. Search is a button, not another form. Add mobile bottom padding. Use a template condition that excludes `checkout`, `order_done`, `payment_start`, `payment_return`, and `payment_callback`.

- [ ] Add this bridge beside the existing base-template JavaScript:

```javascript
const mobileSearch = document.getElementById('mobileSearchBtn');
if (mobileSearch) mobileSearch.onclick = () => document.getElementById('searchBtn').click();
```

- [ ] Run the focused test again; it must pass. Commit with `Add mobile shop navigation`.

### Task 2: Faster product management

**Files:** Modify `shop/admin.py` and `shop/templates/admin/meiyi_stats.html`; test `shop/tests.py`.

**Interfaces:** Produce `StockLevelFilter` for `ProductAdmin.list_filter` and action links to current admin routes.

- [ ] Write failing AdminTests:

```python
def test_product_admin_has_stock_filter(self):
    response = self.client.get(reverse('admin:shop_product_changelist'), {'stock_level': 'low'})
    self.assertContains(response, 'Stock level')

def test_dashboard_has_owner_action_links(self):
    response = self.client.get(reverse('admin:index'))
    self.assertContains(response, 'Manage products')
    self.assertContains(response, 'Manage orders')
```

- [ ] Run `python manage.py test shop.tests.AdminTests --verbosity=1`; it must fail.

- [ ] Add this `SimpleListFilter` in `shop/admin.py` and add it without removing existing product filters:

```python
class StockLevelFilter(admin.SimpleListFilter):
    title = 'Stock level'
    parameter_name = 'stock_level'
    def lookups(self, request, model_admin):
        return [('sold_out', 'Sold out'), ('low', 'Low stock'), ('ready', 'In stock')]
    def queryset(self, request, queryset):
        if self.value() == 'sold_out': return queryset.filter(stock=0)
        if self.value() == 'low': return queryset.filter(stock__gt=0, stock__lte=3)
        if self.value() == 'ready': return queryset.filter(stock__gte=4)
        return queryset
```

- [ ] Add a responsive owner-action row above the existing dashboard cards: Quick Add Product, Manage products, Manage orders, Approve reviews. Use existing named admin URLs and the existing jade/maroon colours.

- [ ] Run focused AdminTests again; they must pass. Commit with `Improve admin product controls`.

### Task 3: PWA guidance and safe offline page

**Files:** Modify `shop/views.py`, `shop/urls.py`, `shop/templates/shop/home.html`, `shop/templates/shop/service-worker.js`; create `shop/templates/shop/offline.html`; test `shop/tests.py`.

**Interfaces:** Produce public `shop:offline`, homepage `#pwaInstallHelp`, and service-worker constant `OFFLINE = '/offline/'`.

- [ ] Write failing PwaTests:

```python
def test_offline_page_is_public_and_helpful(self):
    response = self.client.get(reverse('shop:offline'))
    self.assertContains(response, 'You are offline')
    self.assertContains(response, 'Try again')

def test_home_shows_pwa_install_help(self):
    response = self.client.get(reverse('shop:home'))
    self.assertContains(response, 'id="pwaInstallHelp"')
    self.assertContains(response, 'Add to Home Screen')
```

- [ ] Run `python manage.py test shop.tests.PwaTests --verbosity=1`; it must fail.

- [ ] Implement the public view and route before the product slug route:

```python
def offline(request):
    return render(request, 'shop/offline.html')
```

- [ ] Create an offline template extending `shop/base.html`, with **You are offline** and a home link called **Try again**. Add a jade/champagne install-help card near the home hero. Explain Android **Install Méiyì app** and iPhone Safari Share → **Add to Home Screen**. Store dismissal under `meiyi-install-help-dismissed` in localStorage.

- [ ] Add `const OFFLINE = '/offline/';` to the service worker, cache it at install, and return it only after a failed public navigation. Keep private-path early return unchanged.

- [ ] Run focused PwaTests again; they must pass. Commit with `Improve PWA install and offline experience`.

### Task 4: Verify and deploy

- [ ] Run `python manage.py collectstatic --noinput`, `python manage.py check`, and `python manage.py test`; all must pass.
- [ ] At 360px, 390px, 768px, and laptop widths, check home, collection, product, cart, checkout, account, admin dashboard, and Quick Add. Confirm no horizontal scrolling and no mobile navigation in checkout/order/payment.
- [ ] Push with `git push origin main`. Confirm GitHub main equals the local commit; Render then deploys automatically.
