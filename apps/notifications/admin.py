from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "category", "is_read", "created_at")
    list_filter = ("is_read", "category")
    search_fields = ("user__username", "message")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "in_app_enabled", "email_enabled", "updated_at")
    list_filter = ("in_app_enabled", "email_enabled")
    search_fields = ("user__username",)
