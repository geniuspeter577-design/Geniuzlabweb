from decimal import Decimal
import hashlib
import hmac
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.academy.models import Course, Enrollment
from apps.wallet.models import Wallet
from .models import Transaction
from .services import PaymentProviderError, fulfill_verified_payment

User = get_user_model()


class PaymentFulfillmentTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username="payment-user", email="payment@example.com", password="pass12345"
		)
		self.course = Course.objects.create(
			title="Test Course", slug="payment-course", summary="Test", price=Decimal("25000.00")
		)

	def test_verified_course_payment_enrolls_once(self):
		txn = Transaction.objects.create(
			user=self.user, course=self.course, purpose="course_enrollment",
			provider="paystack", amount=self.course.price,
		)
		result = {
			"reference": txn.reference, "provider_reference": "123",
			"amount": self.course.price, "currency": "NGN",
		}
		self.assertTrue(fulfill_verified_payment(txn, result))
		self.assertFalse(fulfill_verified_payment(txn, result))
		self.assertEqual(Enrollment.objects.filter(user=self.user, course=self.course).count(), 1)
		txn.refresh_from_db()
		self.assertEqual(txn.status, "success")

	def test_verified_wallet_funding_is_idempotent(self):
		txn = Transaction.objects.create(
			user=self.user, purpose="wallet_funding", provider="paystack", amount=Decimal("1000.00")
		)
		result = {
			"reference": txn.reference, "provider_reference": "456",
			"amount": Decimal("1000.00"), "currency": "NGN",
		}
		fulfill_verified_payment(txn, result)
		fulfill_verified_payment(txn, result)
		self.assertEqual(Wallet.objects.get(user=self.user).balance, Decimal("1000.00"))

	def test_amount_mismatch_does_not_fulfill(self):
		txn = Transaction.objects.create(
			user=self.user, course=self.course, purpose="course_enrollment",
			provider="paystack", amount=self.course.price,
		)
		with self.assertRaises(PaymentProviderError):
			fulfill_verified_payment(txn, {
				"reference": txn.reference, "amount": Decimal("1.00"), "currency": "NGN",
			})
		self.assertFalse(Enrollment.objects.filter(user=self.user, course=self.course).exists())

	@patch("apps.payments.services.requests.get")
	def test_duplicate_paystack_webhook_only_credits_once(self, mock_get):
		txn = Transaction.objects.create(
			user=self.user, purpose="wallet_funding", provider="paystack", amount=Decimal("1000.00")
		)
		provider_payload = {
			"status": True,
			"data": {
				"status": "success", "reference": str(txn.reference), "id": 789,
				"amount": 100000, "currency": "NGN",
			},
		}
		mock_get.return_value.status_code = 200
		mock_get.return_value.json.return_value = provider_payload
		body = json.dumps({
			"event": "charge.success",
			"data": {"reference": str(txn.reference)},
		}).encode()
		signature = hmac.new(
			b"test-paystack-secret", body, hashlib.sha512
		).hexdigest()
		with self.settings(PAYMENT_PROVIDERS={"paystack": {"secret_key": "test-paystack-secret"}}):
			response = self.client.post(
				reverse("payment_webhook", kwargs={"provider": "paystack"}),
				data=body,
				content_type="application/json",
				HTTP_X_PAYSTACK_SIGNATURE=signature,
			)
			self.assertEqual(response.status_code, 200)
			response = self.client.post(
				reverse("payment_webhook", kwargs={"provider": "paystack"}),
				data=body,
				content_type="application/json",
				HTTP_X_PAYSTACK_SIGNATURE=signature,
			)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Wallet.objects.get(user=self.user).balance, Decimal("1000.00"))
