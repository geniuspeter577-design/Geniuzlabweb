from django.urls import path
from . import views

# NOTE: GeniuzSubs checkout depends on wallet funding, which is temporarily
# disabled — see settings.FEATURE_VTU_ENABLED. All views are wrapped with
# vtu_feature_gate (404 while disabled); views.py is untouched, so setting
# FEATURE_VTU_ENABLED = True fully restores subscriptions with no code
# changes.
from geniuzlab.feature_flags import vtu_feature_gate

urlpatterns = [
    path('', vtu_feature_gate(views.subs_home), name='subs'),
    path('<int:pk>/subscribe/', vtu_feature_gate(views.subscribe), name='subscribe'),
    path('my-subscriptions/', vtu_feature_gate(views.my_subscriptions), name='my_subscriptions'),
]
