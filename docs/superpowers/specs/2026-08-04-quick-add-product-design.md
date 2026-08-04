# Méiyì Quick Add Product — Design Specification

**Date:** 2026-08-04 (Asia/Kuala_Lumpur)

## Goal

Give the store owner a simple product-entry page that works well on a phone and a laptop. The owner should be able to add a product and several photos from the device without changing GitHub or redeploying Render for each new product.

## Recommended approach

Add a custom, staff-only **Quick Add Product** page inside the existing Django admin. Keep the normal Django Product edit page for advanced editing. Store product records in Neon and uploaded photos in Cloudinary when the `CLOUDINARY_URL` environment variable is configured. Keep local media storage as the development fallback.

This separates business data from uploaded files:

```text
Quick Add form → Django → Neon (product details)
                         ↘ Cloudinary (product photos)
```

Adding or editing a product will not require a GitHub commit or Render deploy. GitHub and Render are only needed when the software code changes.

## User flow

1. Staff member signs in at the admin page.
2. Staff member selects **Quick Add Product** from the admin dashboard.
3. Staff member enters the product details and chooses several photos from the phone or laptop.
4. The first selected photo becomes the main product image. The remaining photos become gallery images.
5. Staff member selects **Save and publish**.
6. The page shows a success message and links to the new product and its admin edit page.

The existing ProductImage inline remains available for adding or editing gallery images later.

## Form fields

Required:

- Product name
- Category
- Price in MYR
- Sizes
- Stock quantity
- At least one product photo

Optional:

- Compare-at price
- Description
- Additional gallery photos
- Best seller switch
- Active switch, defaulting to active

The form will use a mobile-friendly layout: one column on small screens, two columns on larger screens, large touch targets, a photo preview area, and clear validation messages.

## Photo handling

- Accept common image formats only: JPG, JPEG, PNG, and WebP.
- Limit the number of selected photos to a practical gallery size.
- Validate file size and image content on the server.
- Use Cloudinary for live uploaded media so photos survive Render restarts, sleep, and redeploys.
- Never store Cloudinary credentials in GitHub or source code; they are Render environment variables.
- If Cloudinary is not configured locally, use Django's existing local media storage for development.

## Access and security

- The page is available only to authenticated staff users.
- Non-staff users are redirected to the admin login.
- CSRF protection remains enabled.
- Product creation uses the existing model validation and unique slug generation.
- Uploaded file names are handled by Django/Cloudinary storage; user-supplied names are not used as executable paths.

## Implementation boundaries

Included:

- Quick Add Product form, view, URL, template, and admin dashboard link
- Multiple-photo upload handling using the existing ProductImage model
- Cloudinary media-storage configuration with local fallback
- Responsive phone/laptop styling
- Automated tests for permissions, validation, product creation, and gallery creation
- Deployment documentation for the required Cloudinary environment variable

Not included:

- A separate Android or iPhone app
- Bulk CSV product import
- Product variants with separate stock per size
- Image editing or background removal
- Changes to checkout or customer accounts

## Success criteria

- A staff member can create a product from a phone-sized screen without horizontal scrolling.
- A staff member can create a product from a laptop using the same page.
- One submission can create a product with a main image and multiple gallery images.
- Product data remains in Neon after a Render restart.
- Live uploaded images remain available after a Render restart or deploy when Cloudinary is configured.
- Non-staff users cannot access the page.
- Existing admin product editing and storefront product pages continue to work.

