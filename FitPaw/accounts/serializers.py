from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ["id", "username", "img", "first_name", "last_name", "email", "date_joined"]
        read_only_fields = fields


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    class Meta:
        model  = User
        fields = ["username", "password", "first_name", "last_name", "email"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = super().create(validated_data)
        user.is_active = True
        user.is_staff = False
        user.set_password(password)
        user.save()
        return user

