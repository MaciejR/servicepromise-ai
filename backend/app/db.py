from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(24), default="created")
    brief: Mapped[str] = mapped_column(String(3000))
    price_cents: Mapped[int] = mapped_column(Integer, default=1200)
    paypal_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    capture_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    refund_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delivery: Mapped[str | None] = mapped_column(String(20000), nullable=True)
    evaluation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    refund_cents: Mapped[int] = mapped_column(Integer, default=0)
    events: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


cfg = settings()
engine = create_engine(cfg.database_url, connect_args={"check_same_thread": False} if cfg.database_url.startswith("sqlite") else {}, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)


def session():
    with Session() as db:
        yield db


def event(order, kind, message):
    order.events = [*order.events, {"at": now().isoformat(), "kind": kind, "message": message}]
