from django.urls import path

from .views import DocumentDetailView, DocumentListCreateView, DocumentStatusView

urlpatterns = [
    path("documents/", DocumentListCreateView.as_view(), name="document-list"),
    path("documents/<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("documents/<uuid:pk>/status/", DocumentStatusView.as_view(), name="document-status"),
]
