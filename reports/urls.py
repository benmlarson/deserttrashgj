from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.map_view, name="map"),
    path("api/submissions.geojson", views.submissions_geojson, name="submissions_geojson"),
]
