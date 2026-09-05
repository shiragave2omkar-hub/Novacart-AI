"""Server-only Razorpay Test Mode helpers for NovaCart checkout."""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import razorpay


class PaymentIntegrationUnavailable(RuntimeError):
    """Raised when Test Mode credentials are not safely configured."""


class PaymentProviderError(RuntimeError):
    """Raised when Razorpay cannot create a Test Mode order."""


class PaymentVerificationFailed(RuntimeError):
    """Raised when Razorpay cannot verify a checkout signature."""


def get_test_mode_credentials() -> tuple[str, str] | None:
    """Return configured Test Mode credentials without ever exposing the secret."""
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if not key_id.startswith("rzp_test_") or not key_secret:
        return None
    return key_id, key_secret


def razorpay_test_available() -> bool:
    """Whether this process can safely offer Razorpay Test Mode checkout."""
    return get_test_mode_credentials() is not None


def get_razorpay_client() -> tuple[razorpay.Client, str]:
    credentials = get_test_mode_credentials()
    if not credentials:
        raise PaymentIntegrationUnavailable("Razorpay Test Mode credentials are unavailable.")

    key_id, key_secret = credentials
    return razorpay.Client(auth=(key_id, key_secret)), key_id


def cart_total_to_paise(total_inr: object) -> int:
    """Convert a server-calculated INR total to Razorpay's paise amount."""
    try:
        amount = Decimal(str(total_inr)) * 100
    except (InvalidOperation, ValueError) as error:
        raise PaymentProviderError("The server cart total is invalid.") from error

    if amount <= 0 or amount != amount.to_integral_value():
        raise PaymentProviderError("The server cart total is invalid.")
    return int(amount)


def create_test_order(cart_summary: dict) -> dict:
    """Create a Razorpay Test Mode order from the trusted cart total only."""
    client, key_id = get_razorpay_client()
    amount_paise = cart_total_to_paise(cart_summary.get("total"))
    receipt = f"novacart_{uuid4().hex[:20]}"
    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "notes": {"integration_mode": "test", "source": "novacart_checkout"},
    }

    try:
        order = client.order.create(data=order_data)
    except Exception as error:
        raise PaymentProviderError("Razorpay Test Mode order creation failed.") from error

    order_id = str(order.get("id") or "")
    if not order_id:
        raise PaymentProviderError("Razorpay did not return an order ID.")

    return {
        "key_id": key_id,
        "order_id": order_id,
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
    }


def verify_test_payment(payment_details: dict) -> None:
    """Verify a Razorpay Checkout signature using the server-only key secret."""
    client, _ = get_razorpay_client()
    try:
        client.utility.verify_payment_signature(payment_details)
    except Exception as error:
        raise PaymentVerificationFailed("Razorpay payment signature verification failed.") from error
