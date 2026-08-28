from django.contrib import admin
from .models import VTUOrder


@admin.register(VTUOrder)
class VTUOrderAdmin(admin.ModelAdmin):
    list_display = ("user", "service_type", "service_id", "recipient", "amount", "status", "created_at")
    list_filter = ("service_type", "status", "service_id")
    search_fields = ("user__username", "recipient", "request_id", "provider_transaction_id")
    readonly_fields = ("request_id", "provider_transaction_id", "raw_response", "created_at", "updated_at")
