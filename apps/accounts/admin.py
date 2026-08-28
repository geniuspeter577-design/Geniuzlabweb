from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomerProfile, User


@admin.register(User)
class GeniuzUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_staff", "date_joined")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("GeniuzLab Profile", {"fields": ("role", "phone", "bio", "avatar", "cover_photo")}),
    )


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "profile_type", "company_name", "created_at")
    list_filter = ("profile_type",)
    search_fields = ("user__username", "company_name")
