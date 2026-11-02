"""Sandbox-only adapter. Stable request IDs make capture/refund retries safe."""
import httpx
from fastapi import HTTPException
from .config import settings

BASE_URL = "https://api-m.sandbox.paypal.com"


def call(path, payload, request_id):
    cfg = settings()
    try:
        with httpx.Client(timeout=30) as client:
            auth = client.post(f"{BASE_URL}/v1/oauth2/token", auth=(cfg.paypal_client_id, cfg.paypal_client_secret), data={"grant_type": "client_credentials"})
            auth.raise_for_status()
            response = client.post(f"{BASE_URL}{path}", json=payload, headers={
                "Authorization": f"Bearer {auth.json()['access_token']}",
                "PayPal-Request-Id": request_id,
                "Prefer": "return=representation",
            })
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        # Never return provider payloads or credentials to the browser.
        raise HTTPException(502, "PayPal Sandbox request failed. Retry the same operation; do not create another order.") from exc


def create(order):
    url = settings().public_url.rstrip("/")
    return call("/v2/checkout/orders", {
        "intent": "CAPTURE",
        "purchase_units": [{"reference_id": order.id, "custom_id": order.id,
            "description": "ServicePromise AI — guaranteed content brief (sandbox)",
            "amount": {"currency_code": "USD", "value": f"{order.price_cents / 100:.2f}"}}],
        "payment_source": {"paypal": {"experience_context": {
            "return_url": f"{url}/?order={order.id}&approved=1",
            "cancel_url": f"{url}/?order={order.id}&cancelled=1", "user_action": "PAY_NOW",
        }}},
    }, f"create-{order.id}")


def capture(order):
    return call(f"/v2/checkout/orders/{order.paypal_order_id}/capture", {}, f"capture-{order.id}")


def refund(order):
    return call(f"/v2/payments/captures/{order.capture_id}/refund", {
        "amount": {"currency_code": "USD", "value": f"{order.refund_cents / 100:.2f}"},
        "note_to_payer": "ServicePromise AI: the delivered service did not meet the agreed quality policy.",
    }, f"refund-{order.id}")
