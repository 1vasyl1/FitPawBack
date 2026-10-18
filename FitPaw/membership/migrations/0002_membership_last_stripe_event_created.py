from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("membership", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="membership",
            name="last_stripe_event_created",
            field=models.PositiveBigIntegerField(default=0),
        ),
    ]
