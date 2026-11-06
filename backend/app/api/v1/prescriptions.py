
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models import Prescription, User
from app.schemas.prescription import PrescriptionUploadResponse
from app.services.prescription_storage import (
    STORAGE_DIR,
    save_prescription_file,
)
from app.services.gemini_extraction import extract_prescription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.post(
    "/upload",
    response_model=PrescriptionUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_prescription(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can upload prescriptions.",
        )

    storage_key, file_bytes = await save_prescription_file(file)

    mime_type = file.content_type or "application/octet-stream"

    # AI extraction is a draft only. It never approves a prescription.
    try:
        extraction = await run_in_threadpool(
            extract_prescription,
            file_bytes,
            mime_type,
        )
        extraction_data = extraction.model_dump(mode="json")

    except Exception:
        logger.exception(
            "Gemini extraction failed for an uploaded prescription."
        )

        # Preserve the upload even when the AI service is unavailable.
        extraction_data = {
            "medicines": [],
            "needs_manual_review": True,
            "unreadable_reason": None,
            "extraction_notes": (
                "AI extraction unavailable. "
                "Pharmacist review is required."
            ),
        }

    prescription = Prescription(
        customer_id=current_user.id,
        file_object_key=storage_key,
        original_filename=file.filename or "prescription",
        mime_type=mime_type,
        status="uploaded",
        ai_extraction_json=extraction_data,
    )

    try:
        db.add(prescription)
        db.commit()
        db.refresh(prescription)

    except Exception:
        db.rollback()

        stored_file = Path(STORAGE_DIR) / Path(storage_key).name
        stored_file.unlink(missing_ok=True)

        logger.exception("Failed to save prescription record.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save prescription record.",
        )

    return prescription
