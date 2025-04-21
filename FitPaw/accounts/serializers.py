from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username","password", "first_name", "last_name", "email", "img", "date_joined", "is_staff"]
        read_only_fields = ["id", "date_joined", "is_staff"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user