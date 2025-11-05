from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Additional Info", {
            "fields": ("full_name", "nickname", "phone", "address", "provider", "provider_id"),
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)