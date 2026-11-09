
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    phone: Mapped[str | None] = mapped_column(
        String(20), unique=True, nullable=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('customer', 'pharmacist', 'admin')",
            name="ck_users_role",
        ),
    )


class Store(TimestampMixin, Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )


class Medicine(TimestampMixin, Base):
    __tablename__ = "medicines"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    generic_name: Mapped[str | None] = mapped_column(String(200))
    brand_name: Mapped[str | None] = mapped_column(String(150))
    strength: Mapped[str | None] = mapped_column(String(100))
    dosage_form: Mapped[str | None] = mapped_column(String(100))
    schedule_category: Mapped[str] = mapped_column(
        String(20), default="UNKNOWN", nullable=False
    )
    requires_prescription: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "schedule_category IN "
            "('OTC', 'H', 'H1', 'X', 'NARCOTIC', 'UNKNOWN')",
            name="ck_medicines_schedule",
        ),
        Index("ix_medicines_name", "name"),
    )


class Inventory(TimestampMixin, Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id"), nullable=False
    )
    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicines.id"), nullable=False
    )
    available_quantity: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    reserved_quantity: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "store_id", "medicine_id", name="uq_inventory_store_medicine"
        ),
        CheckConstraint(
            "available_quantity >= 0 AND reserved_quantity >= 0",
            name="ck_inventory_quantities",
        ),
    )


class Prescription(TimestampMixin, Base):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    pharmacist_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    file_object_key: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(
        String(30), default="uploaded", nullable=False
    )
    ai_extraction_json: Mapped[dict | None] = mapped_column(JSON)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('uploaded', 'processing', 'pending_review', "
            "'approved', 'rejected', 'reupload_required')",
            name="ck_prescriptions_status",
        ),
        Index("ix_prescriptions_customer_status", "customer_id", "status"),
    )


class PrescriptionItem(TimestampMixin, Base):
    __tablename__ = "prescription_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    prescription_id: Mapped[int] = mapped_column(
        ForeignKey("prescriptions.id"), nullable=False
    )
    medicine_id: Mapped[int | None] = mapped_column(
        ForeignKey("medicines.id"), nullable=True
    )
    extracted_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(150))
    quantity: Mapped[int | None] = mapped_column(Integer)
    pharmacist_approved: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    generic_substitution: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    customer_consent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name="ck_prescription_items_quantity",
        ),
    )


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id"), nullable=True
    )
    prescription_id: Mapped[int | None] = mapped_column(
        ForeignKey("prescriptions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="pending_review", nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('pending_review', 'confirmed', 'preparing', "
            "'ready', 'dispatched', 'delivered', 'cancelled')",
            name="ck_orders_status",
        ),
        Index("ix_orders_customer_status", "customer_id", "status"),
    )


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False
    )
    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicines.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_price"),
    )


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))


class RefillPlan(TimestampMixin, Base):
    __tablename__ = "refill_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    prescription_id: Mapped[int] = mapped_column(
        ForeignKey("prescriptions.id"), nullable=False
    )
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="pending_review", nullable=False
    )
    next_refill_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "interval_days BETWEEN 1 AND 365",
            name="ck_refill_plans_interval",
        ),
        CheckConstraint(
            "status IN "
            "('pending_review', 'active', 'paused', 'rejected', 'cancelled')",
            name="ck_refill_plans_status",
        ),
        Index("ix_refill_plans_customer_status", "customer_id", "status"),
    )


class RefillRequest(TimestampMixin, Base):
    __tablename__ = "refill_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("refill_plans.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="pending_review", nullable=False
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('pending_review', 'approved', 'rejected', 'cancelled')",
            name="ck_refill_requests_status",
        ),
        Index("ix_refill_requests_plan_status", "plan_id", "status"),
    )
