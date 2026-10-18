from django.conf import settings
from django.db import models


class Membership(models.Model):
    class Status(models.TextChoices):
        NONE = "none", "None"
        INCOMPLETE = "incomplete", "Incomplete"
        INCOMPLETE_EXPIRED = "incomplete_expired", "Incomplete expired"
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        UNPAID = "unpaid", "Unpaid"
        PAUSED = "paused", "Paused"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membership",
    )
    plan = models.CharField(max_length=32, blank=True)
    stripe_customer_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    stripe_subscription_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    stripe_price_id = models.CharField(max_length=255, blank=True)
    last_stripe_event_created = models.PositiveBigIntegerField(default=0)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.NONE,
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self):
        return f"{self.user.username}: {self.plan or self.status}"
