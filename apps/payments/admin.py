from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "provider_reference", "user", "course", "provider", "purpose", "amount", "status", "created_at")
    list_filter = ("provider", "purpose", "status")
    search_fields = ("reference", "provider_reference", "user__username", "user__email", "course__title")
