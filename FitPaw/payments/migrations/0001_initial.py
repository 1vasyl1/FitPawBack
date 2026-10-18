from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="StripeWebhookEvent",
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
                ("event_id", models.CharField(max_length=255, unique=True)),
                ("event_type", models.CharField(max_length=255)),
                ("payload", models.JSONField(default=dict)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ("-received_at",)},
        ),
    ]
