from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import SubmissionForm
from .models import Category, Submission
from .utils import extract_gps_from_exif, resize_photo


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


@login_required
def submit_view(request):
    if request.method == "POST":
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.cleaned_data["photo"]

            # Extract EXIF GPS before resize strips it
            gps_coords, exif_data = extract_gps_from_exif(photo)

            # User pin takes priority over EXIF
            lat = form.cleaned_data.get("latitude")
            lng = form.cleaned_data.get("longitude")

            if lat is None or lng is None:
                if gps_coords:
                    lat, lng = gps_coords
                else:
                    form.add_error(
                        None,
                        "No location found. Please place a pin on the map or "
                        "upload a photo with GPS data.",
                    )
                    return render(request, "reports/submit.html", {
                        "form": form,
                        "mapbox_token": settings.MAPBOX_TOKEN,
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
