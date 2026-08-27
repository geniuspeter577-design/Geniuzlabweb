from django.urls import path
from . import views

urlpatterns = [
    path('', views.motion_home, name='motion'),
]
