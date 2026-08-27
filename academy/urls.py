from django.urls import path
from . import views

urlpatterns = [
    path('', views.academy_home, name='academy'),
    path('admin-stats/', views.academy_admin_stats, name='academy_admin_stats'),
    path('course/<slug:slug>/', views.course_detail, name='course_detail'),
    path('enroll/<slug:slug>/', views.enroll_course, name='enroll_course'),
    path('pay/<slug:slug>/', views.course_payment, name='course_payment'),
    path('pay/<slug:slug>/submit/', views.submit_payment, name='submit_payment'),
    path('pay/confirmation/<int:pk>/', views.payment_whatsapp_redirect, name='payment_whatsapp_redirect'),
    path('assignments/<int:pk>/submit/', views.submit_assignment, name='submit_assignment'),
    path('<slug:slug>/curriculum/', views.course_curriculum, name='course_curriculum'),
    path('modules/<int:pk>/', views.module_detail, name='module_detail'),
    path('lessons/<int:pk>/complete/', views.lesson_mark_complete, name='lesson_mark_complete'),
    path('quizzes/<int:pk>/', views.quiz_take, name='quiz_take'),
    path('community/post/', views.post_to_community, name='post_to_community'),
    path('certificate/<uuid:certificate_id>/', views.certificate_detail, name='certificate_detail'),
]
