from django.urls import path
from . import views

# NOTE: initiate_payment is the wallet-funding UI ("Fund Wallet"), which is
# temporarily disabled — see settings.FEATURE_VTU_ENABLED. It redirects to
# the wallet page (which stays live for viewing balance/history) instead
# of 404ing, since that's a real page users can still reach it from.
# transaction_history and payment_receipt are generic, non-VTU views and
# are left fully enabled. views.py is untouched — setting
# FEATURE_VTU_ENABLED = True fully restores wallet funding.
from geniuzlab.feature_flags import vtu_feature_gate_redirect

urlpatterns = [
    path('', views.transaction_history, name='transaction_history'),
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
