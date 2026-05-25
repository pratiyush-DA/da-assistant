from django.urls import path

from .views import ChatHistoryView, ChatStreamView

urlpatterns = [
    path("chat/", ChatStreamView.as_view(), name="chat-stream"),
    path("chat/history/", ChatHistoryView.as_view(), name="chat-history"),
]
