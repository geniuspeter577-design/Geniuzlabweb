from django.urls import path
from . import views

urlpatterns = [
    path('', views.wallet_home, name='wallet_home'),
]
