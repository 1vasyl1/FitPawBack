from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from membership.models import Membership


class PaymentsApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="member",
            email="member@example.com",
            password="password123",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("payments.services.stripe.checkout.Session.create")
    @override_settings(
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_PRICE_ID_PRO="price_pro",
    )
    def test_checkout_session_contains_user_reference(self, session_create):
        session_create.return_value.client_secret = "secret"
        session_create.return_value.id = "cs_test"

        response = self.client.post(
            "/api/payments/create-checkout-session/",
            {"plan": "pro"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["sessionId"], "cs_test")
        params = session_create.call_args.kwargs
        self.assertEqual(params["ui_mode"], "embedded_page")
        self.assertEqual(params["client_reference_id"], str(self.user.id))
        self.assertEqual(params["subscription_data"]["metadata"]["plan"], "pro")
        self.assertTrue(params["idempotency_key"].startswith("checkout_"))

    @patch("payments.services.stripe.checkout.Session.create")
    @override_settings(
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_PRICE_ID_PRO="price_pro",
    )
    def test_checkout_idempotency_key_changes_when_parameters_change(self, session_create):
        session_create.return_value.client_secret = "secret"
        session_create.return_value.id = "cs_test"

        first = self.client.post(
            "/api/payments/create-checkout-session/",
            {"plan": "pro"},
            format="json",
        )
        self.assertEqual(first.status_code, 201)
        first_key = session_create.call_args.kwargs["idempotency_key"]

        self.user.email = "updated@example.com"
        self.user.save(update_fields=["email"])

        second = self.client.post(
            "/api/payments/create-checkout-session/",
            {"plan": "pro"},
            format="json",
        )
        self.assertEqual(second.status_code, 201)
        second_key = session_create.call_args.kwargs["idempotency_key"]

        self.assertNotEqual(first_key, second_key)

    @override_settings(STRIPE_SECRET_KEY="")
    def test_checkout_session_requires_stripe_configuration(self):
        response = self.client.post(
            "/api/payments/create-checkout-session/",
            {"plan": "pro"},
            format="json",
        )

        self.assertEqual(response.status_code, 503)

    def test_session_status_rejects_missing_session_id(self):
        response = self.client.get("/api/payments/session-status/")

        self.assertEqual(response.status_code, 400)

    @patch("payments.services.stripe.Price.retrieve")
    @override_settings(
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_PRICE_ID_ENTER="",
        STRIPE_PRICE_ID_PRO="price_pro",
        STRIPE_PRICE_ID_ELITE="",
    )
    def test_plans_return_only_configured_recurring_prices(self, price_retrieve):
        price_retrieve.return_value.id = "price_pro"
        price_retrieve.return_value.active = True
        price_retrieve.return_value.recurring = {"interval": "month"}
        price_retrieve.return_value.product = {
            "name": "Pro",
            "description": "Pro membership",
        }
        price_retrieve.return_value.unit_amount = 1999
        price_retrieve.return_value.currency = "usd"

        response = self.client.get("/api/payments/plans/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["plan"], "pro")
        self.assertEqual(response.data[0]["interval"], "month")

    @patch("payments.views.stripe.Webhook.construct_event")
    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
    def test_webhook_is_idempotent(self, construct_event):
        construct_event.return_value = {
            "id": "evt_test",
            "type": "unknown.event",
            "data": {"object": {}},
        }
        headers = {"HTTP_STRIPE_SIGNATURE": "signature"}

        first = self.client.post(
            "/api/payments/webhook/",
            b"{}",
            content_type="application/json",
            **headers,
        )
        second = self.client.post(
            "/api/payments/webhook/",
            b"{}",
            content_type="application/json",
            **headers,
        )

        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.data["duplicate"])
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["duplicate"])

    @patch("payments.services.stripe.checkout.Session.retrieve")
    @override_settings(STRIPE_SECRET_KEY="sk_test")
    def test_session_status_rejects_another_users_session(self, session_retrieve):
        session_retrieve.return_value.id = "cs_test"
        session_retrieve.return_value.status = "complete"
        session_retrieve.return_value.payment_status = "paid"
        session_retrieve.return_value.subscription = "sub_test"
        session_retrieve.return_value.client_reference_id = "another-user"
        session_retrieve.return_value.metadata = {}

        response = self.client.get(
            "/api/payments/session-status/",
            {"session_id": "cs_test"},
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(
        STRIPE_PRICE_ID_PRO="price_pro",
        STRIPE_PRICE_ID_ENTER="price_enter",
    )
    def test_subscription_webhook_creates_membership(self):
        from payments.services import process_stripe_webhook_event

        event = {
            "id": "evt_subscription",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test",
                    "customer": "cus_test",
                    "status": "active",
                    "metadata": {"user_id": str(self.user.id)},
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_pro",
                                }
                            }
                        ]
                    },
                    "current_period_start": 1767225600,
                    "current_period_end": 1769904000,
                    "cancel_at_period_end": False,
                    "canceled_at": None,
                }
            },
        }

        self.assertTrue(process_stripe_webhook_event(event))
        membership = Membership.objects.get(user=self.user)
        self.assertEqual(membership.status, Membership.Status.ACTIVE)
        self.assertEqual(membership.plan, "pro")
        self.assertEqual(membership.stripe_subscription_id, "sub_test")

    def test_old_subscription_webhook_does_not_replace_current_membership(self):
        from payments.services import process_stripe_webhook_event

        membership = Membership.objects.create(
            user=self.user,
            stripe_customer_id="cus_test",
            stripe_subscription_id="sub_current",
            status=Membership.Status.ACTIVE,
            last_stripe_event_created=200,
        )
        event = {
            "id": "evt_old_subscription",
            "type": "customer.subscription.updated",
            "created": 300,
            "data": {
                "object": {
                    "id": "sub_old",
                    "customer": "cus_test",
                    "status": "past_due",
                    "metadata": {"user_id": str(self.user.id)},
                }
            },
        }

        self.assertTrue(process_stripe_webhook_event(event))
        membership.refresh_from_db()
        self.assertEqual(membership.status, Membership.Status.ACTIVE)
        self.assertEqual(membership.stripe_subscription_id, "sub_current")
