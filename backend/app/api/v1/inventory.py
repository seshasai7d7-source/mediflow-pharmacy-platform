
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.schemas.inventory import (
    MedicineCatalogueResponse,
    StoreRoutingRequest,
    StoreRoutingResult,
)
from app.services.inventory_service import find_available_stores
from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models import Inventory, Medicine, Store, User
from app.schemas.inventory import InventoryImportResponse
from app.services.inventory_service import import_inventory_csv
from app.services.inventory_service import reserve_inventory

router = APIRouter(prefix="/inventory", tags=["Inventory"])

MAX_CSV_SIZE = 5 * 1024 * 1024


@router.get(
    "/catalogue",
    response_model=MedicineCatalogueResponse,
)
def browse_medicine_catalogue(
    search: str | None = Query(default=None, max_length=200),
    store_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
):
    if store_id is not None:
        store = db.scalar(
            select(Store).where(
                Store.id == store_id,
                Store.is_active.is_(True),
            )
        )
        if store is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found or inactive.",
            )

    filters = [Medicine.is_active.is_(True)]
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            func.lower(Medicine.name).like(func.lower(pattern))
            | func.lower(func.coalesce(Medicine.generic_name, "")).like(
                func.lower(pattern)
            )
            | func.lower(func.coalesce(Medicine.brand_name, "")).like(
                func.lower(pattern)
            )
        )

    count = db.scalar(
        select(func.count(Medicine.id)).where(*filters)
    ) or 0

    medicines = db.scalars(
        select(Medicine)
        .where(*filters)
        .order_by(Medicine.name.asc(), Medicine.id.asc())
        .offset(skip)
        .limit(limit)
    ).all()

    medicine_ids = [medicine.id for medicine in medicines]
    availability_query = (
        select(Inventory, Store)
        .join(Store, Inventory.store_id == Store.id)
        .where(
            Inventory.medicine_id.in_(medicine_ids),
            Store.is_active.is_(True),
        )
    )
    if store_id is not None:
        availability_query = availability_query.where(Store.id == store_id)

    availability_rows = db.execute(availability_query).all()
    availability: dict[int, list[dict]] = {
        medicine.id: [] for medicine in medicines
    }
    for inventory, store in availability_rows:
        unreserved = (
            inventory.available_quantity - inventory.reserved_quantity
        )
        availability[inventory.medicine_id].append({
            "store_id": store.id,
            "store_name": store.name,
            "city": store.city,
            "available_quantity": max(unreserved, 0),
            "is_available": unreserved > 0,
        })

    items = []
    for medicine in medicines:
        stores = availability[medicine.id]
        if store_id is not None and not stores:
            stores = [{
                "store_id": store_id,
                "store_name": store.name,
                "city": store.city,
                "available_quantity": 0,
                "is_available": False,
            }]

        total_available = sum(
            store_availability["available_quantity"]
            for store_availability in stores
        )
        items.append({
            "id": medicine.id,
            "name": medicine.name,
            "generic_name": medicine.generic_name,
            "brand_name": medicine.brand_name,
            "strength": medicine.strength,
            "dosage_form": medicine.dosage_form,
            "schedule_category": medicine.schedule_category,
            "requires_prescription": medicine.requires_prescription,
            "available_quantity": total_available,
            "is_available": total_available > 0,
            "stores": stores,
        })

    return {
        "items": items,
        "total": count,
        "skip": skip,
        "limit": limit,
    }


@router.post(
    "/import",
    response_model=InventoryImportResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_inventory_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "pharmacist")),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported.",
        )

    content = await file.read(MAX_CSV_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The CSV file is empty.",
        )

    if len(content) > MAX_CSV_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="CSV file exceeds the 5 MB size limit.",
        )

    try:
        result = import_inventory_csv(db, content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return result


@router.post(
    "/route",
    response_model=list[StoreRoutingResult],
)
def route_to_available_store(
    request: StoreRoutingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
):
    try:
        customer_latitude = getattr(request, "customer_latitude", None)
        customer_longitude = getattr(request, "customer_longitude", None)

        # Preserve compatibility when customer coordinates are not provided.
        if customer_latitude is None and customer_longitude is None:
            return find_available_stores(
                db,
                request.medicine_id,
                request.quantity,
            )

        return find_available_stores(
            db=db,
            medicine_id=request.medicine_id,
            quantity=request.quantity,
            customer_latitude=customer_latitude,
            customer_longitude=customer_longitude,
        )

    except ValueError as exc:
        message = str(exc)

        if message in (
            "Medicine not found.",
            "Medicine not found or inactive.",
        ):
            error_status = status.HTTP_404_NOT_FOUND
        else:
            error_status = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=error_status,
            detail=message,
        ) from exc


@router.post("/reserve")
def reserve_store_inventory(
    store_id: int,
    request: StoreRoutingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
):
    try:
        result = reserve_inventory(
            db=db,
            store_id=store_id,
            medicine_id=request.medicine_id,
            quantity=request.quantity,
        )
        return result

    except ValueError as exc:
        message = str(exc)

        if message == "Insufficient available stock.":
            error_status = status.HTTP_409_CONFLICT
        elif message == "Inventory record not found.":
            error_status = status.HTTP_404_NOT_FOUND
        else:
            error_status = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=error_status,
            detail=message,
        )
