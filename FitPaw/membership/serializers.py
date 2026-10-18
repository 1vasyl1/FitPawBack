from rest_framework import serializers

from .models import Membership


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = [
            "plan",
            "status",
            "stripe_price_id",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "canceled_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
