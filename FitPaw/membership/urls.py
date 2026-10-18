from django.urls import path

from .views import membership_me

urlpatterns = [
    path("me/", membership_me, name="membership_me"),
]
