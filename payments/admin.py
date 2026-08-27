from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "provider", "purpose", "amount", "status", "created_at")
    list_filter = ("provider", "purpose", "status")
    search_fields = ("reference", "user__username", "user__email")
