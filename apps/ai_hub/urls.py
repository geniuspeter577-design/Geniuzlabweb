from django.urls import path

from . import views

urlpatterns = [
    path('', views.hub_home, name='ai_hub'),
    path('chat/', views.chat_list, name='ai_hub_chat_list'),
    path('chat/new/', views.chat_new, name='ai_hub_chat_new'),
    path('chat/<int:pk>/', views.chat_conversation, name='ai_hub_chat_conversation'),
    path('chat/<int:pk>/send/', views.chat_send_api, name='ai_hub_chat_send'),
    path('chat/<int:pk>/delete/', views.chat_delete, name='ai_hub_chat_delete'),
    path('image/', views.image_generator, name='ai_hub_image'),
    path('image/generate/', views.image_generate_api, name='ai_hub_image_generate'),
    path('video/', views.video_generator, name='ai_hub_video'),
    path('video/generate/', views.video_generate_api, name='ai_hub_video_generate'),
    path('video/<int:pk>/status/', views.video_status_api, name='ai_hub_video_status'),
]
