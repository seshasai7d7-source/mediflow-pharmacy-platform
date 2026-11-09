
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models import User
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services.order_service import (
    create_order_from_prescription,
    get_customer_orders,
    get_customer_order,
    get_all_orders,
    update_order_status,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
):
    try:
        return create_order_from_prescription(
            db=db,
            customer_id=current_user.id,
            prescription_id=order_data.prescription_id,
            customer_latitude=order_data.customer_latitude,
            customer_longitude=order_data.customer_longitude,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Prescription not found.":
            error_status = status.HTTP_404_NOT_FOUND
        elif message == "An active order already exists for this prescription.":
            error_status = status.HTTP_409_CONFLICT
        elif (
            "sufficient stock" in message
            or "Stock changed" in message
        ):
            error_status = status.HTTP_409_CONFLICT
        else:
            error_status = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=error_status,
            detail=message,
        )


@router.get("", response_model=list[OrderResponse])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
):
    return get_customer_orders(db, current_user.id)


# Keep this static route before /{order_id}.
@router.get(
    "/manage",
    response_model=list[OrderResponse],
)
def get_all_orders_for_management(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("pharmacist", "admin")
    ),
):
    return get_all_orders(db)


@router.get("/{order_id}", response_model=OrderResponse)
def get_my_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
):
    order = get_customer_order(
        db,
        current_user.id,
        order_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    return order


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
)
def update_order_status_endpoint(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("pharmacist", "admin")
    ),
):
    try:
        return update_order_status(
            db=db,
            order_id=order_id,
            new_status=status_data.status,
            pharmacist_id=current_user.id,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Order not found.":
            error_status = status.HTTP_404_NOT_FOUND
        else:
            error_status = status.HTTP_409_CONFLICT

        raise HTTPException(
            status_code=error_status,
            detail=message,
        )
