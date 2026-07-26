"""URL configuration for meiyi project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include

from shop import views as shop_views
from shop.sitemaps import CategorySitemap, ProductSitemap, StaticSitemap

sitemaps = {
    'products': ProductSitemap,
    'collections': CategorySitemap,
    'pages': StaticSitemap,
}

urlpatterns = [
    # The admin path can be moved via the ADMIN_URL env var (see settings.py).
    path(settings.ADMIN_URL, admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', shop_views.robots_txt, name='robots'),
    path('', include('shop.urls')),
]

# Serve uploaded product photos during local development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
