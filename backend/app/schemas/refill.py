
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RefillPlanCreateRequest(BaseModel):
    prescription_id: int = Field(gt=0)
    interval_days: int = Field(ge=1, le=365)


class RefillPlanReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=500)


class RefillPlanResponse(BaseModel):
    id: int
    customer_id: int
    prescription_id: int
    interval_days: int
    status: str
    next_refill_at: datetime | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    created_at: datetime


class RefillRequestCreateResponse(BaseModel):
    id: int
    plan_id: int
    status: str
    created_at: datetime


class RefillRequestReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=500)


class RefillRequestResponse(BaseModel):
    id: int
    plan_id: int
    status: str
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    order_id: int | None = None
    created_at: datetime
