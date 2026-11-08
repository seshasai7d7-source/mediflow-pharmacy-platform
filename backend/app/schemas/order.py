
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    prescription_id: int = Field(gt=0)
    customer_latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
    )
    customer_longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
    )


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medicine_id: int
    quantity: int
    unit_price: Decimal


class OrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    store_id: int | None
    prescription_id: int | None
    status: Literal[
        "pending_review",
        "confirmed",
        "preparing",
        "ready",
        "dispatched",
        "delivered",
        "cancelled",
    ]
    total_amount: Decimal
    created_at: datetime
    items: list[OrderItemResponse] = Field(default_factory=list)

class OrderStatusUpdate(BaseModel):
    status: Literal[
        "preparing",
        "ready",
        "dispatched",
        "delivered",
        "cancelled",
    ]