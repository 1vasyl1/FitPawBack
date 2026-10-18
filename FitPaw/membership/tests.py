from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Membership


class MembershipApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="member",
            email="member@example.com",
            password="password123",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_membership_me_creates_empty_membership(self):
        response = self.client.get("/api/membership/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Membership.Status.NONE)
        self.assertTrue(Membership.objects.filter(user=self.user).exists())
