"""
URL configuration for FitPaw project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.shortcuts import redirect
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from schedule.staff_panel import staff_admin

schema_view = get_schema_view(
    openapi.Info(title="FitPaw API", default_version="v1"),
    public=True,
    permission_classes=[permissions.AllowAny],
)


urlpatterns = [
    path('', lambda request: redirect('schema-swagger-ui', permanent=False)),
    path('admin/', admin.site.urls),
    path('staff-panel/', staff_admin.urls),
    path('api/', include('api.urls')),
    path('auth/', include('accounts.urls')),
    path('schedule', include('schedule.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc')
]
