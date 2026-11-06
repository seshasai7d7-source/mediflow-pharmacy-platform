
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    role: Literal["customer", "pharmacist", "admin"]
    is_active: bool
    created_at: datetime
