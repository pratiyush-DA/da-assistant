from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.clients.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/", include("apps.chat.urls")),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.conversations.urls")),
    path("api/", include("apps.lineage.urls")),
]
