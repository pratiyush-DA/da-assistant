from django.urls import path

from .views import HealthView, PlatformStatsView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("stats/", PlatformStatsView.as_view(), name="platform-stats"),
]
