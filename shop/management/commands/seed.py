"""Fill the shop with demo collections and products.

Run:  python manage.py seed
It is safe to run again — it updates existing rows instead of duplicating.

Images are on-brand cheongsam illustration placeholders in shop/static/shop/cheongsam/.
Replace each product's photo anytime via the admin (upload) without touching this file.
"""
from django.core.management.base import BaseCommand
from shop.models import Category, Coupon, Product, ProductImage, Review

# Local placeholder illustrations (served from static). Swap for real photos later.
S = "/static/shop/cheongsam/"


def img(color):
    return f"{S}{color}.svg"


CATEGORIES = [
    ("Modern / Casual", "modern-casual", "Everyday ease, tailored close.",
     img("sage"), 1),
    ("Classic Silk", "classic-silk", "Pure mulberry, timeless lines.",
     img("jade"), 2),
    ("Festive / CNY", "festive-cny", "Reunion ready, quietly bold.",
     img("maroon"), 3),
]

# name, category-slug, price, was, sizes, main, hover, bestseller, gallery[], stock
PRODUCTS = [
    ("Lotus Pond Midi", "modern-casual", 389, 450, "XS,S,M,L",
     img("jade"), img("sage"), True, [img("maroon"), img("ink")], 12),
    ("Blush Peony Casual", "modern-casual", 298, None, "S,M,L",
     img("blush"), img("gold"), True, [], 2),          # low stock demo
    ("Jade Bamboo Silk", "classic-silk", 520, None, "S,M,L",
     img("sage"), img("jade"), True, [], 8),
    ("Champagne Evening", "classic-silk", 610, 680, "XS,S,M,L,XL",
     img("gold"), img("ink"), True, [], 10),
    ("Maroon Reunion", "festive-cny", 450, None, "XS,S,M,L",
     img("maroon"), img("gold"), True, [], 15),
    ("Golden Prosperity", "festive-cny", 480, 540, "S,M,L",
     img("gold"), img("maroon"), False, [], 0),        # sold out demo
    ("Ink Orchid Modern", "modern-casual", 340, None, "XS,S,M,L",
     img("ink"), img("jade"), False, [], 9),
    ("Pearl Mandarin Silk", "classic-silk", 560, None, "S,M,L,XL",
     img("blush"), img("ink"), False, [], 6),
]

DESC = ("A breathable stretch-silk cheongsam with a soft mandarin collar and "
        "hand-knotted pankou buttons. Cut close through the waist and relaxed at "
        "the hem — elegant for dinner, easy for the everyday.")


class Command(BaseCommand):
    help = "Seed demo collections and products."

    def handle(self, *args, **options):
        cats = {}
        for name, slug, tagline, image, order in CATEGORIES:
            cat, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={'name': name, 'tagline': tagline,
                          'image_url': image, 'order': order},
            )
            cats[slug] = cat
        self.stdout.write(self.style.SUCCESS(f"Categories: {len(cats)}"))

        for (name, cslug, price, was, sizes, main, hover, best, gallery, stock) in PRODUCTS:
            p, _ = Product.objects.update_or_create(
                name=name,
                defaults={
                    'category': cats[cslug], 'price': price,
                    'compare_at_price': was, 'sizes': sizes,
                    'image_url': main, 'hover_image_url': hover,
                    'is_bestseller': best, 'description': DESC,
                    'stock': stock,
                },
            )
            if gallery:
                p.gallery.all().delete()
                for src in gallery:
                    ProductImage.objects.create(product=p, image_url=src)
        self.stdout.write(self.style.SUCCESS(f"Products: {len(PRODUCTS)}"))

        Coupon.objects.update_or_create(
            code='WELCOME10',
            defaults={'kind': 'percent', 'value': 10, 'min_subtotal': 0,
                      'active': True},
        )
        self.stdout.write(self.style.SUCCESS("Coupon: WELCOME10 (10% off)"))

        DEMO_REVIEWS = [
            ('Lotus Pond Midi', 'Aisyah R.', 5,
             "The fit is perfect and the fabric is so soft. Wore it to my "
             "cousin's wedding — so many compliments!"),
            ('Lotus Pond Midi', 'Mei Ling T.', 5,
             "Beautiful workmanship. The pankou buttons are lovely and the "
             "size chart is accurate."),
            ('Jade Bamboo Silk', 'Priya N.', 4,
             "Elegant and comfortable for a full day. Shipping to Penang "
             "was fast too."),
        ]
        for pname, rname, rating, comment in DEMO_REVIEWS:
            Review.objects.get_or_create(
                product=Product.objects.get(name=pname), name=rname,
                defaults={'rating': rating, 'comment': comment,
                          'approved': True})
        self.stdout.write(self.style.SUCCESS(f"Reviews: {len(DEMO_REVIEWS)} demo"))
        self.stdout.write(self.style.SUCCESS("Seed complete."))
