from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.gis.db import models as gis_models
from django.db import models

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        USER = "user", "User"
        MODERATOR = "moderator", "Moderator"
        ADMIN = "admin", "Admin"

    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.display_name or self.email


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name or emoji")
    color = models.CharField(max_length=7, help_text="Hex color for map markers, e.g. #FF0000")
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Submission(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        IN_PROGRESS = "in_progress", "Cleanup In Progress"
        CLEANED = "cleaned", "Cleaned"

    user = models.ForeignKey(
        "reports.User", on_delete=models.CASCADE, related_name="submissions"
    )
    photo = models.ImageField(upload_to="submissions/%Y/%m/")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    location = gis_models.PointField(geography=True, srid=4326)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="submissions"
    )
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    description = models.TextField(blank=True)
    exif_data = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    moderated_by = models.ForeignKey(
        "reports.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_submissions",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    cleaned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Submission #{self.pk} by {self.user} ({self.get_status_display()})"
