from django.urls import path
from . import views

urlpatterns = [
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('projects/', views.projects, name='projects'),
    path('projects/showcase/<slug:slug>/', views.project_showcase, name='project_showcase'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),

    path('courses/graphic-design/', views.graphic_design, name='graphic_design'),
    path('courses/video-editing/', views.video_editing, name='video_editing'),
    path('courses/ai-productivity/', views.ai_productivity, name='ai_productivity'),
    path('courses/web-development/', views.web_development, name='web_development'),

    path('graphics/', views.graphics, name='graphics'),
]
