from django.urls import path
from . import views

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('start/<int:user_id>/', views.start_conversation, name='start_conversation'),
    path('<int:pk>/', views.conversation_detail, name='conversation_detail'),
    path('<int:pk>/poll/', views.poll_conversation, name='poll_conversation'),
    path('<int:pk>/typing/', views.set_typing, name='set_typing'),
]
