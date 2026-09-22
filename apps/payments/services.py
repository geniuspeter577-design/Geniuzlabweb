import hashlib
import hmac
import json
from decimal import Decimal

import requests
from django.conf import settings
from django.urls import reverse


class PaymentConfigurationError(Exception):
    pass


class PaymentProviderError(Exception):
    pass


def _provider_config(provider):
    config = getattr(settings, "PAYMENT_PROVIDERS", {}).get(provider, {})
    if not config.get("secret_key"):
        raise PaymentConfigurationError(
            f"{provider.title()} payments are not configured. Add the provider secret key."
        )
    return config


def _callback_url(request, provider):
    return request.build_absolute_uri(
        reverse("payment_callback", kwargs={"provider": provider})
    )


def initialize_provider_payment(request, txn):
    config = _provider_config(txn.provider)
    if txn.amount <= 0:
        raise PaymentProviderError("Payment amount must be greater than zero.")
    if txn.currency != "NGN":
        raise PaymentProviderError("Only NGN payments are currently supported.")

    try:
        if txn.provider == "paystack":
            response = requests.post(
                "https://api.paystack.co/transaction/initialize",
                headers={"Authorization": f"Bearer {config['secret_key']}"},
                json={
                    "email": txn.user.email,
                    "amount": int(txn.amount * 100),
                    "currency": txn.currency,
                    "reference": txn.reference,
                    "callback_url": _callback_url(request, txn.provider),
                },
                timeout=20,
            )
        elif txn.provider == "flutterwave":
            response = requests.post(
                "https://api.flutterwave.com/v3/payments",
                headers={"Authorization": f"Bearer {config['secret_key']}"},
                json={
                    "tx_ref": txn.reference,
                    "amount": str(txn.amount),
                    "currency": txn.currency,
                    "redirect_url": _callback_url(request, txn.provider),
                    "customer": {"email": txn.user.email, "name": txn.user.get_full_name() or txn.user.username},
                    "customizations": {"title": "GeniuzLab Payment"},
                },
                timeout=20,
            )
        else:
            raise PaymentProviderError(f"Unsupported payment provider: {txn.provider}")
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise PaymentProviderError("The payment provider could not be reached.") from exc
    except ValueError as exc:
        raise PaymentProviderError("The payment provider returned invalid data.") from exc

    if txn.provider == "paystack":
        if not data.get("status") or not (data.get("data") or {}).get("authorization_url"):
            raise PaymentProviderError(data.get("message") or "Paystack did not initialize payment.")
        return data["data"]["authorization_url"]
    if data.get("status") != "success" or not (data.get("data") or {}).get("link"):
        raise PaymentProviderError(data.get("message") or "Flutterwave did not initialize payment.")
    return data["data"]["link"]


def _verify_paystack(reference):
    config = _provider_config("paystack")
    try:
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {config['secret_key']}"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise PaymentProviderError("Paystack verification failed.") from exc
    data = payload.get("data") or {}
    if not payload.get("status") or data.get("status") != "success":
        return None
    return {
        "reference": data.get("reference"),
        "provider_reference": str(data.get("id") or ""),
        "amount": Decimal(data.get("amount", 0)) / 100,
        "currency": data.get("currency"),
    }


def _verify_flutterwave(reference, transaction_id):
    config = _provider_config("flutterwave")
    if not transaction_id:
        raise PaymentProviderError("Flutterwave transaction ID is missing.")
    try:
        response = requests.get(
            f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",
            headers={"Authorization": f"Bearer {config['secret_key']}"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise PaymentProviderError("Flutterwave verification failed.") from exc
    data = payload.get("data") or {}
    if payload.get("status") != "success" or data.get("status") != "successful":
        return None
    if data.get("tx_ref") != reference:
        raise PaymentProviderError("Flutterwave reference mismatch.")
    return {
        "reference": data.get("tx_ref"),
        "provider_reference": str(data.get("id") or ""),
        "amount": Decimal(str(data.get("amount", 0))),
        "currency": data.get("currency"),
    }


def verify_provider_payment(provider, txn, payload=None, raw_body=None):
    config = _provider_config(provider)
    if raw_body is not None:
        try:
            event = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise PaymentProviderError("Invalid webhook payload.") from exc
        if provider == "paystack":
            signature = (payload or {}).get("X-Paystack-Signature", "")
            expected = hmac.new(config["secret_key"].encode(), raw_body, hashlib.sha512).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise PaymentProviderError("Invalid Paystack webhook signature.")
            if event.get("event") != "charge.success":
                return None
            reference = (event.get("data") or {}).get("reference")
            return _verify_paystack(reference)
        webhook_hash = getattr(settings, "FLUTTERWAVE_WEBHOOK_HASH", "")
        if not webhook_hash or not hmac.compare_digest((payload or {}).get("verif-hash", ""), webhook_hash):
            raise PaymentProviderError("Invalid Flutterwave webhook signature.")
        data = event.get("data") or {}
        if event.get("event") not in {"charge.completed", "transfer.completed"}:
            return None
        return _verify_flutterwave(data.get("tx_ref"), data.get("id"))

    if provider == "paystack":
        return _verify_paystack(txn.reference)
    transaction_id = (payload or {}).get("transaction_id") or (payload or {}).get("id")
    return _verify_flutterwave(txn.reference, transaction_id)


def fulfill_verified_payment(txn, result):
    if result.get("reference") != txn.reference:
        raise PaymentProviderError("Payment reference mismatch.")
    if result.get("currency") != txn.currency or Decimal(result.get("amount", 0)) != txn.amount:
        raise PaymentProviderError("Verified payment amount or currency mismatch.")
    txn.provider_reference = result.get("provider_reference", "")
    txn.save(update_fields=["provider_reference", "updated_at"])
    return txn.mark_success()