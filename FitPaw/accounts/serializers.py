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


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.email = validated_data.get("email", instance.email)
        instance.save()
        return instance