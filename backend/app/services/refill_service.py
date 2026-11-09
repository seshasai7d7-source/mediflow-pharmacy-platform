
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Prescription,
    RefillPlan,
    RefillRequest,
)
from app.services.order_service import create_order_from_prescription


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_refill_plan(
    db: Session,
    customer_id: int,
    prescription_id: int,
    interval_days: int,
) -> RefillPlan:
    """Create a refill plan request for an approved customer prescription."""

    try:
        prescription = db.scalar(
            select(Prescription).where(
                Prescription.id == prescription_id,
                Prescription.customer_id == customer_id,
            )
        )

        if prescription is None:
            raise ValueError("Prescription not found.")

        if prescription.status != "approved":
            raise ValueError(
                "Only pharmacist-approved prescriptions can have refill plans."
            )

        existing_plan = db.scalar(
            select(RefillPlan).where(
                RefillPlan.customer_id == customer_id,
                RefillPlan.prescription_id == prescription_id,
                RefillPlan.status.in_(
                    ["pending_review", "active", "paused"]
                ),
            )
        )

        if existing_plan is not None:
            raise ValueError(
                "A refill plan already exists for this prescription."
            )

        plan = RefillPlan(
            customer_id=customer_id,
            prescription_id=prescription_id,
            interval_days=interval_days,
            status="pending_review",
        )

        db.add(plan)
        db.flush()

        db.add(
            AuditLog(
                actor_id=customer_id,
                action="refill.plan_requested",
                entity_type="refill_plan",
                entity_id=plan.id,
                details={
                    "prescription_id": prescription_id,
                    "interval_days": interval_days,
                },
            )
        )

        db.commit()
        db.refresh(plan)

        return plan

    except Exception:
        db.rollback()
        raise


def review_refill_plan(
    db: Session,
    plan_id: int,
    pharmacist_id: int,
    decision: str,
    review_note: str | None = None,
) -> RefillPlan:
    """Approve or reject a customer's refill plan."""

    try:
        plan = db.scalar(
            select(RefillPlan)
            .where(RefillPlan.id == plan_id)
            .with_for_update()
        )

        if plan is None:
            raise ValueError("Refill plan not found.")

        if plan.status != "pending_review":
            raise ValueError(
                "Refill plan has already been reviewed."
            )

        if decision not in {"approved", "rejected"}:
            raise ValueError("Invalid refill plan decision.")

        prescription = db.scalar(
            select(Prescription).where(
                Prescription.id == plan.prescription_id,
                Prescription.customer_id == plan.customer_id,
            )
        )

        if prescription is None or prescription.status != "approved":
            raise ValueError(
                "The associated prescription is no longer approved."
            )

        now = _now()

        plan.status = (
            "active" if decision == "approved" else "rejected"
        )
        plan.reviewed_by = pharmacist_id
        plan.reviewed_at = now
        plan.review_note = review_note

        if decision == "approved":
            plan.next_refill_at = now + timedelta(
                days=plan.interval_days
            )

        db.add(
            AuditLog(
                actor_id=pharmacist_id,
                action=f"refill.plan_{decision}",
                entity_type="refill_plan",
                entity_id=plan.id,
                details={
                    "review_note": review_note,
                },
            )
        )

        db.commit()
        db.refresh(plan)

        return plan

    except Exception:
        db.rollback()
        raise


def create_refill_request(
    db: Session,
    customer_id: int,
    plan_id: int,
) -> RefillRequest:
    """Submit a refill request when an approved plan becomes due."""

    try:
        plan = db.scalar(
            select(RefillPlan)
            .where(
                RefillPlan.id == plan_id,
                RefillPlan.customer_id == customer_id,
            )
            .with_for_update()
        )

        if plan is None:
            raise ValueError("Refill plan not found.")

        if plan.status != "active":
            raise ValueError("Refill plan is not active.")

        if plan.next_refill_at is None:
            raise ValueError("Refill schedule is not available.")

        now = _now()
        next_refill_at = plan.next_refill_at

        # SQLite may return a naive datetime in tests.
        if next_refill_at.tzinfo is None:
            next_refill_at = next_refill_at.replace(
                tzinfo=timezone.utc
            )

        if next_refill_at > now:
            raise ValueError(
                "The next refill date has not arrived."
            )

        existing_request = db.scalar(
            select(RefillRequest)
            .where(
                RefillRequest.plan_id == plan_id,
                RefillRequest.status == "pending_review",
            )
            .with_for_update()
        )

        if existing_request is not None:
            raise ValueError(
                "A refill request is already awaiting review."
            )

        refill_request = RefillRequest(
            plan_id=plan_id,
            status="pending_review",
        )

        db.add(refill_request)
        db.flush()

        db.add(
            AuditLog(
                actor_id=customer_id,
                action="refill.requested",
                entity_type="refill_request",
                entity_id=refill_request.id,
                details={
                    "plan_id": plan_id,
                },
            )
        )

        db.commit()
        db.refresh(refill_request)

        return refill_request

    except Exception:
        db.rollback()
        raise


def approve_refill_request(
    db: Session,
    request_id: int,
    pharmacist_id: int,
    review_note: str | None = None,
) -> dict:
    """Approve a pending refill request and create its order atomically."""

    try:
        refill_request = db.scalar(
            select(RefillRequest)
            .where(RefillRequest.id == request_id)
            .with_for_update()
        )

        if refill_request is None:
            raise ValueError("Refill request not found.")

        if refill_request.status != "pending_review":
            raise ValueError(
                "Refill request has already been reviewed."
            )

        plan = db.scalar(
            select(RefillPlan)
            .where(RefillPlan.id == refill_request.plan_id)
            .with_for_update()
        )

        if plan is None:
            raise ValueError("Refill plan not found.")

        if plan.status != "active":
            raise ValueError("Refill plan is not active.")

        prescription = db.scalar(
            select(Prescription)
            .where(
                Prescription.id == plan.prescription_id,
                Prescription.customer_id == plan.customer_id,
            )
            .with_for_update()
        )

        if prescription is None:
            raise ValueError("Prescription not found.")

        if prescription.status != "approved":
            raise ValueError(
                "The associated prescription is no longer approved."
            )

        now = _now()

        if plan.next_refill_at is None:
            raise ValueError("Refill schedule is not available.")

        next_refill_at = plan.next_refill_at

        if next_refill_at.tzinfo is None:
            next_refill_at = next_refill_at.replace(
                tzinfo=timezone.utc
            )

        if next_refill_at > now:
            raise ValueError(
                "The next refill date has not arrived."
            )

        # Create the order and reserve inventory without committing.
        order = create_order_from_prescription(
            db=db,
            customer_id=plan.customer_id,
            prescription_id=plan.prescription_id,
            is_refill_order=True,
            commit=False,
        )

        # Update the refill request.
        refill_request.status = "approved"
        refill_request.reviewed_by = pharmacist_id
        refill_request.reviewed_at = now
        refill_request.review_note = (
            review_note
            if review_note is not None
            else "Approved by pharmacist."
        )
        refill_request.order_id = order["id"]

        # Schedule the next refill interval.
        plan.next_refill_at = now + timedelta(
            days=plan.interval_days
        )

        db.add(
            AuditLog(
                actor_id=pharmacist_id,
                action="refill.request_approved",
                entity_type="refill_request",
                entity_id=refill_request.id,
                details={
                    "plan_id": plan.id,
                    "prescription_id": plan.prescription_id,
                    "order_id": order["id"],
                    "review_note": review_note,
                },
            )
        )

        db.add(
            AuditLog(
                actor_id=pharmacist_id,
                action="order.created_from_refill",
                entity_type="order",
                entity_id=order["id"],
                details={
                    "refill_request_id": refill_request.id,
                    "refill_plan_id": plan.id,
                },
            )
        )

        # Commit request, plan, order, stock, and audit records together.
        db.commit()

        db.refresh(refill_request)
        db.refresh(plan)

        return {
            "refill_request": {
                "id": refill_request.id,
                "plan_id": refill_request.plan_id,
                "status": refill_request.status,
                "reviewed_by": refill_request.reviewed_by,
                "reviewed_at": refill_request.reviewed_at,
                "review_note": refill_request.review_note,
                "order_id": refill_request.order_id,
                "created_at": refill_request.created_at,
            },
            "order": order,
        }

    except Exception:
        db.rollback()
        raise


def update_refill_plan_status(
    db: Session,
    customer_id: int,
    plan_id: int,
    new_status: str,
) -> RefillPlan:
    """Allow a customer to pause, resume, or cancel their own plan."""

    try:
        plan = db.scalar(
            select(RefillPlan)
            .where(
                RefillPlan.id == plan_id,
                RefillPlan.customer_id == customer_id,
            )
            .with_for_update()
        )

        if plan is None:
            raise ValueError("Refill plan not found.")

        if plan.status not in {"active", "paused"}:
            raise ValueError(
                "Only active or paused refill plans can be changed."
            )

        if new_status not in {"active", "paused", "cancelled"}:
            raise ValueError("Invalid refill plan status.")

        if new_status == "active" and plan.status != "paused":
            raise ValueError("Only paused plans can be resumed.")

        if new_status == "paused" and plan.status != "active":
            raise ValueError("Only active plans can be paused.")

        plan.status = new_status

        cancelled_requests = []

        if new_status in {"paused", "cancelled"}:
            pending_requests = db.scalars(
                select(RefillRequest)
                .where(
                    RefillRequest.plan_id == plan_id,
                    RefillRequest.status == "pending_review",
                )
                .with_for_update()
            ).all()

            now = _now()

            for refill_request in pending_requests:
                refill_request.status = "cancelled"
                refill_request.reviewed_at = now
                refill_request.review_note = (
                    f"Automatically cancelled because the refill plan was {new_status}."
                )
                cancelled_requests.append(refill_request.id)

                db.add(
                    AuditLog(
                        actor_id=customer_id,
                        action="refill.request_cancelled",
                        entity_type="refill_request",
                        entity_id=refill_request.id,
                        details={
                            "plan_id": plan.id,
                            "reason": f"plan_{new_status}",
                        },
                    )
                )

        db.add(
            AuditLog(
                actor_id=customer_id,
                action=f"refill.plan_{new_status}",
                entity_type="refill_plan",
                entity_id=plan.id,
                details={
                    "cancelled_request_ids": cancelled_requests,
                },
            )
        )

        db.commit()
        db.refresh(plan)

        return plan

    except Exception:
        db.rollback()
        raise
