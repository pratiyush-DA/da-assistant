from django.urls import path

from .views import LineageChatView, LineageIngestView, LineageTableView

urlpatterns = [
    path("lineage/ingest/", LineageIngestView.as_view(), name="lineage-ingest"),
    path("lineage/chat/", LineageChatView.as_view(), name="lineage-chat"),
    path("lineage/<str:table>/", LineageTableView.as_view(), name="lineage-table"),
]
