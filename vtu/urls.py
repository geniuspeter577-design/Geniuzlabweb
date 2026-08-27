from django.urls import path
from . import views

# NOTE: VTU (GeniuzSubs airtime/data/cable/electricity) is temporarily
# disabled on the public-facing app via settings.FEATURE_VTU_ENABLED.
# Every view below is wrapped with vtu_feature_gate, which 404s while the
# flag is False and otherwise calls straight through to the real view with
# no change in behavior. views.py itself is untouched — set
# FEATURE_VTU_ENABLED = True to fully restore this app.
from geniuzlab.feature_flags import vtu_feature_gate

urlpatterns = [
    path('', vtu_feature_gate(views.vtu_home), name='vtu_home'),

    path('airtime/', vtu_feature_gate(views.buy_airtime), name='vtu_buy_airtime'),

    path('data/', vtu_feature_gate(views.buy_data), name='vtu_buy_data'),
    path('api/variations/<str:service_id>/', vtu_feature_gate(views.api_variations), name='vtu_api_variations'),

    path('cable/', vtu_feature_gate(views.buy_cable), name='vtu_buy_cable'),
    path('api/verify-cable/', vtu_feature_gate(views.api_verify_cable), name='vtu_api_verify_cable'),

    path('electricity/', vtu_feature_gate(views.buy_electricity), name='vtu_buy_electricity'),
    path('api/verify-electricity/', vtu_feature_gate(views.api_verify_electricity), name='vtu_api_verify_electricity'),

    path('education/', vtu_feature_gate(views.buy_education), name='vtu_buy_education'),

    path('orders/', vtu_feature_gate(views.order_history), name='vtu_order_history'),
    path('orders/<int:pk>/', vtu_feature_gate(views.order_detail), name='vtu_order_detail'),
    path('orders/<int:pk>/requery/', vtu_feature_gate(views.order_requery), name='vtu_order_requery'),
]
