import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest

os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(tempfile.mkdtemp()) / "test.db")
os.environ["PAYMENT_MODE"] = "demo"
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app import paypal
from app.config import settings, Settings


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def order(client):
    response = client.post("/api/orders", json={"brief": "Help a small coffee company reach its first twenty subscribers."})
    assert response.status_code == 201
    data = response.json()
    return f"/api/orders/{data['id']}", {"Authorization": "Bearer " + data["access_token"]}


def paid_order(client):
    url, headers = order(client)
    assert client.post(url + "/checkout", headers=headers).json()["status"] == "paid"
    return url, headers


def test_complete_success_and_refund_denied(client):
    url, headers = paid_order(client)
    result = client.post(url + "/deliver", headers=headers, json={"scenario": "success"})
    assert result.status_code == 200
    data = result.json()
    assert data["evaluation"]["format_pass"] is True
    assert data["evaluation"]["quality_pass"] is True
    assert data["evaluation"]["evaluator"] == "demo-fixture"
    assert data["refund_cents"] == 0
    assert client.post(url + "/refund", headers=headers).status_code == 409


def test_breach_refunds_exactly_once_even_with_concurrent_retries(client):
    url, headers = paid_order(client)
    result = client.post(url + "/deliver", headers=headers, json={"scenario": "breach"}).json()
    assert result["evaluation"]["refund_percent"] == 50
    assert result["refund_cents"] == 600
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda _: client.post(url + "/refund", headers=headers), range(3)))
    assert all(response.status_code == 200 for response in responses)
    results = [response.json() for response in responses]
    assert len({result["refund_id"] for result in results}) == 1
    final = client.get(url, headers=headers).json()
    assert len([event for event in final["events"] if event["kind"] == "refund"]) == 1
    assert client.post(url + "/deliver", headers=headers, json={"scenario": "success"}).json()["delivery"] == final["delivery"]


def test_access_and_payment_gate(client):
    url, headers = order(client)
    assert client.get(url).status_code == 404
    assert client.post(url + "/checkout", headers={"Authorization": "Bearer wrong"}).status_code == 404
    assert client.post(url + "/deliver", headers=headers, json={}).status_code == 409
    assert client.post(url + "/refund", headers=headers).status_code == 409
    assert client.post(url + "/capture", headers=headers).status_code == 409
    assert client.post("/api/orders", json={"brief": "tiny", "price_cents": 1}).status_code == 422


def test_payment_and_delivery_retries_do_not_duplicate_events(client):
    url, headers = paid_order(client)
    a = client.post(url + "/checkout", headers=headers).json()
    assert len([event for event in a["events"] if event["kind"] == "payment"]) == 1
    a = client.post(url + "/deliver", headers=headers, json={}).json()
    b = client.post(url + "/deliver", headers=headers, json={}).json()
    assert a["events"] == b["events"]


def test_auto_refund_uses_committed_policy(client, monkeypatch):
    monkeypatch.setattr(settings(), "auto_refund", True)
    url, headers = paid_order(client)
    data = client.post(url + "/deliver", headers=headers, json={"scenario": "breach"}).json()
    assert data["status"] == "refunded"
    assert data["refund_cents"] == 600


def sandbox(monkeypatch):
    monkeypatch.setattr(settings(), "payment_mode", "sandbox")
    monkeypatch.setattr(settings(), "operator_token", "x" * 40)


def test_sandbox_checkout_capture_and_wrong_amount(client, monkeypatch):
    sandbox(monkeypatch)
    monkeypatch.setattr(paypal, "create", lambda _: {"id": "PAYPAL-123", "links": [{"rel": "payer-action", "href": "https://www.sandbox.paypal.com/checkoutnow?token=PAYPAL-123"}]})
    url, headers = order(client)
    checkout = client.post(url + "/checkout", headers=headers).json()
    assert checkout["status"] == "awaiting_approval"
    monkeypatch.setattr(paypal, "capture", lambda _: {"status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"id": "CAP-123", "status": "COMPLETED", "amount": {"value": "1.00", "currency_code": "USD"}}]}}]})
    assert client.post(url + "/capture", headers=headers).status_code == 409
    assert client.get(url, headers=headers).json()["status"] == "awaiting_approval"
    monkeypatch.setattr(paypal, "capture", lambda _: {"status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"id": "CAP-123", "status": "COMPLETED", "amount": {"value": "12.00", "currency_code": "USD"}}]}}]})
    assert client.post(url + "/capture", headers=headers).json()["capture_id"] == "CAP-123"
    assert client.post(url + "/deliver", headers=headers, json={}).status_code == 403
    assert client.post(url + "/deliver", headers={**headers, "X-Operator-Token": "x"*40}, json={"scenario": "breach"}).status_code == 422


def test_provider_timeout_leaves_refund_retryable(client, monkeypatch):
    url, headers = paid_order(client)
    client.post(url + "/deliver", headers=headers, json={"scenario": "breach"})
    from app.db import Session, Order
    with Session() as db:
        row = db.get(Order, url.rsplit("/", 1)[-1])
        row.mode = "sandbox"
        db.commit()
    def fail(_):
        raise HTTPException(502, "Provider timed out")
    monkeypatch.setattr(paypal, "refund", fail)
    assert client.post(url + "/refund", headers=headers).status_code == 502
    assert client.get(url, headers=headers).json()["status"] == "evaluated"
    monkeypatch.setattr(paypal, "refund", lambda _: {"id": "REF-123", "status": "PENDING"})
    assert client.post(url + "/refund", headers=headers).json()["status"] == "refund_pending"


def test_bad_judge_output_fails_closed(client, monkeypatch):
    url, headers = paid_order(client)
    sandbox(monkeypatch)
    from app.db import Session, Order
    with Session() as db:
        row = db.get(Order, url.rsplit("/", 1)[-1])
        row.mode = "sandbox"
        db.commit()
    import app.quality as quality
    monkeypatch.setattr(quality, "llm", lambda *args, **kwargs: 'not a valid verdict')
    response = client.post(url + "/deliver", headers={**headers, "X-Operator-Token": "x"*40}, json={})
    assert response.status_code == 502
    stored = client.get(url, headers=headers).json()
    assert stored["evaluation"] is None
    assert stored["refund_cents"] == 0
    assert stored["status"] == "paid"


def test_demo_never_calls_paypal(client, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Demo must not call a payment provider")
    monkeypatch.setattr(paypal, "call", unexpected)
    url, headers = paid_order(client)
    client.post(url + "/deliver", headers=headers, json={"scenario": "breach"})
    assert client.post(url + "/refund", headers=headers).json()["status"] == "refunded"


def test_settings_reject_live_payments_and_incomplete_sandbox():
    with pytest.raises(ValueError):
        Settings(payment_mode="live", _env_file=None)
    with pytest.raises(ValueError):
        Settings(payment_mode="sandbox", _env_file=None)


def test_sandbox_end_to_end_with_mocked_providers(client, monkeypatch):
    sandbox(monkeypatch)
    monkeypatch.setattr(paypal, "create", lambda _: {"id": "PAYPAL-ABC", "links": [{"rel": "approve", "href": "https://www.sandbox.paypal.com/checkoutnow?token=PAYPAL-ABC"}]})
    monkeypatch.setattr(paypal, "capture", lambda _: {"status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"id": "CAP-ABC", "status": "COMPLETED", "amount": {"value": "12.00", "currency_code": "USD"}}]}}]})
    import app.quality as quality
    replies = iter(["Audience\nToo short.\nValue\nUseful.\nAction\nSubscribe.", '{"relevance":85,"clarity":85,"usefulness":85,"explanation":"Relevant but much too short."}'])
    monkeypatch.setattr(quality, "llm", lambda *args, **kwargs: next(replies))
    refunded = []
    def provider_refund(order):
        refunded.append((order.capture_id, order.refund_cents))
        return {"id": "REF-ABC", "status": "COMPLETED"}
    monkeypatch.setattr(paypal, "refund", provider_refund)
    url, headers = order(client)
    client.post(url + "/checkout", headers=headers)
    client.post(url + "/capture", headers=headers)
    headers["X-Operator-Token"] = "x"*40
    data = client.post(url + "/deliver", headers=headers, json={}).json()
    assert data["evaluation"]["evaluator"] == "azure-openai"
    assert data["refund_cents"] == 300
    assert client.post(url + "/refund", headers=headers).json()["status"] == "refunded"
    client.post(url + "/refund", headers=headers)
    assert refunded == [("CAP-ABC", 300)]


def test_paypal_http_adapter_sandbox_origin_and_stable_request_id(monkeypatch):
    import httpx
    requests = []
    def handle(request):
        requests.append(request)
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "test-access"})
        return httpx.Response(201, json={"id": "REF-HTTP", "status": "COMPLETED"})
    actual_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: actual_client(transport=httpx.MockTransport(handle), **kwargs))
    result = paypal.call("/v2/payments/captures/CAP-HTTP/refund", {"amount": {"currency_code": "USD", "value": "6.00"}}, "refund-stable")
    assert result["id"] == "REF-HTTP"
    assert all(r.url.host == "api-m.sandbox.paypal.com" for r in requests)
    assert requests[1].headers["PayPal-Request-Id"] == "refund-stable"
    assert requests[1].headers["Authorization"] == "Bearer test-access"
