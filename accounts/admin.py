from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin config for the custom User model."""

    model = User
    list_display = ["email", "name", "is_google_user", "is_staff", "is_active"]
    list_filter = ["is_staff", "is_active", "is_google_user"]
    search_fields = ["email", "name"]
    ordering = ["email"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("name", "avatar", "google_id", "is_google_user")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )
