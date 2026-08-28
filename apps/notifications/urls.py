from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list, name='notifications'),
    path('<int:pk>/read/', views.mark_read, name='mark_notification_read'),
    path('<int:pk>/delete/', views.delete_notification, name='delete_notification'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_notifications_read'),
    path('clear-read/', views.delete_all_read, name='delete_read_notifications'),
    path('preferences/', views.preferences, name='notification_preferences'),
]
