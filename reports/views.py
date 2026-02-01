from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

from .models import Category, Submission


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
