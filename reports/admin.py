from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.gis.admin import GISModelAdmin
from django.utils import timezone

from .models import Category, Submission, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "display_name", "role", "is_staff", "date_joined")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("email", "display_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("display_name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Submission)
class SubmissionAdmin(GISModelAdmin):
    list_display = ("id", "user", "category", "severity", "status", "created_at")
    list_filter = ("status", "severity", "category", "created_at")
    readonly_fields = ("exif_data", "created_at", "updated_at")
    actions = ["approve_submissions", "reject_submissions"]

    @admin.action(description="Approve selected submissions")
    def approve_submissions(self, request, queryset):
        queryset.update(
            status=Submission.Status.APPROVED,
            moderated_by=request.user,
            moderated_at=timezone.now(),
        )

    @admin.action(description="Reject selected submissions")
    def reject_submissions(self, request, queryset):
        queryset.update(
            status=Submission.Status.REJECTED,
            moderated_by=request.user,
            moderated_at=timezone.now(),
        )
