from django.urls import path
from . import views

# Wallet funding remains behind the existing feature flag. Course checkout,
# callbacks, webhooks, history and receipts are independent payment flows.
from geniuzlab.feature_flags import vtu_feature_gate_redirect

urlpatterns = [
    path('', views.transaction_history, name='transaction_history'),
    path('course/<slug:slug>/pay/', views.initiate_course_payment, name='initiate_course_payment'),
    path('callback/<str:provider>/', views.payment_callback, name='payment_callback'),
    path('webhooks/<str:provider>/', views.payment_webhook, name='payment_webhook'),
    path(
        'pay/',
        vtu_feature_gate_redirect(
            'wallet_home',
            message="Wallet funding is temporarily unavailable.",
        )(views.initiate_payment),
        name='initiate_payment',
    ),
    path('receipt/<str:reference>/', views.payment_receipt, name='payment_receipt'),
]
