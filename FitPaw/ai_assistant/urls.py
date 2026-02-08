from django.urls import path
from .views import AssistantChatView, demo

urlpatterns = [
    path("api/assistant/chat/", AssistantChatView.as_view(), name="assistant-chat"),
    path("assistant/demo/", demo, name="assistant-demo"),
]
