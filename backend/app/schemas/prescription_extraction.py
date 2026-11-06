
from pydantic import BaseModel, ConfigDict, Field


class ExtractedMedicine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medicine_name: str
    strength: str | None = None
    dosage: str | None = None
    quantity: int | None = Field(default=None, gt=0)


class PrescriptionExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medicines: list[ExtractedMedicine] = Field(default_factory=list)
    needs_manual_review: bool = True
    unreadable_reason: str | None = None
    extraction_notes: str | None = None
