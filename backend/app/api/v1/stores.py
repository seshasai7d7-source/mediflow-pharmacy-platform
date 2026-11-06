
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models import Store, User
from app.schemas.inventory import StoreCreate, StoreResponse


router = APIRouter(prefix="/stores", tags=["Stores"])


@router.post(
    "",
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_store(
    store_data: StoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    store = Store(
        name=store_data.name,
        address=store_data.address,
        city=store_data.city,
        pincode=store_data.pincode,
        latitude=store_data.latitude,
        longitude=store_data.longitude,
        is_active=True,
    )

    try:
        db.add(store)
        db.commit()
        db.refresh(store)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create store due to a database conflict.",
        )

    return store


@router.get("", response_model=list[StoreResponse])
def list_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stores = db.scalars(
        select(Store)
        .where(Store.is_active.is_(True))
        .order_by(Store.name)
    ).all()

    return stores
