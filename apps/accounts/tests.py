from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegistrationTests(TestCase):
	def test_public_registration_cannot_grant_staff_roles(self):
		response = self.client.post(reverse("register"), {
			"username": "forged-admin",
			"email": "forged-admin@example.com",
			"password": "StrongPass123!",
			"confirm_password": "StrongPass123!",
			"role": "admin",
		})
		self.assertRedirects(response, reverse("dashboard"))
		user = User.objects.get(username="forged-admin")
		self.assertEqual(user.role, "customer")
		self.assertFalse(user.is_staff)

	def test_public_registration_allows_student_role(self):
		self.client.post(reverse("register"), {
			"username": "student-user",
			"email": "student@example.com",
			"password": "StrongPass123!",
			"confirm_password": "StrongPass123!",
			"role": "student",
		})
		self.assertEqual(User.objects.get(username="student-user").role, "student")


class LoginRedirectTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username="login-user", email="login@example.com", password="StrongPass123!"
		)

	def test_external_next_url_is_not_followed(self):
		response = self.client.post(reverse("login") + "?next=https://evil.example/", {
			"username": "login-user", "password": "StrongPass123!",
		})
		self.assertRedirects(response, reverse("dashboard"))
