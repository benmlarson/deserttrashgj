import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import SubmissionForm
from .models import Category, Submission
from .utils import cleanup_temp_uploads, extract_gps_from_exif, resize_photo

TEMP_PHOTO_DIR = Path(settings.MEDIA_ROOT) / "tmp_uploads"


def map_view(request):
    categories = Category.objects.all()
    context = {
        "mapbox_token": settings.MAPBOX_TOKEN,
        "categories": categories,
        "severity_choices": Submission.Severity.choices,
        # Only public statuses for the filter dropdown
        "status_choices": [
            (value, label)
            for value, label in Submission.Status.choices
            if value in ("approved", "in_progress", "cleaned")
        ],
    }
    return render(request, "reports/map.html", context)


def _save_temp_photo(uploaded_file):
    """Save an uploaded photo to a temp file and return the filename."""
    TEMP_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(uploaded_file.name).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    path = TEMP_PHOTO_DIR / filename
    with open(path, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)
    return filename


def _load_temp_photo(filename):
    """Load a temp photo file and return it as an InMemoryUploadedFile, or None."""
    # Sanitize: only allow a hex UUID + extension, no path traversal
    safe = Path(filename).name
    path = TEMP_PHOTO_DIR / safe
    if not path.is_file():
        return None
    from io import BytesIO

    data = path.read_bytes()
    buf = BytesIO(data)
    ext = path.suffix.lower()
    content_type = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
    }.get(ext, "image/jpeg")
    return InMemoryUploadedFile(
        file=buf, field_name="photo", name=safe,
        content_type=content_type, size=len(data), charset=None,
    )


def _delete_temp_photo(filename):
    """Remove a temp photo file if it exists."""
    if not filename:
        return
    safe = Path(filename).name
    path = TEMP_PHOTO_DIR / safe
    path.unlink(missing_ok=True)


@login_required
def submit_view(request):
    cleanup_temp_uploads()

    if request.method == "POST":
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            # Use newly uploaded photo, or fall back to temp photo from prior submit
            photo = form.cleaned_data.get("photo")
            temp_photo_name = form.cleaned_data.get("temp_photo")

            if not photo and temp_photo_name:
                photo = _load_temp_photo(temp_photo_name)
                if not photo:
                    form.add_error("photo", "Previous photo expired. Please select a photo again.")
                    return render(request, "reports/submit.html", {
                        "form": form,
                        "mapbox_token": settings.MAPBOX_TOKEN,
                    })

            # Extract EXIF GPS before resize strips it
            gps_coords, exif_data = extract_gps_from_exif(photo)

            # User pin takes priority over EXIF
            lat = form.cleaned_data.get("latitude")
            lng = form.cleaned_data.get("longitude")

            if lat is None or lng is None:
                if gps_coords:
                    lat, lng = gps_coords
                else:
                    # Save the photo so the user doesn't have to reselect it
                    if not temp_photo_name:
                        temp_photo_name = _save_temp_photo(photo)
                    form.add_error(
                        None,
                        "No location found. Please place a pin on the map or "
                        "upload a photo with GPS data.",
                    )
                    return render(request, "reports/submit.html", {
                        "form": form,
                        "mapbox_token": settings.MAPBOX_TOKEN,
                        "temp_photo": temp_photo_name,
                    })

            # Resize photo
            resized = resize_photo(photo)

            submission = form.save(commit=False)
            submission.user = request.user
            submission.status = Submission.Status.PENDING
            submission.latitude = Decimal(str(round(lat, 6)))
            submission.longitude = Decimal(str(round(lng, 6)))
            submission.location = Point(float(lng), float(lat), srid=4326)
            submission.exif_data = exif_data
            submission.photo = resized
            submission.save()

            # Clean up temp file if one was used
            _delete_temp_photo(temp_photo_name)

            messages.success(request, "Report submitted! It will appear on the map after review.")
            return redirect("reports:map")
    else:
        form = SubmissionForm()

    return render(request, "reports/submit.html", {
        "form": form,
        "mapbox_token": settings.MAPBOX_TOKEN,
    })


def submissions_geojson(request):
    """Return approved/in_progress/cleaned submissions as GeoJSON."""
    PUBLIC_STATUSES = ["approved", "in_progress", "cleaned"]
    qs = Submission.objects.filter(status__in=PUBLIC_STATUSES).select_related(
        "category"
    )

    # Filter by category slug(s)
    categories = request.GET.getlist("category")
    if categories:
        qs = qs.filter(category__slug__in=categories)

    # Filter by severity
    severity = request.GET.get("severity")
    if severity:
        qs = qs.filter(severity=severity)

    # Filter by status
    status = request.GET.get("status")
    if status and status in PUBLIC_STATUSES:
        qs = qs.filter(status=status)

    # Filter by date range
    date_from = request.GET.get("date_from")
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)

    date_to = request.GET.get("date_to")
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    features = []
    for sub in qs:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(sub.longitude), float(sub.latitude)],
                },
                "properties": {
                    "id": sub.pk,
                    "category_name": sub.category.name,
                    "color": sub.category.color,
                    "severity": sub.severity,
                    "status": sub.status,
                    "status_display": sub.get_status_display(),
                    "description": sub.description[:200] if sub.description else "",
                    "created_at": sub.created_at.strftime("%b %d, %Y"),
                },
            }
        )

    return JsonResponse(
        {"type": "FeatureCollection", "features": features}
    )
