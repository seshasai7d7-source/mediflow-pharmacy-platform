
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models import (
    AuditLog,
    Medicine,
    Prescription,
    PrescriptionItem,
    User,
)
from app.schemas.pharmacist import (
    PrescriptionQueueItem,
    PrescriptionDetailWithItemsResponse,
    PrescriptionReviewRequest,
    PrescriptionReviewResponse,
)

router = APIRouter(prefix="/pharmacist", tags=["Pharmacist"])


@router.get(
    "/prescriptions/queue",
    response_model=list[PrescriptionQueueItem],
)
def get_prescription_queue(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_roles("pharmacist")),
    db: Session = Depends(get_db),
):
    statement = (
        select(Prescription, User.full_name, User.email)
        .join(User, Prescription.customer_id == User.id)
        .where(Prescription.status == "uploaded")
        .order_by(Prescription.created_at.asc())
        .offset(offset)
        .limit(limit)
    )

    results = db.execute(statement).all()

    return [
        PrescriptionQueueItem(
            id=prescription.id,
            customer_id=prescription.customer_id,
            customer_name=customer_name,
            customer_email=customer_email,
            original_filename=prescription.original_filename,
            mime_type=prescription.mime_type,
            status=prescription.status,
            ai_extraction_json=prescription.ai_extraction_json,
            created_at=prescription.created_at,
        )
        for prescription, customer_name, customer_email in results
    ]


@router.get(
    "/prescriptions/{prescription_id}",
    response_model=PrescriptionDetailWithItemsResponse,
)
def get_prescription_details(
    prescription_id: int,
    current_user: User = Depends(require_roles("pharmacist")),
    db: Session = Depends(get_db),
):
    prescription = db.get(Prescription, prescription_id)

    if prescription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found.",
        )

    customer = db.get(User, prescription.customer_id)

    items = db.scalars(
        select(PrescriptionItem).where(
            PrescriptionItem.prescription_id == prescription_id
        )
    ).all()

    return PrescriptionDetailWithItemsResponse(
        id=prescription.id,
        customer_id=prescription.customer_id,
        customer_name=customer.full_name,
        customer_email=customer.email,
        original_filename=prescription.original_filename,
        mime_type=prescription.mime_type,
        status=prescription.status,
        ai_extraction_json=prescription.ai_extraction_json,
        rejection_reason=prescription.rejection_reason,
        created_at=prescription.created_at,
        items=[
            {
                "id": item.id,
                "medicine_id": item.medicine_id,
                "extracted_name": item.extracted_name,
                "dosage": item.dosage,
                "quantity": item.quantity,
                "pharmacist_approved": item.pharmacist_approved,
                "generic_substitution": item.generic_substitution,
                "customer_consent": item.customer_consent,
            }
            for item in items
        ],
    )


@router.post(
    "/prescriptions/{prescription_id}/review",
    response_model=PrescriptionReviewResponse,
)
def review_prescription(
    prescription_id: int,
    review: PrescriptionReviewRequest,
    current_user: User = Depends(require_roles("pharmacist")),
    db: Session = Depends(get_db),
):
    # Lock the prescription row to prevent concurrent reviews.
    prescription = db.scalar(
        select(Prescription)
        .where(Prescription.id == prescription_id)
        .with_for_update()
    )

    if prescription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found.",
        )

    if prescription.status != "uploaded":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This prescription has already been reviewed or is not awaiting review.",
        )

    verified_medicines = []

    if review.decision == "approved":
        # Validate every medicine before changing prescription status.
        for item in review.medicines:
            medicine = db.scalar(
                select(Medicine).where(
                    Medicine.id == item.medicine_id,
                    Medicine.is_active.is_(True),
                )
            )

            if medicine is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Active medicine with ID {item.medicine_id} was not found.",
                )

            if medicine.schedule_category in {"X", "NARCOTIC"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"{medicine.name} cannot be approved for online sale "
                        "because it belongs to a prohibited category."
                    ),
                )

            if medicine.schedule_category == "UNKNOWN":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"{medicine.name} has an unknown schedule category. "
                        "Classify it before approval."
                    ),
                )

            verified_medicines.append((item, medicine))

    # Save the pharmacist's verified medicine details.
    if review.decision == "approved":
        for item, medicine in verified_medicines:
            db.add(
                PrescriptionItem(
                    prescription_id=prescription.id,
                    medicine_id=medicine.id,
                    extracted_name=medicine.name,
                    dosage=item.dosage,
                    quantity=item.quantity,
                    pharmacist_approved=True,
                    generic_substitution=item.generic_substitution,
                    customer_consent=item.customer_consent,
                )
            )

        prescription.status = "approved"
        prescription.rejection_reason = None

    else:
        prescription.status = "rejected"
        prescription.rejection_reason = review.rejection_reason

    prescription.pharmacist_id = current_user.id
    prescription.reviewed_at = datetime.now(timezone.utc)

    # Record who performed the review and what decision was made.
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action=f"prescription.{review.decision}",
            entity_type="prescription",
            entity_id=prescription.id,
            details={
                "decision": review.decision,
                "medicine_count": len(verified_medicines),
                "rejection_reason": review.rejection_reason,
            },
        )
    )

    try:
        db.commit()
        db.refresh(prescription)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save the prescription review.",
        )

    return PrescriptionReviewResponse(
        id=prescription.id,
        status=prescription.status,
        pharmacist_id=prescription.pharmacist_id,
        rejection_reason=prescription.rejection_reason,
        reviewed_at=prescription.reviewed_at,
    )
