# Méiyì Shop — Visual Polish (Stage 2) Design

Date: 2026-06-19 (Asia/Kuala_Lumpur)
Owner: Lee Dick Xen
Project: `meiyi` Django shop

## Goal

Make the shop feel more premium and "alive" without changing its existing
look. Keep the current jade / champagne / maroon theme, Playfair + Inter fonts,
and existing patterns (Tailwind via CDN, `fade-up`, image hover-swap). All
changes are CSS / template / small vanilla JS only. No new Python features, no
new dependencies.

## Constraints

- Do not break existing behaviour. The order/checkout fixes from the code
  review stay as they are.
- Follow existing style; reuse the Tailwind config colours already in
  `base.html`.
- Each item must work on mobile and desktop.
- Keep JS small and inline per template, matching the current code.

## Scope — 13 items, grouped

### Group A — Motion & feedback (site-wide, in `base.html`)
1. Micro-interactions: buttons press down on click (`active:scale`), product
   cards lift with a soft shadow on hover, inputs get a jade focus ring.
2. "Added to bag" toast: a small message slides in top-right and auto-fades
   (~2.2s); the nav cart count does a short "bump" animation when it changes.
3. Smooth image fade-in: product/category images fade in once loaded instead
   of popping in.

### Group B — Cart & checkout
4. Checkout steps bar: "Bag → Details → Confirmed" shown on cart, checkout,
   and order-done pages; current step highlighted in jade.
5. Free-shipping progress bar: a visual bar in the cart summary showing how
   close the subtotal is to the free-shipping threshold (replaces text-only).
6. Quantity stepper: `−` / `+` buttons around the quantity number on the cart
   and product pages (keeps the existing number input, adds buttons).
7. Nicer empty-cart state: an outline icon + friendly line, not plain text.

### Group C — Product page
8. Image zoom: zoom the main gallery image on hover (desktop) / tap (mobile).
9. Sticky add-to-bag bar on mobile: a slim bottom bar with price + Add button
   that appears after the user scrolls past the main button.
10. Details accordion: collapsible Description / Materials / Care / Shipping
    sections under the product (Description open by default).
11. Quick-add on cards: the existing "Quick View" hover label becomes a real
    quick-add that adds the first size to the bag without leaving the page.

### Group D — Catalog & brand
12. Badge consistency: show "Best Seller" and sale "−%" badges on the
    collection-page product cards (homepage already has them).
13. Minimalist monogram logo + favicon: a simple SVG mark (no text, no
    background) used as the favicon and optionally beside the wordmark.

## Build order & verification

Build group by group; after each, confirm the page still renders (Django
`check` + load the page) before moving on.

1. Group A (base.html foundation) → verify every page still loads, toast shows
   after add-to-bag, cards lift on hover.
2. Group B → verify cart math unchanged, steps bar shows correct active step,
   progress bar matches the existing "amount to free shipping" value.
3. Group C → verify product page on a narrow window: zoom works, sticky bar
   appears on scroll, accordion opens/closes, quick-add posts and shows toast.
4. Group D → verify collection cards show badges; favicon loads; logo has no
   text and no background.

## Out of scope (later stages)

- Search bar (needs a backend view) — New Features stage.
- Real product photos — content, not code.
- Real payment gateway — Stage 4.
- Server-side form validation, stock/inventory — Code-quality stage.

## Acceptance criteria

- `python manage.py check` passes.
- No existing page errors; cart subtotal/shipping/total values are unchanged.
- All 13 items visible and working on both mobile and desktop widths.
- No new Python dependencies added.
