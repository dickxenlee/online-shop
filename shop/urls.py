from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('offline/', views.offline, name='offline'),
    path('search/', views.search, name='search'),
    path('cart/', views.cart_detail, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<str:key>/', views.cart_update, name='cart_update'),
    path('cart/remove/<str:key>/', views.cart_remove, name='cart_remove'),
    path('coupon/apply/', views.coupon_apply, name='coupon_apply'),
    path('coupon/remove/', views.coupon_remove, name='coupon_remove'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/<str:token>/', views.order_done, name='order_done'),
    path('order/<str:token>/cancel/', views.order_cancel, name='order_cancel'),
    path('payment/start/<str:token>/', views.payment_start, name='payment_start'),
    path('payment/return/', views.payment_return, name='payment_return'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('track/', views.track, name='track'),
    path('register/', views.register, name='register'),
    path('login/', views.MeiyiLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('account/', views.account, name='account'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='shop/password_reset.html',
        # Our own email body — the default one can't build namespaced URLs.
        email_template_name='shop/password_reset_email.html',
        success_url=reverse_lazy('shop:password_reset_done')),
        name='password_reset'),
    path('password-reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='shop/password_reset_done.html'),
        name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='shop/password_reset_confirm.html',
        success_url=reverse_lazy('shop:password_reset_complete')),
        name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='shop/password_reset_complete.html'),
        name='password_reset_complete'),
    path('notify/<int:product_id>/', views.stock_notify, name='stock_notify'),
    path('wishlist/', views.wishlist_page, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle, name='wishlist_toggle'),
    path('newsletter/', views.newsletter_signup, name='newsletter'),
    path('review/<int:product_id>/', views.review_add, name='review_add'),
    path('shipping-returns/', views.info_shipping, name='info_shipping'),
    path('size-guide/', views.info_size_guide, name='info_size_guide'),
    path('about/', views.info_about, name='info_about'),
    path('privacy/', views.info_privacy, name='info_privacy'),
    path('collection/<slug:slug>/', views.collection, name='collection'),
    path('<slug:slug>/', views.product_detail, name='product'),
]
