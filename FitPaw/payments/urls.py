from django.urls import path

from .views import (
    create_checkout_session,
    get_membership_plans,
    get_session_status,
    stripe_webhook,
)

urlpatterns = [
    path("create-checkout-session/", create_checkout_session, name="create_checkout_session"),
    path("plans/", get_membership_plans, name="plans"),
    path("session-status/", get_session_status, name="session_status"),
    path("webhook/", stripe_webhook, name="stripe_webhook"),
]
