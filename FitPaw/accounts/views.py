from http.client import responses

from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from datetime import timedelta
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.generics import CreateAPIView
from .serializers import (UserReadSerializer, UserSignupSerializer)

User = get_user_model()

class SignupView(CreateAPIView):
    serializer_class = UserSignupSerializer
    permission_classes = [AllowAny]


@api_view(["POST"])
def signup(self, request, *args, **kwargs):
    """
    {
      "username": "...",
      "password": "...",
      "email": "...",
      "first_name": "...",
      "last_name": "..."
    }
    """
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    token = TokenObtainPairSerializer.get_token(user)
    refresh = str(token)
    access = str(token.access_token)

    user_data = UserReadSerializer(user).data

    return Response(
        {
            "refresh": refresh,
            "access": access,
            "user": user_data,
        },
        status=status.HTTP_201_CREATED
    )


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserReadSerializer(self.user).data
        return data

@permission_classes([AllowAny])
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        access_token = str(response.data["access"])
        expiry = timezone.now() + timedelta(minutes=15)
    # ACCES_TOKEN_LIFETIME
        response.set_cookie(
            key="access",
            value=access_token,
            expires=expiry,
            httponly=True,
            secure=True,
            samesite="Lax",
        )
        return response
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("username")
    serializer_class = UserReadSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return UserSignupSerializer
        return UserReadSerializer

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        if self.request.method in ( "PUT", "PATCH", "DELETE"):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["GET", "PATCH"])
    def me(self, request):
        user = request.user
        if request.method == "GET":
            serializer = UserReadSerializer(user)
        else:
            serializer = UserReadSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)