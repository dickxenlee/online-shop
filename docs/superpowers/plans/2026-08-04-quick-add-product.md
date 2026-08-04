# Quick Add Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a responsive staff-only product form that creates a product and multiple gallery images from a phone or laptop without a GitHub update for each product.

**Architecture:** Add a custom admin view and template beside the existing Django admin. Reuse `Product` and `ProductImage`; the first selected file becomes `Product.image`, and later files become `ProductImage` rows. Configure Cloudinary as the live media storage while keeping the existing local storage fallback for development.

**Tech Stack:** Django 5.2, existing Django admin, `Pillow`, Cloudinary media storage, Neon PostgreSQL, Tailwind CDN.

## Global Constraints

- Product details remain in Neon; uploaded live media must not depend on Render's ephemeral filesystem.
- The page must work on phone and laptop widths without horizontal scrolling.
- Only authenticated staff users may create products.
- Cloudinary credentials must be Render environment variables and must never enter GitHub.
- Existing Product editing, ProductImage inlines, storefront pages, and guest checkout must continue working.

### Task 1: Add the quick-add form and permission tests

**Files:**
- Modify: `shop/forms.py`
- Test: `shop/tests.py`

- [ ] Add `QuickProductForm` with fields `name`, `category`, `price`, `compare_at_price`, `description`, `sizes`, `stock`, `is_bestseller`, `is_active`, and a multiple-file `photos` field.
- [ ] Validate at least one photo, allow JPG/JPEG/PNG/WebP, reject unsupported files, and reject files larger than 10 MB each.
- [ ] Add tests for staff access, non-staff rejection, missing photo validation, and invalid file validation.
- [ ] Run `python manage.py test shop.tests --verbosity=1` and confirm the new tests fail before the view exists.

### Task 2: Implement the quick-add view and routes

**Files:**
- Modify: `shop/views.py`
- Modify: `shop/urls.py`
- Modify: `shop/admin.py`
- Create: `shop/templates/admin/quick_product.html`

- [ ] Add a `staff_member_required` view named `quick_product` that accepts GET and POST.
- [ ] On POST, validate the form inside `transaction.atomic()`.
- [ ] Create the `Product`; generate its slug through the model's existing `save()` behavior.
- [ ] Save the first photo to `Product.image` and each remaining photo to a `ProductImage` row.
- [ ] Redirect to the product admin change page with a success message after saving.
- [ ] Add the URL under the existing admin namespace and add a dashboard link labelled `Quick Add Product`.
- [ ] Build a responsive form with one column on phones, two columns on laptops, a multiple photo picker, photo previews, and large touch-friendly controls.
- [ ] Add tests proving one product plus three gallery images are created and that invalid submissions create no partial product.
- [ ] Run `python manage.py test shop.tests --verbosity=1` and confirm the quick-add tests pass.

### Task 3: Configure persistent live media

**Files:**
- Modify: `requirements.txt`
- Modify: `meiyi/settings.py`
- Modify: `DEPLOY.md`

- [ ] Add the pinned Cloudinary storage dependency compatible with Django 5.2 and Pillow.
- [ ] Configure the default media storage to use Cloudinary only when `CLOUDINARY_URL` exists; preserve local `FileSystemStorage` when it does not.
- [ ] Keep static-file storage on WhiteNoise unchanged.
- [ ] Document adding `CLOUDINARY_URL` in Render Environment and explain that the value must not be committed.
- [ ] Run `python manage.py check` and the complete test suite.

### Task 4: Verify and publish

**Files:**
- No additional files.

- [ ] Run `python manage.py check`.
- [ ] Run `python manage.py test` and require all existing and new tests to pass.
- [ ] Open the quick-add page locally at a phone-sized browser width and a laptop width.
- [ ] Stage only the Quick Add, media configuration, tests, and documentation files.
- [ ] Commit with `Add mobile-friendly quick product form`.
- [ ] Push `main` and wait for Render to deploy the commit.
- [ ] Add `CLOUDINARY_URL` to Render and redeploy once; then create one test product from the live phone-sized page.

