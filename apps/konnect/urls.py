from django.urls import path
from . import views

urlpatterns = [
    path('hire-creative/', views.hire_creative, name='hire_creative'),
    path('creatives/<int:pk>/', views.creative_detail, name='creative_detail'),
    path('creatives/<int:pk>/request/', views.request_service, name='request_service'),
    path('my-creative-profile/', views.create_creative_profile, name='edit_creative_profile'),
    path('my-creative-profile/portfolio/', views.portfolio_dashboard, name='portfolio_dashboard'),
    path('my-creative-profile/portfolio/add/', views.add_portfolio_item, name='add_portfolio_item'),
    path('my-creative-profile/portfolio/<int:pk>/edit/', views.edit_portfolio_item, name='edit_portfolio_item'),
    path('my-creative-profile/portfolio/<int:pk>/delete/', views.delete_portfolio_item, name='delete_portfolio_item'),
    path('my-creative-profile/availability/', views.toggle_availability, name='toggle_availability'),
    path('service-requests/', views.my_service_requests, name='my_service_requests'),
    path('service-requests/<int:pk>/<str:action>/', views.respond_service_request, name='respond_service_request'),
    path('service-requests/<int:pk>/review/', views.leave_review, name='leave_review'),
    path('creatives/<int:pk>/save/', views.toggle_saved_creative, name='toggle_saved_creative'),

    # Home Feed / Discover / Search
    path('feed/', views.home_feed, name='home_feed'),
    path('discover/', views.discover, name='discover'),
    path('search/', views.search, name='search'),

    # Project-level social interactions
    path('projects/<int:pk>/like/', views.toggle_like, name='toggle_like'),
    path('projects/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('comments/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
    path('projects/<int:pk>/share/', views.share_project, name='share_project'),
    path('projects/<int:pk>/save/', views.toggle_save_project, name='toggle_save_project'),
    path('projects/<int:pk>/report/', views.report_project, name='report_project'),

    # Follow / Unfollow
    path('users/<int:user_id>/follow/', views.toggle_follow, name='toggle_follow'),

    path('jobs/', views.jobs, name='jobs'),
    path('jobs/post/', views.post_job, name='post_job'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('jobs/<int:pk>/apply/', views.apply_job, name='apply_job'),
    path('my-applications/', views.my_applications, name='my_applications'),

    path('collaborate/', views.collaborate, name='collaborate'),
    path('collaborate/<int:user_id>/request/', views.send_collaboration_request, name='send_collaboration_request'),
    path('collaborate/<int:pk>/<str:action>/', views.respond_collaboration_request, name='respond_collaboration_request'),
]
