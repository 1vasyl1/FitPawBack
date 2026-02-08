from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render

from .serializers import ChatRequestSerializer
from .services.assistant_service import handle_message


class AssistantChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        msg = serializer.validated_data["message"]
        result = handle_message(msg)
        return Response({"reply": result.reply}, status=status.HTTP_200_OK)


def demo(request):
    return render(request, "ai_assistant/demo.html")
