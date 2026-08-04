# Méiyì PWA Mobile App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the existing Méiyì website installable as a free Progressive Web App on Android, iPhone, laptop, and desktop browsers.

**Architecture:** Keep Django as the only backend and add a web app manifest, root-scoped service worker, app metadata, install prompt, and local app icons. Cache only safe static assets and the public storefront shell; never cache admin, account, checkout, order, payment, or customer data responses.

**Tech Stack:** Django 5.2, existing templates, vanilla JavaScript, Web App Manifest, Service Worker, WhiteNoise static files.

## Global Constraints

- This is an installable website, not a separate native Android/iPhone codebase.
- Product, order, login, and payment requests remain online and use the existing Django routes.
- No private data, admin pages, checkout pages, or payment callbacks may be cached.
- The PWA must continue working as a normal website when installation is unavailable.
- The app must use the existing Méiyì jade, champagne, maroon, and ink brand colors.

### Task 1: Add PWA metadata and icons

**Files:**
- Modify: `shop/templates/shop/base.html`
- Create: `shop/static/shop/manifest.webmanifest`
- Create: `shop/static/shop/icons/icon-192.png`
- Create: `shop/static/shop/icons/icon-512.png`
- Test: `shop/tests.py`

- [ ] Add manifest and theme-color links to the base template.
- [ ] Add iOS standalone metadata and a descriptive app title.
- [ ] Create icon sizes 192px and 512px from the existing minimalist Méiyì mark with no text and no background clutter.
- [ ] Define the manifest with name `Méiyì`, short name `Méiyì`, `display: standalone`, `start_url: /`, `scope: /`, jade theme color, champagne background color, and the two icons.
- [ ] Add tests that the manifest is served and contains the required install fields.

### Task 2: Add a root-scoped service worker

**Files:**
- Modify: `shop/urls.py`
- Modify: `shop/views.py`
- Create: `shop/templates/shop/service-worker.js`
- Test: `shop/tests.py`

- [ ] Serve `/service-worker.js` from Django with JavaScript content type and root scope.
- [ ] Cache versioned static assets and the public homepage shell only.
- [ ] Use network-first behavior for public pages and fall back to the cached homepage when offline.
- [ ] Never cache paths beginning with `/admin/`, `/account/`, `/checkout/`, `/order/`, `/payment/`, `/login/`, `/logout/`, or `/password-reset/`.
- [ ] Add tests for status code, content type, and the presence of the sensitive-path exclusions.

### Task 3: Add installation UX and mobile checks

**Files:**
- Modify: `shop/templates/shop/base.html`
- Modify: `shop/static/shop` JavaScript location used by the base template
- Test: `shop/tests.py`

- [ ] Register the service worker only in secure production contexts or local development.
- [ ] Listen for `beforeinstallprompt` and show a small branded install button when the browser supports it.
- [ ] Hide the install button after installation or when unsupported.
- [ ] Keep the existing mobile menu and cart behavior unchanged.
- [ ] Verify the homepage, collections, product page, cart, checkout, admin, login, account, and order pages at 360px, 390px, 768px, and laptop widths.
- [ ] Run the complete Django test suite and a production static-file check.

### Task 4: Verify and publish

**Files:**
- No additional files.

- [ ] Run `python manage.py check`.
- [ ] Run `python manage.py test`.
- [ ] Run `python manage.py collectstatic --noinput` in a production-like environment.
- [ ] Confirm the service worker and manifest use HTTPS on Render.
- [ ] Stage only PWA files and related tests.
- [ ] Commit with `Make Meiyi installable as a PWA`.
- [ ] Push `main`, wait for Render to deploy, and test installation from Android Chrome and iPhone Safari.

