
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PrescriptionQueueItem(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    customer_email: str
    original_filename: str
    mime_type: str
    status: str
    ai_extraction_json: dict[str, Any] | None = None
    created_at: datetime


class PrescriptionReviewMedicine(BaseModel):
    medicine_id: int = Field(gt=0)
    dosage: str | None = None
    quantity: int = Field(gt=0)
    generic_substitution: bool = False
    customer_consent: bool = False

    @model_validator(mode="after")
    def validate_generic_consent(self):
        if self.generic_substitution and not self.customer_consent:
            raise ValueError(
                "Customer consent is required for generic substitution."
            )
        return self


class PrescriptionReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    medicines: list[PrescriptionReviewMedicine] = Field(
        default_factory=list
    )
    rejection_reason: str | None = Field(
        default=None,
        max_length=500
    )

    @model_validator(mode="after")
    def validate_review(self):
        if self.decision == "approved" and not self.medicines:
            raise ValueError(
                "At least one verified medicine is required for approval."
            )

        if self.decision == "rejected" and not self.rejection_reason:
            raise ValueError(
                "A rejection reason is required."
            )

        return self


class PrescriptionReviewResponse(BaseModel):
    id: int
    status: str
    pharmacist_id: int
    rejection_reason: str | None = None
    reviewed_at: datetime

class PrescriptionDetailResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    customer_email: str
    original_filename: str
    mime_type: str
    status: str
    ai_extraction_json: dict[str, Any] | None = None
    rejection_reason: str | None = None
    created_at: datetime


class PrescriptionReviewMedicineResponse(BaseModel):
    id: int
    medicine_id: int | None
    extracted_name: str
    dosage: str | None
    quantity: int | None
    pharmacist_approved: bool
    generic_substitution: bool
    customer_consent: bool


class PrescriptionDetailWithItemsResponse(
    PrescriptionDetailResponse
):
    items: list[PrescriptionReviewMedicineResponse] = Field(
        default_factory=list
    )