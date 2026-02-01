from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.map_view, name="map"),
    path("upload/", views.submit_view, name="submit"),
    path("api/submissions.geojson", views.submissions_geojson, name="submissions_geojson"),
    path("moderate/", views.moderate_list, name="moderate_list"),
    path("moderate/<int:pk>/", views.moderate_detail, name="moderate_detail"),
    path("moderate/<int:pk>/action/", views.moderate_action, name="moderate_action"),
]
