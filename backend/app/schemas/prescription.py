from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class PrescriptionUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    mime_type: str
    status: Literal[
        "uploaded",
        "processing",
        "reupload_required",
        "approved",
        "rejected",
    ]
    ai_extraction_json: dict[str, Any] | None = None
    created_at: datetime