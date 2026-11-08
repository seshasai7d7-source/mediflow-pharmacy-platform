
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StoreCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    address: str = Field(min_length=5, max_length=300)
    city: str = Field(min_length=2, max_length=100)
    pincode: str = Field(min_length=4, max_length=10)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    city: str
    pincode: str
    latitude: float | None
    longitude: float | None
    is_active: bool
    created_at: datetime


class InventoryResponse(BaseModel):
    id: int
    store_id: int
    medicine_id: int
    available_quantity: int
    reserved_quantity: int


class InventoryImportResponse(BaseModel):
    message: str
    records_processed: int
    records_created: int
    records_updated: int
    records_skipped: int


class StoreRoutingRequest(BaseModel):
    medicine_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
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


class StoreRoutingResult(BaseModel):
    store_id: int
    store_name: str
    address: str
    city: str
    available_quantity: int
    distance_km: float | None = None
