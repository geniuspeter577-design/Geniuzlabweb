from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Wallet

User = get_user_model()


class WalletInvariantTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username="wallet-user", email="wallet@example.com", password="pass12345"
		)
		self.wallet = Wallet.objects.create(user=self.user, balance=Decimal("100.00"))

	def test_negative_credit_and_debit_are_rejected(self):
		with self.assertRaises(ValueError):
			self.wallet.credit(Decimal("-1.00"))
		with self.assertRaises(ValueError):
			self.wallet.debit(Decimal("-1.00"))
		self.wallet.refresh_from_db()
		self.assertEqual(self.wallet.balance, Decimal("100.00"))

	def test_credit_with_same_reference_is_idempotent(self):
		self.assertTrue(self.wallet.credit(Decimal("25.00"), reference="payment-1"))
		self.assertFalse(self.wallet.credit(Decimal("25.00"), reference="payment-1"))
		self.wallet.refresh_from_db()
		self.assertEqual(self.wallet.balance, Decimal("125.00"))
