import stripe
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from membership.models import Membership
from membership.serializers import MembershipSerializer

from .services import (
    ActiveMembershipError,
    InvalidPlanError,
    MissingEmailError,
    StripeConfigurationError,
    create_checkout_session as create_stripe_checkout_session,
    list_membership_plans,
    process_stripe_webhook_event,
    retrieve_checkout_session,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_checkout_session_view(request):
    plan = request.data.get("plan")
    if not plan:
        return Response(
            {"detail": "Plan is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        checkout_session = create_stripe_checkout_session(request.user, plan)
    except (InvalidPlanError, MissingEmailError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except ActiveMembershipError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    except StripeConfigurationError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except stripe.error.StripeError as exc:
        return Response(
            {"detail": getattr(exc, "user_message", None) or str(exc) or "Stripe error."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            "clientSecret": checkout_session.client_secret,
            "sessionId": checkout_session.id,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_membership_plans(request):
    try:
        plans = list_membership_plans()
    except StripeConfigurationError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except stripe.error.StripeError as exc:
        return Response(
            {"detail": getattr(exc, "user_message", None) or str(exc) or "Stripe error."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(plans)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_session_status(request):
    session_id = request.query_params.get("session_id")
    if not session_id:
        return Response(
            {"detail": "session_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        checkout_session = retrieve_checkout_session(session_id)
    except StripeConfigurationError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except stripe.error.InvalidRequestError:
        return Response(
            {"detail": "Checkout session not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except stripe.error.StripeError as exc:
        return Response(
            {"detail": getattr(exc, "user_message", None) or str(exc) or "Stripe error."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    metadata = getattr(checkout_session, "metadata", {}) or {}
    owner_id = getattr(checkout_session, "client_reference_id", None) or metadata.get(
        "user_id"
    )
    if str(owner_id) != str(request.user.id):
        return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

    membership = Membership.objects.filter(user=request.user).first()
    subscription_id = getattr(checkout_session, "subscription", None)
    if not isinstance(subscription_id, str):
        subscription_id = getattr(subscription_id, "id", None)
    return Response(
        {
            "sessionId": checkout_session.id,
            "status": checkout_session.status,
            "paymentStatus": checkout_session.payment_status,
            "subscriptionId": subscription_id,
            "membership": MembershipSerializer(membership).data if membership else None,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return Response(
            {"detail": "Stripe webhook is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    signature = request.META.get("HTTP_STRIPE_SIGNATURE")
    if not signature:
        return Response(
            {"detail": "Stripe-Signature header is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        event = stripe.Webhook.construct_event(
            request.body,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return Response(
            {"detail": "Invalid webhook payload."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except stripe.error.SignatureVerificationError:
        return Response(
            {"detail": "Invalid webhook signature."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    processed = process_stripe_webhook_event(event)
    return Response({"received": True, "duplicate": not processed})


create_checkout_session = create_checkout_session_view
