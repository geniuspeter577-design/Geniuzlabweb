from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    # Clean, Instagram/LinkedIn-style public profile URL — used everywhere
    # a username or avatar is clickable across the site.
    path('u/<str:username>/', accounts_views.public_profile, name='public_profile'),
    path('', include('konnect.urls')),
    path('academy/', include('academy.urls')),
    path('motion/', include('motion.urls')),
    path('subs/', include('subs.urls')),
    path('vtu/', include('vtu.urls')),
    path('payments/', include('payments.urls')),
    path('wallet/', include('wallet.urls')),
    path('chat/', include('chat.urls')),
    path('notifications/', include('notifications.urls')),
    path('automation/', include('automation.urls')),
    path('assistant/', include('assistant.urls')),
    path('ai-hub/', include('ai_hub.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'dashboard.error_views.custom_404'
handler500 = 'dashboard.error_views.custom_500'
