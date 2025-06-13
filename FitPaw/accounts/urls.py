from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import  TokenRefreshView

from accounts.views import  UserViewSet, MyTokenObtainPairView, SignupView

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", UserViewSet.as_view, name="me"),
]