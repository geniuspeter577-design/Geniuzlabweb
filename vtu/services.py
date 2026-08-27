"""
Thin wrapper around the VTpass API (https://vtpass.com/documentation/).

VTpass is a single VTU aggregator covering airtime, data, cable TV,
electricity, and education (WAEC/JAMB) — one account, one set of keys,
one API shape for all of Phase 6.

Configuration (see settings.py / .env):
    VTPASS_API_KEY
    VTPASS_SECRET_KEY
    VTPASS_PUBLIC_KEY      (used for some GET endpoints)
    VTPASS_LIVE_MODE       ("true"/"false") — sandbox by default

Sandbox base URL:  https://sandbox.vtpass.com/api/
Live base URL:     https://vtpass.com/api/

If no API key is configured, every call raises VTUNotConfigured so calling
views can degrade gracefully (mirrors how payments/settings.py already
treats missing Paystack keys as "pending" rather than crashing).
"""
import time
import uuid

import requests
from django.conf import settings


class VTUNotConfigured(Exception):
    """Raised when VTPASS_API_KEY / VTPASS_SECRET_KEY are not set."""


class VTUProviderError(Exception):
    """Raised when VTpass returns a non-success response."""

    def __init__(self, message, response_data=None):
        super().__init__(message)
        self.response_data = response_data or {}


def _config():
    cfg = getattr(settings, "VTPASS", {})
    if not cfg.get("api_key") or not cfg.get("secret_key"):
        raise VTUNotConfigured(
            "VTPASS_API_KEY / VTPASS_SECRET_KEY are not set. "
            "Add sandbox keys from https://sandbox.vtpass.com to your .env to enable VTU purchases."
        )
    return cfg


def _base_url():
    live = getattr(settings, "VTPASS", {}).get("live_mode", False)
    return "https://vtpass.com/api" if live else "https://sandbox.vtpass.com/api"


def _headers(cfg):
    return {
        "api-key": cfg["api_key"],
        "secret-key": cfg["secret_key"],
        "public-key": cfg.get("public_key", ""),
        "Content-Type": "application/json",
    }


def generate_request_id():
    """VTpass requires a unique alphanumeric requestId, timestamp-prefixed."""
    return time.strftime("%Y%m%d%H%M") + uuid.uuid4().hex[:10]


def _get(path, params=None):
    cfg = _config()
    resp = requests.get(f"{_base_url()}/{path}", headers=_headers(cfg), params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _post(path, payload):
    cfg = _config()
    resp = requests.post(f"{_base_url()}/{path}", headers=_headers(cfg), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Catalog lookups
# ---------------------------------------------------------------------------

def get_services(identifier):
    """List providers/networks for a category.

    identifier: 'airtime' | 'data' | 'tv-subscription' | 'electricity-bill' | 'education'
    """
    return _get("services", params={"identifier": identifier})


def get_variations(service_id):
    """List purchasable plans (data bundles, cable packages, exam pin types) for a serviceID."""
    return _get("service-variations", params={"serviceID": service_id})


# ---------------------------------------------------------------------------
# Verification (required by VTpass before paying for cable TV / electricity)
# ---------------------------------------------------------------------------

def verify_merchant(service_id, billers_code, variation_code=None):
    """Confirm a smartcard/IUC or meter number and return the customer's name."""
    payload = {"serviceID": service_id, "billersCode": billers_code}
    if variation_code:
        payload["type"] = variation_code
    data = _post("merchant-verify", payload)
    if str(data.get("code")) != "000":
        raise VTUProviderError(data.get("response_description", "Verification failed"), data)
    return data.get("content", {})


# ---------------------------------------------------------------------------
# Purchase
# ---------------------------------------------------------------------------

def purchase(service_id, amount, phone, request_id, variation_code=None, billers_code=None, extra=None):
    """Unified purchase call — covers airtime, data, cable, electricity, education.

    Returns the parsed JSON response. Caller is responsible for interpreting
    `response_description` / `content.transactions.status` and updating the
    matching VTUOrder + wallet accordingly.
    """
    payload = {
        "request_id": request_id,
        "serviceID": service_id,
        "amount": str(amount),
        "phone": phone,
    }
    if variation_code:
        payload["variation_code"] = variation_code
        payload["billersCode"] = billers_code or phone
    if extra:
        payload.update(extra)

    data = _post("pay", payload)
    return data


def requery(request_id):
    """Check the final status of a transaction that came back pending/timed out."""
    return _post("requery", {"request_id": request_id})


def transaction_status(response_data):
    """Map a VTpass response to one of our VTUOrder.STATUS_* values."""
    txn = (response_data.get("content") or {}).get("transactions") or {}
    raw_status = str(txn.get("status") or "").lower()
    code = str(response_data.get("code", ""))

    if raw_status == "delivered" or (code == "000" and raw_status in ("", "delivered")):
        return "successful"
    if raw_status in ("pending", "initiated"):
        return "pending"
    if raw_status == "reversed":
        return "reversed"
    if raw_status == "failed" or code not in ("000", ""):
        return "failed"
    return "pending"
