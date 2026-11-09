
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models import RefillPlan, RefillRequest, User, AuditLog
from app.schemas.refill import (
    RefillPlanCreateRequest,
    RefillPlanReviewRequest,
    RefillPlanResponse,
    RefillRequestCreateResponse,
    RefillRequestReviewRequest,
    RefillRequestResponse,
)
from app.services.refill_service import (
    approve_refill_request,
    create_refill_plan,
    create_refill_request,
    review_refill_plan,
    update_refill_plan_status,
)

router = APIRouter(prefix="/refills", tags=["Refills"])


def handle_refill_error(exc: ValueError):
    message = str(exc)

    if "not found" in message.lower():
        error_status = status.HTTP_404_NOT_FOUND
    elif any(
        term in message.lower()
        for term in (
            "already",
            "not active",
            "not arrived",
            "can be changed",
            "no longer approved",
            "must be approved",
            "requires pharmacist approval",
            "invalid",
            "stock",
            "sufficient",
            "no single store",
        )
    ):
        error_status = status.HTTP_409_CONFLICT
    else:
        error_status = status.HTTP_400_BAD_REQUEST

    raise HTTPException(
        status_code=error_status,
        detail=message,
    )


@router.post(
    "/plans",
    response_model=RefillPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def request_refill_plan(
    plan_data: RefillPlanCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
):
    try:
        return create_refill_plan(
            db=db,
            customer_id=current_user.id,
            prescription_id=plan_data.prescription_id,
            interval_days=plan_data.interval_days,
        )
    except ValueError as exc:
        handle_refill_error(exc)


@router.get(
    "/plans/my",
    response_model=list[RefillPlanResponse],
)
def get_my_refill_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
):
    statement = (
        select(RefillPlan)
        .where(RefillPlan.customer_id == current_user.id)
        .order_by(RefillPlan.created_at.desc())
    )

    return db.scalars(statement).all()


@router.patch(
    "/plans/{plan_id}/status",
    response_model=RefillPlanResponse,
)
def change_refill_plan_status(
    plan_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
):
    try:
        return update_refill_plan_status(
            db=db,
            customer_id=current_user.id,
            plan_id=plan_id,
            new_status=new_status,
        )
    except ValueError as exc:
        handle_refill_error(exc)


@router.get(
    "/plans/queue",
    response_model=list[RefillPlanResponse],
)
def get_pending_refill_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("pharmacist", "admin")
    ),
):
    statement = (
        select(RefillPlan)
        .where(RefillPlan.status == "pending_review")
        .order_by(RefillPlan.created_at.asc())
    )

    return db.scalars(statement).all()


@router.patch(
    "/plans/{plan_id}/review",
    response_model=RefillPlanResponse,
)
def review_refill_plan_endpoint(
    plan_id: int,
    review_data: RefillPlanReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("pharmacist", "admin")
    ),
):
    try:
        return review_refill_plan(
            db=db,
            plan_id=plan_id,
            pharmacist_id=current_user.id,
            decision=review_data.decision,
            review_note=review_data.review_note,
        )
    except ValueError as exc:
        handle_refill_error(exc)


@router.post(
    "/plans/{plan_id}/requests",
    response_model=RefillRequestCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_refill_request(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
):
    try:
        return create_refill_request(
            db=db,
            customer_id=current_user.id,
            plan_id=plan_id,
        )
    except ValueError as exc:
        handle_refill_error(exc)


@router.get(
    "/requests/my",
    response_model=list[RefillRequestResponse],
)
def get_my_refill_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
):
    statement = (
        select(RefillRequest)
        .join(
            RefillPlan,
            RefillRequest.plan_id == RefillPlan.id,
        )
        .where(RefillPlan.customer_id == current_user.id)
        .order_by(RefillRequest.created_at.desc())
    )

    return db.scalars(statement).all()


@router.get(
    "/requests/queue",
    response_model=list[RefillRequestResponse],
)
def get_pending_refill_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("pharmacist", "admin")
    ),
):
    statement = (
        select(RefillRequest)
        .where(RefillRequest.status == "pending_review")
        .order_by(RefillRequest.created_at.asc())
    )

    return db.scalars(statement).all()


@router.patch(
    "/requests/{request_id}/review",
)
def review_refill_request_endpoint(
    request_id: int,
    review_data: RefillRequestReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("pharmacist", "admin")
    ),
):
    try:
        if review_data.decision == "approved":
            return approve_refill_request(
                db=db,
                request_id=request_id,
                pharmacist_id=current_user.id,
                review_note=review_data.review_note,
            )

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

        now = datetime.now(timezone.utc)

        refill_request.status = "rejected"
        refill_request.reviewed_by = current_user.id
        refill_request.reviewed_at = now
        refill_request.review_note = review_data.review_note

        db.add(
            AuditLog(
                actor_id=current_user.id,
                action="refill.request_rejected",
                entity_type="refill_request",
                entity_id=refill_request.id,
                details={
                    "plan_id": plan.id,
                    "review_note": review_data.review_note,
                },
            )
        )

        db.commit()
        db.refresh(refill_request)

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
            "order": None,
        }

    except ValueError as exc:
        db.rollback()
        handle_refill_error(exc)

    except Exception:
        db.rollback()
        raise
