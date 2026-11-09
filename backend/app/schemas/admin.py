
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.inventory import StoreResponse
from app.schemas.user import UserResponse


class AdminUserUpdate(BaseModel):
    role: Literal["customer", "pharmacist", "admin"] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if self.role is None and self.is_active is None:
            raise ValueError("At least one field must be provided.")
        return self


class AdminUserListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    users: list[UserResponse]
    total: int


class AdminStoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    address: str | None = Field(default=None, min_length=5, max_length=300)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    pincode: str | None = Field(default=None, min_length=4, max_length=10)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        required_fields = {"name", "address", "city", "pincode"}
        for field in required_fields.intersection(self.model_fields_set):
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")

        return self


class AdminStoreListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stores: list[StoreResponse]
    total: int


class AdminPlatformOverviewResponse(BaseModel):
    users: dict[str, int]
    stores: dict[str, int]
    orders: dict[str, int]
    prescriptions: dict[str, int]
    inventory: dict[str, int]
