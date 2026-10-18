from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


class UserProfileApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="member",
            email="member@example.com",
            password="password",
        )
        self.other_user = user_model.objects.create_user(
            username="other",
            email="other@example.com",
            password="password",
        )
        self.client = APIClient()
        access_token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        self.url = "/auth/users/me/"

    def test_get_me_returns_authenticated_user(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["id"]), str(self.user.id))
        self.assertEqual(response.data["username"], self.user.username)

    def test_patch_me_updates_only_allowed_fields_for_authenticated_user(self):
        response = self.client.patch(
            self.url,
            {
                "id": str(self.other_user.id),
                "username": "changed-username",
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Edward",
                "last_name": "Zaza",
                "email": "edward@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["first_name"], "Edward")
        self.assertEqual(response.data["last_name"], "Zaza")
        self.assertEqual(response.data["email"], "edward@example.com")
        self.assertEqual(str(response.data["id"]), str(self.user.id))
        self.user.refresh_from_db()
        self.other_user.refresh_from_db()
        self.assertEqual(self.user.username, "member")
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.other_user.email, "other@example.com")

    def test_me_requires_authentication(self):
        client = APIClient()

        get_response = client.get(self.url)
        patch_response = client.patch(
            self.url,
            {"first_name": "Edward"},
            format="json",
        )

        self.assertEqual(get_response.status_code, 401)
        self.assertEqual(patch_response.status_code, 401)

    def test_me_rejects_invalid_bearer_token(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer invalid")

        response = client.patch(self.url, {"first_name": "Edward"}, format="json")

        self.assertEqual(response.status_code, 401)

    def test_patch_me_rejects_invalid_email(self):
        response = self.client.patch(
            self.url,
            {"email": "not-an-email"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "member@example.com")


class AuthRefreshCookieTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.username = "member"
        self.password = "password123"
        user_model.objects.create_user(
            username=self.username,
            email="member@example.com",
            password=self.password,
        )
        self.client = APIClient()

    def test_refresh_uses_cookie_without_refresh_in_body(self):
        login_response = self.client.post(
            "/auth/login/",
            {
                "username": self.username,
                "password": self.password,
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertIn("refresh", login_response.cookies)

        refresh_response = self.client.post("/auth/token/refresh/", {}, format="json")

        self.assertEqual(refresh_response.status_code, 200)
        self.assertIn("access", refresh_response.data)

    def test_refresh_without_cookie_returns_401(self):
        client = APIClient()

        response = client.post("/auth/token/refresh/", {}, format="json")

        self.assertEqual(response.status_code, 401)
