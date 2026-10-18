import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Membership",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "plan",
                    models.CharField(blank=True, max_length=32),
                ),
                (
                    "stripe_customer_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "stripe_subscription_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "stripe_price_id",
                    models.CharField(blank=True, max_length=255),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("none", "None"),
                            ("incomplete", "Incomplete"),
                            ("incomplete_expired", "Incomplete expired"),
                            ("trialing", "Trialing"),
                            ("active", "Active"),
                            ("past_due", "Past due"),
                            ("canceled", "Canceled"),
                            ("unpaid", "Unpaid"),
                            ("paused", "Paused"),
                        ],
                        default="none",
                        max_length=32,
                    ),
                ),
                (
                    "current_period_start",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "current_period_end",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("cancel_at_period_end", models.BooleanField(default=False)),
                ("canceled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="membership",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-updated_at",)},
        ),
    ]
