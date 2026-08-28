from django.contrib import admin

from .models import ChatConversation, ChatMessage, GeneratedImage, GeneratedVideo


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ("user", "prompt", "provider", "status", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("prompt", "user__username")
    date_hierarchy = "created_at"


@admin.register(GeneratedVideo)
class GeneratedVideoAdmin(admin.ModelAdmin):
    list_display = ("user", "prompt", "provider", "status", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("prompt", "user__username")
    date_hierarchy = "created_at"


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("role", "content", "created_at")
    can_delete = False


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ("user", "display_title", "created_at", "updated_at")
    search_fields = ("title", "user__username")
    date_hierarchy = "created_at"
    inlines = [ChatMessageInline]
