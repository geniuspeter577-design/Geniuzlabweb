from django.urls import path
from . import views

urlpatterns = [
    path('', views.automation_dashboard, name='automation_dashboard'),
    path('settings/update/', views.update_settings, name='automation_update_settings'),
    path('run-now/', views.run_now, name='automation_run_now'),
    path('run-bible-verse-now/', views.run_bible_verse_now, name='automation_run_bible_verse_now'),
    path('broadcasts/create/', views.create_broadcast, name='automation_create_broadcast'),
    path('broadcasts/<int:pk>/send/', views.send_broadcast_view, name='automation_send_broadcast'),
]
