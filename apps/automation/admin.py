from django.contrib import admin

from .models import AutomationSettings, BibleVerse, BibleVerseLog, Broadcast, DailyMessageTemplate, NotificationLog


@admin.register(AutomationSettings)
class AutomationSettingsAdmin(admin.ModelAdmin):
    list_display = ("enabled", "send_hour", "send_minute", "assistant_enabled", "bible_verse_enabled", "last_run_date")

    def has_add_permission(self, request):
        # Singleton — only the one row (pk=1) should ever exist.
        return not AutomationSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DailyMessageTemplate)
class DailyMessageTemplateAdmin(admin.ModelAdmin):
    list_display = ("role", "category", "message", "link", "is_active")
    list_filter = ("role", "category", "is_active")
    search_fields = ("message",)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("template", "user", "date", "channel", "status", "sent_at")
    list_filter = ("date", "channel", "status")
    search_fields = ("user__username",)
    date_hierarchy = "date"


@admin.register(BibleVerse)
class BibleVerseAdmin(admin.ModelAdmin):
    list_display = ("reference", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("reference", "text")


@admin.register(BibleVerseLog)
class BibleVerseLogAdmin(admin.ModelAdmin):
    list_display = ("verse", "user", "date", "sent_at")
    list_filter = ("date",)
    search_fields = ("user__username", "verse__reference")
    date_hierarchy = "date"


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ("target_role", "message", "created_by", "created_at", "sent_at", "recipient_count")
    list_filter = ("target_role",)
