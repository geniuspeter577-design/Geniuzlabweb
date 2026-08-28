from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from apps.accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('apps.dashboard.urls')),
    path('accounts/', include('apps.accounts.urls')),
    # Clean, Instagram/LinkedIn-style public profile URL — used everywhere
    # a username or avatar is clickable across the site.
    path('u/<str:username>/', accounts_views.public_profile, name='public_profile'),
    path('', include('apps.konnect.urls')),
    path('academy/', include('apps.academy.urls')),
    path('motion/', include('apps.motion.urls')),
    path('subs/', include('apps.subs.urls')),
    path('vtu/', include('apps.vtu.urls')),
    path('payments/', include('apps.payments.urls')),
    path('wallet/', include('apps.wallet.urls')),
    path('chat/', include('apps.chat.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('automation/', include('apps.automation.urls')),
    path('assistant/', include('apps.assistant.urls')),
    path('ai-hub/', include('apps.ai_hub.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'apps.dashboard.error_views.custom_404'
handler500 = 'apps.dashboard.error_views.custom_500'
