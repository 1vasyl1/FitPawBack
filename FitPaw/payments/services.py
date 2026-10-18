from datetime import datetime, timezone as datetime_timezone
import hashlib
import json

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from membership.models import Membership

from .models import StripeWebhookEvent


PLAN_SETTINGS = {
    "enter": "STRIPE_PRICE_ID_ENTER",
    "pro": "STRIPE_PRICE_ID_PRO",
    "elite": "STRIPE_PRICE_ID_ELITE",
}


class PaymentsError(Exception):
    """Base exception for expected Payments API errors."""


class InvalidPlanError(PaymentsError):
    pass


class MissingEmailError(PaymentsError):
    pass


class ActiveMembershipError(PaymentsError):
    pass


class StripeConfigurationError(PaymentsError):
    pass


def _value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _json_safe(value):
    if hasattr(value, "to_dict_recursive"):
        value = value.to_dict_recursive()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def _timestamp_to_datetime(value):
    if not value:
        return None
    return datetime.fromtimestamp(value, tz=datetime_timezone.utc)


def get_price_map():
    return {
        plan: getattr(settings, setting_name, "")
        for plan, setting_name in PLAN_SETTINGS.items()
    }


def get_plan_for_price(price_id):
    return next(
        (plan for plan, configured_price_id in get_price_map().items() if configured_price_id == price_id),
        None,
    )


def _ensure_stripe_configured():
    if not settings.STRIPE_SECRET_KEY:
        raise StripeConfigurationError("Stripe is not configured.")
    stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(user, plan):
    _ensure_stripe_configured()

    price_id = get_price_map().get(plan)
    if not price_id:
        raise InvalidPlanError("Invalid or not configured plan.")
    if not user.email:
        raise MissingEmailError("Authenticated user must have an email address.")

    with transaction.atomic():
        membership, _ = Membership.objects.get_or_create(
            user=user,
            defaults={"status": Membership.Status.NONE},
        )
        membership = Membership.objects.select_for_update().get(pk=membership.pk)
        if membership.status in {
            Membership.Status.INCOMPLETE,
            Membership.Status.ACTIVE,
            Membership.Status.TRIALING,
            Membership.Status.PAST_DUE,
            Membership.Status.UNPAID,
            Membership.Status.PAUSED,
        }:
            raise ActiveMembershipError("User already has an active membership.")

        params = {
            "ui_mode": "embedded_page",
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "client_reference_id": str(user.id),
            "metadata": {"user_id": str(user.id), "plan": plan},
            "subscription_data": {
                "metadata": {"user_id": str(user.id), "plan": plan},
            },
            "return_url": settings.STRIPE_RETURN_URL,
        }
        if membership.stripe_customer_id:
            params["customer"] = membership.stripe_customer_id
        else:
            params["customer_email"] = user.email

        idempotency_payload = {
            "user_id": str(user.id),
            "params": params,
        }
        key_seed = json.dumps(
            idempotency_payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        idempotency_key = f"checkout_{hashlib.sha256(key_seed.encode()).hexdigest()}"
        return stripe.checkout.Session.create(
            idempotency_key=idempotency_key,
            **params,
        )


def list_membership_plans():
    _ensure_stripe_configured()
    plans = []
    for plan, price_id in get_price_map().items():
        if not price_id:
            continue

        try:
            price = stripe.Price.retrieve(price_id, expand=["product"])
        except stripe.error.InvalidRequestError as exc:
            raise StripeConfigurationError(
                f"Configured Stripe price for plan '{plan}' is invalid."
            ) from exc

        if not _value(price, "active", False) or not _value(price, "recurring"):
            raise StripeConfigurationError(
                f"Configured Stripe price for plan '{plan}' must be an active recurring price."
            )

        product = _value(price, "product", {})
        plans.append(
            {
                "plan": plan,
                "price_id": price_id,
                "name": _value(product, "name", ""),
                "description": _value(product, "description", ""),
                "amount": _value(price, "unit_amount"),
                "currency": _value(price, "currency"),
                "interval": _value(_value(price, "recurring", {}), "interval"),
            }
        )

    order = {plan: index for index, plan in enumerate(PLAN_SETTINGS)}
    return sorted(plans, key=lambda item: order[item["plan"]])


def retrieve_checkout_session(session_id):
    _ensure_stripe_configured()
    return stripe.checkout.Session.retrieve(session_id)


def _membership_for_stripe_data(customer_id=None, subscription_id=None):
    if subscription_id:
        membership = Membership.objects.filter(
            stripe_subscription_id=subscription_id
        ).first()
        if membership:
            return membership
        if customer_id:
            membership = Membership.objects.filter(
                stripe_customer_id=customer_id
            ).first()
            if membership and not membership.stripe_subscription_id:
                return membership
            return None
    if customer_id:
        return Membership.objects.filter(stripe_customer_id=customer_id).first()
    return None


def _membership_for_user_id(user_id, customer_id=None, subscription_id=None):
    if not user_id:
        return None
    user = get_user_model().objects.filter(pk=user_id).first()
    if not user:
        return None
    membership, _ = Membership.objects.get_or_create(
        user=user,
        defaults={"status": Membership.Status.INCOMPLETE},
    )
    if (
        customer_id
        and membership.stripe_customer_id
        and membership.stripe_customer_id != customer_id
    ):
        return None
    if (
        subscription_id
        and membership.stripe_subscription_id
        and membership.stripe_subscription_id != subscription_id
    ):
        return None
    return membership


def _event_is_stale(membership, event_created):
    return bool(
        event_created
        and event_created < membership.last_stripe_event_created
    )


def _set_event_created(membership, event_created):
    if event_created > membership.last_stripe_event_created:
        membership.last_stripe_event_created = event_created


def _set_membership_from_subscription(
    membership,
    subscription,
    status=None,
    event_created=0,
):
    membership = Membership.objects.select_for_update().get(pk=membership.pk)
    if _event_is_stale(membership, event_created):
        return membership

    items = _value(subscription, "items", {})
    subscription_items = _value(items, "data", []) or []
    first_item = subscription_items[0] if subscription_items else {}
    price = _value(first_item, "price", {})
    price_id = _value(price, "id")

    membership.stripe_customer_id = _value(subscription, "customer")
    membership.stripe_subscription_id = _value(subscription, "id")
    membership.stripe_price_id = price_id
    membership.plan = get_plan_for_price(price_id) or membership.plan
    membership.status = status or _value(
        subscription,
        "status",
        Membership.Status.INCOMPLETE,
    )
    membership.current_period_start = _timestamp_to_datetime(
        _value(subscription, "current_period_start")
    )
    membership.current_period_end = _timestamp_to_datetime(
        _value(subscription, "current_period_end")
    )
    membership.cancel_at_period_end = bool(
        _value(subscription, "cancel_at_period_end", False)
    )
    membership.canceled_at = _timestamp_to_datetime(
        _value(subscription, "canceled_at")
    )
    _set_event_created(membership, event_created)
    membership.save()
    return membership


@transaction.atomic
def sync_membership_from_checkout_session(session, event_created=0):
    metadata = _value(session, "metadata", {}) or {}
    user_id = _value(session, "client_reference_id") or _value(metadata, "user_id")
    membership = _membership_for_user_id(user_id)
    if not membership:
        return None
    membership = Membership.objects.select_for_update().get(pk=membership.pk)
    if _event_is_stale(membership, event_created):
        return membership

    membership.stripe_customer_id = _value(session, "customer")
    membership.stripe_subscription_id = _value(session, "subscription")
    membership.plan = _value(metadata, "plan", membership.plan)
    membership.stripe_price_id = get_price_map().get(
        membership.plan,
        membership.stripe_price_id,
    )
    membership.status = (
        Membership.Status.ACTIVE
        if _value(session, "payment_status") == "paid"
        else Membership.Status.INCOMPLETE
    )
    _set_event_created(membership, event_created)
    membership.save()
    return membership


def sync_membership_from_subscription(subscription, status=None, event_created=0):
    metadata = _value(subscription, "metadata", {}) or {}
    membership = _membership_for_stripe_data(
        customer_id=_value(subscription, "customer"),
        subscription_id=_value(subscription, "id"),
    )
    if not membership:
        membership = _membership_for_user_id(
            _value(metadata, "user_id"),
            customer_id=_value(subscription, "customer"),
            subscription_id=_value(subscription, "id"),
        )
    if not membership:
        return None
    return _set_membership_from_subscription(
        membership,
        subscription,
        status=status,
        event_created=event_created,
    )


def sync_membership_from_invoice(invoice, status, event_created=0):
    membership = _membership_for_stripe_data(
        customer_id=_value(invoice, "customer"),
        subscription_id=_value(invoice, "subscription"),
    )
    if membership:
        membership = Membership.objects.select_for_update().get(pk=membership.pk)
        if _event_is_stale(membership, event_created):
            return membership
        membership.status = status
        _set_event_created(membership, event_created)
        membership.save(update_fields=["status", "updated_at"])
    return membership


@transaction.atomic
def process_stripe_webhook_event(event):
    event_id = _value(event, "id")
    event_type = _value(event, "type", "unknown")
    event_created = _value(event, "created", 0) or 0
    event_payload = _json_safe(event)
    webhook_event, created = StripeWebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={
            "event_type": event_type,
            "payload": event_payload,
        },
    )
    if not created:
        return False

    event_object = _value(_value(event, "data", {}), "object", {})
    if event_type == "checkout.session.completed":
        sync_membership_from_checkout_session(event_object, event_created)
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
    }:
        sync_membership_from_subscription(
            event_object,
            event_created=event_created,
        )
    elif event_type == "customer.subscription.deleted":
        sync_membership_from_subscription(
            event_object,
            status=Membership.Status.CANCELED,
            event_created=event_created,
        )
    elif event_type == "invoice.paid":
        sync_membership_from_invoice(
            event_object,
            Membership.Status.ACTIVE,
            event_created,
        )
    elif event_type == "invoice.payment_failed":
        sync_membership_from_invoice(
            event_object,
            Membership.Status.PAST_DUE,
            event_created,
        )

    webhook_event.processed_at = timezone.now()
    webhook_event.save(update_fields=["processed_at"])
    return True
