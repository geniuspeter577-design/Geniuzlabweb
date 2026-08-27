from django.contrib import admin
from .models import AssistantLog


@admin.register(AssistantLog)
class AssistantLogAdmin(admin.ModelAdmin):
    list_display = ("user", "session_key", "message", "intent", "created_at")
    list_filter = ("intent",)
    search_fields = ("message", "reply", "user__username")
    date_hierarchy = "created_at"
