"""Automated tests for the Méiyì shop.

Run all of them any time with:
    python manage.py test shop

They use a temporary database — your real data is never touched.
"""
from datetime import timedelta
from decimal import Decimal
from base64 import b64decode
import json
from pathlib import Path
from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.staticfiles import finders
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (Category, Coupon, Order, Product, Review, StockAlert,
                     Subscriber, WishlistItem)

GOOD_FORM = {
    'full_name': 'Mei Test', 'email': 'mei@example.com',
    'phone': '012-345 6789', 'address': '1 Jalan Test', 'city': 'KL',
    'postcode': '50000', 'state': 'WP', 'region': 'west',
    'payment_method': 'fpx',
}


def make_category(name='Test Silk'):
    return Category.objects.create(name=name)


def make_product(category=None, name='Test Dress', price='100.00',
                 stock=10, **kw):
    return Product.objects.create(
        category=category or make_category(name=f"Cat {name}"),
        name=name, price=Decimal(price), stock=stock, **kw)


class ModelTests(TestCase):
    def test_duplicate_names_get_unique_slugs(self):
        cat = make_category()
        a = Product.objects.create(category=cat, name='Twin', price=10)
        b = Product.objects.create(category=cat, name='Twin', price=20)
        self.assertNotEqual(a.slug, b.slug)

    def test_product_sale_and_size_helpers(self):
        p = make_product(price='80.00', compare_at_price=Decimal('100.00'),
                         sizes=' S, M ,L ')
        self.assertTrue(p.on_sale)
        self.assertEqual(p.discount_percent, 20)
        self.assertEqual(p.size_list, ['S', 'M', 'L'])

    def test_stock_flags(self):
        self.assertFalse(make_product(name='Out', stock=0).in_stock)
        self.assertTrue(make_product(name='Low', stock=2).low_stock)
        self.assertFalse(make_product(name='Full', stock=9).low_stock)

    def test_coupon_rules(self):
        percent = Coupon.objects.create(code='ten', kind='percent', value=10)
        self.assertEqual(percent.code, 'TEN')          # auto-uppercase
        self.assertEqual(percent.discount_for(Decimal('250.00')),
                         Decimal('25.00'))
        fixed = Coupon.objects.create(code='RM30', kind='fixed', value=30)
        self.assertEqual(fixed.discount_for(Decimal('20.00')),
                         Decimal('20.00'))             # never below zero total
        min_spend = Coupon.objects.create(code='BIG', kind='fixed', value=5,
                                          min_subtotal=500)
        ok, _ = min_spend.check_valid(Decimal('100.00'))
        self.assertFalse(ok)
        expired = Coupon.objects.create(
            code='OLD', kind='percent', value=10,
            valid_until=timezone.localdate() - timedelta(days=1))
        ok, _ = expired.check_valid(Decimal('100.00'))
        self.assertFalse(ok)
        inactive = Coupon.objects.create(code='OFF', kind='percent', value=10,
                                         active=False)
        self.assertFalse(inactive.check_valid(Decimal('100.00'))[0])


class CartTests(TestCase):
    def setUp(self):
        self.p = make_product(stock=3)
        self.add_url = reverse('shop:cart_add', args=[self.p.id])

    def test_add_and_show(self):
        self.client.post(self.add_url, {'size': 'M', 'quantity': 2})
        r = self.client.get(reverse('shop:cart'))
        self.assertContains(r, self.p.name)
        self.assertContains(r, 'RM 200.00')

    def test_add_is_capped_at_stock(self):
        self.client.post(self.add_url, {'size': 'M', 'quantity': 99})
        r = self.client.get(reverse('shop:cart'))
        self.assertContains(r, 'value="3"')            # capped to stock

    def test_sold_out_ajax_add_rejected(self):
        self.p.stock = 0
        self.p.save()
        r = self.client.post(self.add_url, {'size': 'M'},
                             HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 400)
        self.assertIn('sold out', r.json()['error'])

    def test_coupon_apply_and_remove(self):
        Coupon.objects.create(code='TEN', kind='percent', value=10)
        self.client.post(self.add_url, {'size': 'M', 'quantity': 2})
        self.client.post(reverse('shop:coupon_apply'), {'code': 'ten'})
        r = self.client.get(reverse('shop:cart'))
        self.assertContains(r, 'TEN')
        self.assertContains(r, '− RM 20.00')
        self.client.post(reverse('shop:coupon_remove'))
        r = self.client.get(reverse('shop:cart'))
        self.assertNotContains(r, '− RM 20.00')

    def test_unknown_coupon_rejected(self):
        self.client.post(self.add_url, {'size': 'M'})
        self.client.post(reverse('shop:coupon_apply'), {'code': 'NOPE'})
        r = self.client.get(reverse('shop:cart'))
        self.assertContains(r, 'not found')


class CheckoutTests(TestCase):
    def setUp(self):
        self.p = make_product(stock=5, price='200.00')
        self.client.post(reverse('shop:cart_add', args=[self.p.id]),
                         {'size': 'M', 'quantity': 1})

    def test_empty_cart_redirects_away(self):
        self.client.post(reverse('shop:cart_remove',
                                 args=[f'{self.p.id}:M']))
        r = self.client.get(reverse('shop:checkout'))
        self.assertRedirects(r, reverse('shop:cart'))

    def test_invalid_fields_show_errors_and_keep_values(self):
        bad = dict(GOOD_FORM, email='not-an-email', phone='123',
                   postcode='ABC')
        r = self.client.post(reverse('shop:checkout'), bad)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Malaysian phone number')
        self.assertContains(r, 'postcode is 5 digits')
        self.assertContains(r, 'value="Mei Test"')     # typed value kept
        self.assertEqual(Order.objects.count(), 0)

    def test_demo_checkout_pays_decrements_and_emails(self):
        r = self.client.post(reverse('shop:checkout'), GOOD_FORM)
        order = Order.objects.get()
        self.assertRedirects(r, reverse('shop:order_done',
                                        kwargs={'token': order.token}))
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.total, Decimal('210.00'))   # 200 + RM10 west
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 4)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('confirmed', mail.outbox[0].subject)

    def test_coupon_recorded_on_order(self):
        Coupon.objects.create(code='TEN', kind='percent', value=10)
        self.client.post(reverse('shop:coupon_apply'), {'code': 'TEN'})
        self.client.post(reverse('shop:checkout'), GOOD_FORM)
        order = Order.objects.get()
        self.assertEqual(order.discount, Decimal('20.00'))
        self.assertEqual(order.coupon_code, 'TEN')
        self.assertEqual(order.total, Decimal('190.00'))   # 200 - 20 + 10

    def test_order_page_needs_token_not_id(self):
        self.client.post(reverse('shop:checkout'), GOOD_FORM)
        order = Order.objects.get()
        ok = self.client.get(reverse('shop:order_done',
                                     kwargs={'token': order.token}))
        self.assertEqual(ok.status_code, 200)
        guess = self.client.get(f'/order/{order.id}/')
        self.assertEqual(guess.status_code, 404)


class PaymentGatewayTests(TestCase):
    def setUp(self):
        self.p = make_product(stock=5, price='200.00')
        self.client.post(reverse('shop:cart_add', args=[self.p.id]),
                         {'size': 'M', 'quantity': 1})

    def checkout_with_gateway(self, billcode='abc123'):
        with patch('shop.payments.enabled', return_value=True), \
             patch('shop.payments.create_bill',
                   return_value=(f'https://dev.toyyibpay.com/{billcode}',
                                 billcode)):
            return self.client.post(reverse('shop:checkout'), GOOD_FORM)

    def test_gateway_checkout_redirects_and_stays_pending(self):
        r = self.checkout_with_gateway()
        order = Order.objects.get()
        self.assertEqual(r.status_code, 302)
        self.assertIn('toyyibpay.com', r.headers['Location'])
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_ref, 'abc123')
        self.assertEqual(len(mail.outbox), 0)          # no email before paying

    def test_callback_marks_paid_and_emails(self):
        self.checkout_with_gateway()
        order = Order.objects.get()
        with patch('shop.payments.bill_paid', return_value=True):
            r = self.client.post(reverse('shop:payment_callback'),
                                 {'order_id': order.token, 'billcode': 'abc123',
                                  'status': '1'})
        self.assertEqual(r.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(len(mail.outbox), 1)

    def test_callback_without_real_payment_stays_pending(self):
        """A forged callback with the right codes must still not mark paid
        unless toyyibPay's API confirms the money really moved."""
        self.checkout_with_gateway()
        order = Order.objects.get()
        with patch('shop.payments.bill_paid', return_value=False):
            self.client.post(reverse('shop:payment_callback'),
                             {'order_id': order.token, 'billcode': 'abc123',
                              'status': '1'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(len(mail.outbox), 0)

    def test_forged_callback_rejected(self):
        self.checkout_with_gateway()
        order = Order.objects.get()
        r = self.client.post(reverse('shop:payment_callback'),
                             {'order_id': order.token, 'billcode': 'WRONG',
                              'status': '1'})
        self.assertEqual(r.status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')

    def test_return_url_verifies_before_marking_paid(self):
        self.checkout_with_gateway()
        order = Order.objects.get()
        with patch('shop.payments.bill_paid', return_value=True):
            self.client.get(reverse('shop:payment_return'),
                            {'order_id': order.token, 'status_id': '1'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')

    def test_failed_return_stays_pending(self):
        self.checkout_with_gateway()
        order = Order.objects.get()
        self.client.get(reverse('shop:payment_return'),
                        {'order_id': order.token, 'status_id': '3'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')


class FeatureTests(TestCase):
    def setUp(self):
        self.cat = make_category('Feature Silk')
        self.p1 = make_product(category=self.cat, name='Jade Feature',
                               price='100.00', sizes='S,M')
        self.p2 = make_product(category=self.cat, name='Pearl Feature',
                               price='300.00', sizes='XL')

    def test_search_finds_by_name(self):
        r = self.client.get(reverse('shop:search'), {'q': 'jade'})
        self.assertContains(r, 'Jade Feature')
        self.assertNotContains(r, 'Pearl Feature')

    def test_collection_sort_and_size_filter(self):
        url = self.cat.get_absolute_url()
        r = self.client.get(url, {'sort': 'price'})
        prices = [p.price for p in r.context['products']]
        self.assertEqual(prices, sorted(prices))
        r = self.client.get(url, {'size': 'XL'})
        names = [p.name for p in r.context['products']]
        self.assertEqual(names, ['Pearl Feature'])

    def test_wishlist_toggle_and_page(self):
        url = reverse('shop:wishlist_toggle', args=[self.p1.id])
        d = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest').json()
        self.assertEqual((d['added'], d['count']), (True, 1))
        self.assertContains(self.client.get(reverse('shop:wishlist')),
                            'Jade Feature')
        d = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest').json()
        self.assertEqual((d['added'], d['count']), (False, 0))

    def test_review_hidden_until_approved(self):
        self.client.post(reverse('shop:review_add', args=[self.p1.id]),
                         {'name': 'Girl A', 'rating': '4', 'comment': 'Nice!'})
        page = self.client.get(self.p1.get_absolute_url())
        self.assertNotContains(page, 'Girl A')
        Review.objects.filter(name='Girl A').update(approved=True)
        page = self.client.get(self.p1.get_absolute_url())
        self.assertContains(page, 'Girl A')

    def test_bad_review_rating_rejected(self):
        self.client.post(reverse('shop:review_add', args=[self.p1.id]),
                         {'name': 'Bad', 'rating': '9', 'comment': 'x'})
        self.assertFalse(Review.objects.exists())

    def test_newsletter_duplicate_and_invalid(self):
        url = reverse('shop:newsletter')
        self.client.post(url, {'email': 'girl@example.com'})
        self.client.post(url, {'email': 'girl@example.com'})
        self.client.post(url, {'email': 'nope'})
        self.assertEqual(Subscriber.objects.count(), 1)

    def test_newsletter_evil_redirect_blocked(self):
        r = self.client.post(reverse('shop:newsletter'),
                             {'email': 'a@b.com',
                              'next': 'https://evil.example.com/'})
        self.assertEqual(r.headers['Location'], '/')

    def test_track_order(self):
        self.client.post(reverse('shop:cart_add', args=[self.p1.id]),
                         {'size': 'S'})
        self.client.post(reverse('shop:checkout'), GOOD_FORM)
        order = Order.objects.get()
        r = self.client.post(reverse('shop:track'),
                             {'number': str(order.id),
                              'email': 'mei@example.com'})
        self.assertRedirects(r, reverse('shop:order_done',
                                        kwargs={'token': order.token}))
        r = self.client.post(reverse('shop:track'),
                             {'number': str(order.id),
                              'email': 'wrong@example.com'})
        self.assertContains(r, 'No order found')

    def test_static_pages_load(self):
        for name in ['shop:home', 'shop:info_shipping', 'shop:info_size_guide',
                     'shop:info_about', 'shop:info_privacy', 'shop:track',
                     'shop:wishlist']:
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)


class PaginationTests(TestCase):
    def setUp(self):
        self.cat = make_category('Big Silk')
        for i in range(15):
            make_product(category=self.cat, name=f'Piece {i}', price='100.00')

    def test_collection_paginates(self):
        r = self.client.get(self.cat.get_absolute_url())
        self.assertEqual(len(r.context['products']), 12)
        self.assertContains(r, 'Page 1 of 2')
        r2 = self.client.get(self.cat.get_absolute_url(), {'page': 2})
        self.assertEqual(len(r2.context['products']), 3)

    def test_search_paginates_and_keeps_query(self):
        r = self.client.get(reverse('shop:search'), {'q': 'Piece'})
        self.assertEqual(len(r.context['products']), 12)
        self.assertContains(r, 'q=Piece')
        self.assertContains(r, 'page=2')


class ExtrasTests(TestCase):
    def setUp(self):
        self.p = make_product()

    def test_shipped_email_sent_on_admin_change(self):
        self.client.post(reverse('shop:cart_add', args=[self.p.id]),
                         {'size': 'M'})
        self.client.post(reverse('shop:checkout'), GOOD_FORM)
        order = Order.objects.get()
        mail.outbox.clear()

        from django.contrib.admin.sites import AdminSite
        from .admin import OrderAdmin

        class FakeForm:
            changed_data = ['status']

        order.status = 'shipped'
        OrderAdmin(Order, AdminSite()).save_model(None, order, FakeForm(), True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('on its way', mail.outbox[0].subject)

    def test_review_honeypot_blocks_bots(self):
        self.client.post(reverse('shop:review_add', args=[self.p.id]),
                         {'name': 'Bot', 'rating': '5', 'comment': 'spam',
                          'website': 'http://spam.example'})
        self.assertFalse(Review.objects.exists())

    def test_newsletter_honeypot_blocks_bots(self):
        self.client.post(reverse('shop:newsletter'),
                         {'email': 'bot@spam.example', 'website': 'x'})
        self.assertFalse(Subscriber.objects.exists())

    def test_sitemap_and_robots(self):
        r = self.client.get('/sitemap.xml')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.p.slug)
        r = self.client.get('/robots.txt')
        self.assertContains(r, 'Sitemap:')
        self.assertContains(r, 'Disallow: /admin/')


@override_settings(MANUAL_PAYMENT=True)
class ManualPaymentTests(TestCase):
    """Bank-transfer mode: live site, no gateway keys yet."""

    def setUp(self):
        self.p = make_product()

    def _checkout(self):
        self.client.post(reverse('shop:cart_add', args=[self.p.id]),
                         {'size': 'M'})
        form = dict(GOOD_FORM, payment_method='transfer')
        self.client.post(reverse('shop:checkout'), form)
        return Order.objects.get()

    def test_checkout_shows_bank_transfer_box(self):
        self.client.post(reverse('shop:cart_add', args=[self.p.id]),
                         {'size': 'M'})
        r = self.client.get(reverse('shop:checkout'))
        self.assertContains(r, 'Bank Transfer via WhatsApp')
        self.assertNotContains(r, 'Demo checkout')

    def test_order_stays_pending_and_instructions_emailed(self):
        mail.outbox = []
        order = self._checkout()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_method, 'transfer')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('how to pay', mail.outbox[0].subject)
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 9)   # reserved while waiting

    def test_order_page_shows_whatsapp_pay_button(self):
        order = self._checkout()
        r = self.client.get(reverse('shop:order_done', args=[order.token]))
        self.assertContains(r, 'Payment Pending')
        self.assertContains(r, 'wa.me/')
        self.assertContains(r, 'How to pay')


class AdminTests(TestCase):
    """The admin dashboard and the one-click order actions."""

    def setUp(self):
        from django.contrib.auth.models import User
        boss = User.objects.create_superuser(
            'boss', 'boss@example.com', 'test-only-password')
        self.client.force_login(boss)
        self.p = make_product()

    def _paid_order(self):
        """Buy the product through the shop (demo mode = instantly paid)."""
        self.client.post(reverse('shop:cart_add', args=[self.p.id]),
                         {'size': 'M'})
        self.client.post(reverse('shop:checkout'), GOOD_FORM)
        return Order.objects.latest('id')

    def _run_action(self, url_name, action, pks):
        return self.client.post(reverse(url_name),
                                {'action': action, '_selected_action': pks,
                                 'index': '0'})

    def test_dashboard_shows_stats(self):
        self._paid_order()
        r = self.client.get(reverse('admin:index'))
        self.assertContains(r, 'Sales today')
        self.assertContains(r, 'RM 110.00')       # RM 100 + RM 10 shipping
        self.assertContains(r, 'Latest orders')

    def test_mark_shipped_action_updates_and_emails(self):
        order = self._paid_order()
        mail.outbox = []
        self._run_action('admin:shop_order_changelist', 'mark_shipped',
                         [order.pk])
        order.refresh_from_db()
        self.assertEqual(order.status, 'shipped')
        self.assertEqual(len(mail.outbox), 1)

    def test_mark_paid_action_for_bank_transfer(self):
        order = Order.objects.create(
            full_name='Mei Test', email='mei@example.com', phone='0123456789',
            address='1 Jalan Test', city='KL', postcode='50000', state='WP',
            subtotal=Decimal('100.00'), shipping=Decimal('10.00'),
            total=Decimal('110.00'), status='pending')
        mail.outbox = []
        self._run_action('admin:shop_order_changelist', 'mark_paid',
                         [order.pk])
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(len(mail.outbox), 1)   # receipt email

    def test_orders_csv_download(self):
        order = self._paid_order()
        r = self._run_action('admin:shop_order_changelist', 'export_csv',
                             [order.pk])
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/csv', r['Content-Type'])
        body = r.content.decode('utf-8')
        self.assertIn('Mei Test', body)
        self.assertIn('Test Dress', body)

    def test_subscriber_csv_download(self):
        sub = Subscriber.objects.create(email='fan@example.com')
        r = self._run_action('admin:shop_subscriber_changelist', 'export_csv',
                             [sub.pk])
        self.assertIn('fan@example.com', r.content.decode('utf-8'))


class QuickProductTests(TestCase):
    """Staff can use the phone-friendly product form from the admin area."""

    def setUp(self):
        from django.contrib.auth.models import User
        self.staff = User.objects.create_superuser(
            'boutique-owner', 'owner@example.com', 'test-only-password')

    def test_staff_can_open_quick_product_page(self):
        self.client.force_login(self.staff)

        response = self.client.get('/admin/quick-product/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Méiyì — Store Management')

    def test_non_staff_cannot_open_quick_product_page(self):
        from django.contrib.auth.models import User
        customer = User.objects.create_user(
            'customer', 'customer@example.com', 'test-only-password')
        self.client.force_login(customer)

        response = self.client.get('/admin/quick-product/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_photo_is_required_when_adding_product(self):
        self.client.force_login(self.staff)

        response = self.client.post('/admin/quick-product/', {
            'name': 'Jade Moon Cheongsam',
            'category': make_category().pk,
            'price': '269.00',
            'sizes': 'S,M,L',
            'stock': 5,
            'is_active': 'on',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add at least one photo.')
        self.assertFalse(Product.objects.filter(name='Jade Moon Cheongsam').exists())

    def _photo(self, name='jade.png'):
        return SimpleUploadedFile(
            name,
            b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='),
            content_type='image/png')

    def test_invalid_photo_type_creates_no_product(self):
        self.client.force_login(self.staff)
        bad_photo = SimpleUploadedFile(
            'not-a-photo.txt', b'not an image', content_type='text/plain')

        response = self.client.post('/admin/quick-product/', {
            'name': 'Jade Moon Cheongsam',
            'category': make_category().pk,
            'price': '269.00',
            'sizes': 'S,M,L',
            'stock': 5,
            'is_active': 'on',
            'photos': bad_photo,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Only JPG, PNG, and WebP photos are allowed.')
        self.assertFalse(Product.objects.filter(name='Jade Moon Cheongsam').exists())

    def test_staff_can_add_product_with_gallery_photos(self):
        self.client.force_login(self.staff)
        category = make_category()

        response = self.client.post('/admin/quick-product/', {
            'name': 'Jade Moon Cheongsam',
            'category': category.pk,
            'price': '269.00',
            'compare_at_price': '319.00',
            'description': 'A modern jade cheongsam.',
            'sizes': 'S,M,L',
            'stock': 5,
            'is_bestseller': 'on',
            'is_active': 'on',
            'photos': [self._photo('cover.png'), self._photo('back.png'),
                       self._photo('detail.png'), self._photo('closeup.png')],
        })

        product = Product.objects.get(name='Jade Moon Cheongsam')
        self.assertRedirects(
            response, reverse('admin:shop_product_change', args=[product.pk]))
        self.assertTrue(product.image.name.startswith('products/'))
        self.assertEqual(product.gallery.count(), 3)


class PwaTests(TestCase):
    def test_home_has_mobile_bottom_navigation(self):
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'id="mobileBottomNav"')
        self.assertContains(response, 'id="mobileSearchBtn"')

    def test_offline_page_is_public_and_helpful(self):
        response = self.client.get(reverse('shop:offline'))
        self.assertContains(response, 'You are offline')
        self.assertContains(response, 'Try again')

    def test_home_shows_pwa_install_help(self):
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'id="pwaInstallHelp"')
        self.assertContains(response, 'Add to Home Screen')
    def test_manifest_describes_the_installable_meiyi_app(self):
        manifest_path = finders.find('shop/manifest.webmanifest')
        if manifest_path is None:
            self.fail('The PWA manifest is missing from the static files.')

        manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))

        self.assertEqual(manifest['name'], 'Méiyì')
        self.assertEqual(manifest['display'], 'standalone')
        self.assertEqual(manifest['start_url'], '/')
        self.assertEqual(manifest['scope'], '/')
        self.assertEqual(len(manifest['icons']), 2)

    def test_service_worker_is_root_scoped_and_excludes_private_pages(self):
        response = self.client.get('/service-worker.js')

        self.assertEqual(response.status_code, 200)
        self.assertIn('application/javascript', response['Content-Type'])
        self.assertEqual(response['Service-Worker-Allowed'], '/')
        body = response.content.decode('utf-8')
        for private_path in ('/admin/', '/account/', '/checkout/', '/order/',
                             '/payment/', '/login/', '/logout/',
                             '/password-reset/'):
            self.assertIn(private_path, body)


class CustomerAccountTests(TestCase):
    def setUp(self):
        self.p = make_product()

    def _register(self, email='mei@example.com',
                  password='lotus-jade-river-42'):
        return self.client.post(reverse('shop:register'),
                                {'email': email, 'password1': password,
                                 'password2': password})

    def test_register_creates_account_and_logs_in(self):
        from django.contrib.auth.models import User
        r = self._register()
        self.assertRedirects(r, reverse('shop:account'))
        self.assertTrue(User.objects.filter(username='mei@example.com').exists())

    def test_duplicate_email_rejected(self):
        self._register()
        self.client.post(reverse('shop:logout'))
        r = self._register()
        self.assertContains(r, 'already exists')

    def test_account_requires_login(self):
        r = self.client.get(reverse('shop:account'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r.url)

    def test_checkout_links_order_and_shows_in_account(self):
        self._register()
        self.client.post(reverse('shop:cart_add', args=[self.p.id]),
                         {'size': 'M'})
        self.client.post(reverse('shop:checkout'), GOOD_FORM)
        order = Order.objects.get()
        self.assertEqual(order.user.username, 'mei@example.com')
        r = self.client.get(reverse('shop:account'))
        self.assertContains(r, f'#{order.id}')

    def test_checkout_prefills_from_last_order(self):
        self._register()
        self.client.post(reverse('shop:cart_add', args=[self.p.id]),
                         {'size': 'M'})
        self.client.post(reverse('shop:checkout'), GOOD_FORM)
        self.client.post(reverse('shop:cart_add', args=[self.p.id]),
                         {'size': 'M'})
        r = self.client.get(reverse('shop:checkout'))
        self.assertContains(r, '1 Jalan Test')     # saved address came back

    def test_wishlist_merges_into_account_and_persists(self):
        self.client.post(reverse('shop:wishlist_toggle', args=[self.p.id]))
        self._register()
        self.assertTrue(WishlistItem.objects.filter(product=self.p).exists())
        r = self.client.get(reverse('shop:wishlist'))
        self.assertContains(r, self.p.name)


class StockAlertTests(TestCase):
    def setUp(self):
        self.p = make_product(stock=0)

    def test_sold_out_page_offers_alert_signup(self):
        r = self.client.get(self.p.get_absolute_url())
        self.assertContains(r, 'Notify Me')

    def test_signup_stored_once(self):
        for _ in range(2):
            self.client.post(reverse('shop:stock_notify', args=[self.p.id]),
                             {'email': 'fan@example.com'})
        self.assertEqual(StockAlert.objects.count(), 1)

    def test_honeypot_blocks_bots(self):
        self.client.post(reverse('shop:stock_notify', args=[self.p.id]),
                         {'email': 'bot@spam.example', 'website': 'x'})
        self.assertFalse(StockAlert.objects.exists())

    def test_restock_emails_waiting_customers_once(self):
        StockAlert.objects.create(product=self.p, email='fan@example.com')
        mail.outbox = []
        from django.contrib.admin.sites import AdminSite
        from .admin import ProductAdmin

        class FakeForm:
            changed_data = ['stock']

        self.p.stock = 5
        ProductAdmin(Product, AdminSite()).save_model(None, self.p,
                                                      FakeForm(), True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('back in stock', mail.outbox[0].subject)
        self.assertTrue(StockAlert.objects.get().notified)
        # Saving again must not email the same customer twice.
        self.p.stock = 8
        ProductAdmin(Product, AdminSite()).save_model(None, self.p,
                                                      FakeForm(), True)
        self.assertEqual(len(mail.outbox), 1)


class CancelOrderTests(TestCase):
    def setUp(self):
        self.p = make_product()

    def _order(self):
        self.client.post(reverse('shop:cart_add', args=[self.p.id]),
                         {'size': 'M'})
        self.client.post(reverse('shop:checkout'), GOOD_FORM)
        return Order.objects.get()

    @override_settings(MANUAL_PAYMENT=True)
    def test_customer_cancels_pending_order_and_stock_returns(self):
        order = self._order()          # manual mode → stays pending
        self.assertEqual(order.status, 'pending')
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 9)
        self.client.post(reverse('shop:order_cancel', args=[order.token]))
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 10)

    def test_paid_order_cannot_be_cancelled(self):
        order = self._order()          # demo mode → instantly paid
        self.assertEqual(order.status, 'paid')
        self.client.post(reverse('shop:order_cancel', args=[order.token]))
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')


class NavigationAndSecurityTests(TestCase):
    def test_mobile_navigation_has_large_named_icon_targets(self):
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'id="mobileBottomNav"')
        self.assertContains(response, 'aria-label="Home"')
        self.assertContains(response, 'aria-label="Search"')
        self.assertContains(response, 'min-h-12')
        self.assertContains(response, 'w-6 h-6')

    def test_base_does_not_hide_images_when_javascript_is_unavailable(self):
        response = self.client.get(reverse('shop:home'))
        self.assertNotContains(response, 'img{opacity:0')

    def test_security_headers_use_strict_production_defaults(self):
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')
        self.assertEqual(settings.SECURE_REFERRER_POLICY,
                         'strict-origin-when-cross-origin')

    def test_home_uses_the_local_tailwind_build(self):
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'shop/tailwind')
        self.assertNotContains(response, 'cdn.tailwindcss.com')

    def test_home_uses_compiled_nav_spacing_and_new_app_icon(self):
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'app-icon')

    def test_desktop_navigation_groups_brand_and_links_in_one_row(self):
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'id="desktopNav"')
        self.assertContains(response, 'desktop-brand-links')

    def test_install_button_is_visible_without_browser_prompt(self):
        response = self.client.get(reverse('shop:home'))
        self.assertNotContains(response, 'id="installApp" type="button" hidden')
        self.assertContains(response, '>\n    Install\n  </button>')

    def test_homepage_images_below_hero_are_lazy_loaded(self):
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'loading="lazy"')


class AdminHomeLinkTests(TestCase):
    def test_admin_dashboard_has_view_home_page_link(self):
        from django.contrib.auth.models import User
        User.objects.create_superuser(username='admin-home', password='test-admin-password', email='admin-home@example.com')
        self.client.login(username='admin-home', password='test-admin-password')
        response = self.client.get(reverse('admin:index'))
        self.assertContains(response, 'View Home Page')
        self.assertContains(response, reverse('shop:home'))


class StaffLoginTests(TestCase):
    def test_staff_login_page_is_available_from_customer_login(self):
        response = self.client.get(reverse('shop:login'))
        self.assertContains(response, 'Admin sign in')
        self.assertContains(response, reverse('shop:staff_login'))

    def test_staff_can_login_and_go_to_admin(self):
        from django.contrib.auth.models import User
        User.objects.create_user(username='owner@example.com',
                                 password='test-owner-password', is_staff=True)
        response = self.client.post(reverse('shop:staff_login'), {
            'username': 'owner@example.com',
            'password': 'test-owner-password',
        })
        self.assertRedirects(response, reverse('admin:index'))

    def test_customer_cannot_use_staff_login(self):
        from django.contrib.auth.models import User
        User.objects.create_user(username='customer@example.com',
                                 password='test-customer-password')
        response = self.client.post(reverse('shop:staff_login'), {
            'username': 'customer@example.com',
            'password': 'test-customer-password',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Staff access is required')
