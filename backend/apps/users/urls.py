from django.urls import path

from .views import UserDetailView, UserListCreateView, UserSearchView

urlpatterns = [
    path("users/", UserListCreateView.as_view(), name="user-list"),
    path("users/search/", UserSearchView.as_view(), name="user-search"),
    path("users/<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
]
