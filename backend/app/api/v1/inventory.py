
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.schemas.inventory import StoreRoutingRequest, StoreRoutingResult
from app.services.inventory_service import find_available_stores
from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models import User
from app.schemas.inventory import InventoryImportResponse
from app.services.inventory_service import import_inventory_csv
from app.services.inventory_service import reserve_inventory

router = APIRouter(prefix="/inventory", tags=["Inventory"])

MAX_CSV_SIZE = 5 * 1024 * 1024


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
