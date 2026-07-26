"""Sitemap for search engines — lists every public page for Google."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Category, Product


class ProductSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True)


class CategorySitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Category.objects.all()


class StaticSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return ['shop:home', 'shop:info_shipping', 'shop:info_size_guide',
                'shop:info_about', 'shop:info_privacy', 'shop:track']

    def location(self, item):
        return reverse(item)
