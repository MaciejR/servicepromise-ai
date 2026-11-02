import hashlib
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session as DbSession
from . import paypal
from .config import settings
from .db import Base, Order, engine, event, session
from .quality import POLICY, evaluate, generate
from .catalog.routes import router as catalog_router, start_worker


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    stop, worker = start_worker()
    try:
        yield
    finally:
        stop.set()
        if worker:
            worker.join(timeout=5)


app = FastAPI(title="ServicePromise AI", version="0.1.0", lifespan=lifespan)
app.include_router(catalog_router)
app.add_middleware(CORSMiddleware, allow_origins=settings().cors_origins.split(","),
                   allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "X-Operator-Token"])


class NewOrder(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    brief: str = Field(min_length=20, max_length=3000)


class DeliveryRequest(BaseModel):
    scenario: str = Field(default="success", pattern="^(success|breach)$")


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def owned(order_id, db, authorization, lock=False):
    # SQLite has no SELECT FOR UPDATE: serialize writes before reading state.
    # PostgreSQL locks the order row instead. Locks cover provider call + state commit.
    if lock and engine.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    query = select(Order).where(Order.id == order_id)
    order = db.scalar(query.with_for_update() if lock else query)
    token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
    if not order or not secrets.compare_digest(order.token_hash, digest(token)):
        raise HTTPException(404, "Order not found")
    return order


def operator(value):
    cfg = settings()
    if cfg.payment_mode == "sandbox" and not secrets.compare_digest(value, cfg.operator_token):
        raise HTTPException(403, "Sandbox delivery and refunds require the operator token")


def view(order):
    return {k: getattr(order, k) for k in ["id", "mode", "status", "brief", "price_cents", "approval_url",
        "paypal_order_id", "capture_id", "refund_id", "delivery", "evaluation", "refund_cents", "events", "created_at"]}


def process_refund(order):
    if order.status in {"refunded", "refund_pending"}:
        return
    if order.status != "evaluated" or not order.evaluation or order.refund_cents <= 0:
        raise HTTPException(409, "A paid, evaluated order with a policy breach is required")
    if order.refund_cents > order.price_cents * POLICY["maximum_refund_percent"] // 100:
        raise HTTPException(409, "Refund exceeds the agreed policy cap")
    if order.mode == "demo":
        order.refund_id = f"DEMO-REFUND-{order.id[:8]}"
        order.status = "refunded"
    else:
        result = paypal.refund(order)
        order.refund_id = result["id"]
        if result.get("status") not in {"COMPLETED", "PENDING"}:
            raise HTTPException(502, "PayPal did not confirm the refund")
        order.status = "refunded" if result["status"] == "COMPLETED" else "refund_pending"
    event(order, "refund", f"{'Simulated refund' if order.mode == 'demo' else 'PayPal sandbox refund'}: ${order.refund_cents / 100:.2f}; {order.status}")


@app.get("/api/health")
def health():
    return {"status": "ok", "payment_mode": settings().payment_mode}


@app.get("/api/config")
def config():
    return {"payment_mode": settings().payment_mode, "policy": POLICY, "auto_refund": settings().auto_refund,
            "ai_mode": "demo-fixture" if settings().payment_mode == "demo" else "azure-openai"}


@app.post("/api/orders", status_code=201)
def new_order(body: NewOrder, db: DbSession = Depends(session)):
    token = secrets.token_urlsafe(32)
    order = Order(id=str(uuid4()), token_hash=digest(token), mode=settings().payment_mode,
                  status="created", brief=body.brief, events=[], price_cents=POLICY["price_cents"])
    event(order, "promise", "Accepted policy v1: 120–220 words; Audience, Value, Action; quality ≥70; refund capped at 50%.")
    db.add(order)
    db.commit()
    return {**view(order), "access_token": token}


@app.get("/api/orders/{order_id}")
def get_order(order_id: str, authorization: str = Header(default=""), db: DbSession = Depends(session)):
    return view(owned(order_id, db, authorization))


@app.post("/api/orders/{order_id}/checkout")
def checkout(order_id: str, authorization: str = Header(default=""), db: DbSession = Depends(session)):
    order = owned(order_id, db, authorization, lock=True)
    if order.status != "created":
        return view(order)
    if order.mode == "demo":
        order.paypal_order_id = f"DEMO-ORDER-{order.id[:8]}"
        order.capture_id = f"DEMO-CAPTURE-{order.id[:8]}"
        order.status = "paid"
        event(order, "payment", "Simulated payment captured: $12.00. No PayPal request was made.")
    else:
        result = paypal.create(order)
        order.paypal_order_id = result["id"]
        order.approval_url = next((x["href"] for x in result.get("links", []) if x["rel"] in {"approve", "payer-action"}), None)
        if not order.approval_url or not order.approval_url.startswith("https://www.sandbox.paypal.com/"):
            raise HTTPException(502, "PayPal did not return a sandbox approval link")
        order.status = "awaiting_approval"
        event(order, "checkout", "Sandbox checkout created; buyer approval required before capture.")
    db.commit()
    return view(order)


@app.post("/api/orders/{order_id}/capture")
def capture(order_id: str, authorization: str = Header(default=""), db: DbSession = Depends(session)):
    order = owned(order_id, db, authorization, lock=True)
    if order.status in {"paid", "evaluated", "refunded", "refund_pending"}:
        return view(order)
    if order.status != "awaiting_approval":
        raise HTTPException(409, "Buyer approval is required")
    result = paypal.capture(order)
    captures = [capture for unit in result.get("purchase_units", []) for capture in unit.get("payments", {}).get("captures", [])]
    if result.get("status") != "COMPLETED" or len(captures) != 1:
        raise HTTPException(409, "Payment is not completed. No delivery is allowed yet.")
    paid = captures[0]
    if paid.get("status") != "COMPLETED" or paid.get("amount") != {"currency_code": "USD", "value": f"{order.price_cents / 100:.2f}"}:
        raise HTTPException(409, "Capture status or amount does not match the order")
    order.capture_id = paid["id"]
    order.status = "paid"
    event(order, "payment", "PayPal Sandbox confirmed capture: $12.00.")
    db.commit()
    return view(order)


@app.post("/api/orders/{order_id}/deliver")
def deliver(order_id: str, body: DeliveryRequest, authorization: str = Header(default=""),
            x_operator_token: str = Header(default=""), db: DbSession = Depends(session)):
    operator(x_operator_token)
    order = owned(order_id, db, authorization, lock=True)
    if order.status in {"evaluated", "refunded", "refund_pending"}:
        return view(order)
    if order.status != "paid":
        raise HTTPException(409, "Capture payment before delivering the service")
    if order.mode == "sandbox" and body.scenario != "success":
        raise HTTPException(422, "Fault injection is only available in demo mode")
    delivery = generate(order.brief, body.scenario)
    result = evaluate(order.brief, delivery, order.mode)
    order.delivery = delivery
    order.evaluation = result
    order.refund_cents = result["refund_cents"]
    order.status = "evaluated"
    event(order, "delivery", f"Service delivered: {result['word_count']} words.")
    event(order, "evaluation", f"Score {result['score']}/100; deterministic policy proposes {result['refund_percent']}% refund; evaluator: {result['evaluator']}.")
    # Commit evidence first: refund retries never regenerate a service or verdict.
    db.commit()
    if settings().auto_refund and order.refund_cents:
        order = owned(order_id, db, authorization, lock=True)
        process_refund(order)
        db.commit()
    return view(order)


@app.post("/api/orders/{order_id}/refund")
def refund(order_id: str, authorization: str = Header(default=""), x_operator_token: str = Header(default=""), db: DbSession = Depends(session)):
    operator(x_operator_token)
    order = owned(order_id, db, authorization, lock=True)
    process_refund(order)
    db.commit()
    return view(order)


# Single-container alternative to Static Web Apps. API routes take precedence.
static = Path(__file__).resolve().parent.parent / "static"
if static.is_dir():
    app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")
