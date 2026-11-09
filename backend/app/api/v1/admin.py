
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models import AuditLog, Inventory, Order, Prescription, Store, User
from app.schemas.admin import (
    AdminPlatformOverviewResponse,
    AdminStoreListResponse,
    AdminStoreUpdate,
    AdminUserListResponse,
    AdminUserUpdate,
)
from app.schemas.user import UserResponse
from app.schemas.inventory import StoreResponse


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    role: str | None = Query(
        default=None,
        pattern="^(customer|pharmacist|admin)$",
    ),
    is_active: bool | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    filters = []

    if search:
        search_term = f"%{search.strip()}%"
        filters.append(
            or_(
                User.full_name.ilike(search_term),
                User.email.ilike(search_term),
            )
        )

    if role is not None:
        filters.append(User.role == role)

    if is_active is not None:
        filters.append(User.is_active.is_(is_active))

    total = db.scalar(
        select(func.count(User.id)).where(*filters)
    ) or 0

    users = db.scalars(
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    return {
        "users": users,
        "total": total,
    }


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
)
def update_user(
    user_id: int,
    update_data: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    changes = update_data.model_dump(exclude_unset=True)

    if user.id == current_user.id and (
        changes.get("role", user.role) != "admin"
        or changes.get("is_active", user.is_active) is False
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own admin role or deactivate your account.",
        )

    old_values = {
        field: getattr(user, field)
        for field in changes
    }

    for field, value in changes.items():
        setattr(user, field, value)

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="user.updated",
            entity_type="user",
            entity_id=user.id,
            details={
                "old_values": old_values,
                "new_values": changes,
            },
        )
    )

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update user.",
        )

    return user


@router.get("/stores", response_model=AdminStoreListResponse)
def list_all_stores(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    filters = []

    if search:
        search_term = f"%{search.strip()}%"
        filters.append(
            or_(
                Store.name.ilike(search_term),
                Store.city.ilike(search_term),
                Store.address.ilike(search_term),
                Store.pincode.ilike(search_term),
            )
        )

    if is_active is not None:
        filters.append(Store.is_active.is_(is_active))

    total = db.scalar(
        select(func.count(Store.id)).where(*filters)
    ) or 0

    stores = db.scalars(
        select(Store)
        .where(*filters)
        .order_by(Store.name, Store.id)
        .offset(skip)
        .limit(limit)
    ).all()

    return {
        "stores": stores,
        "total": total,
    }


@router.get(
    "/stores/{store_id}",
    response_model=StoreResponse,
)
def get_admin_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    store = db.get(Store, store_id)

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found.",
        )

    return store


@router.patch(
    "/stores/{store_id}",
    response_model=StoreResponse,
)
def update_store(
    store_id: int,
    update_data: AdminStoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    store = db.get(Store, store_id)

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found.",
        )

    changes = update_data.model_dump(exclude_unset=True)

    old_values = {
        field: getattr(store, field)
        for field in changes
    }

    for field, value in changes.items():
        setattr(store, field, value)

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="store.updated",
            entity_type="store",
            entity_id=store.id,
            details={
                "old_values": old_values,
                "new_values": changes,
            },
        )
    )

    try:
        db.commit()
        db.refresh(store)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update store.",
        )

    return store

@router.get("/overview", response_model=AdminPlatformOverviewResponse)
def get_platform_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    # User metrics
    total_users = db.scalar(select(func.count(User.id))) or 0
    active_users = db.scalar(
        select(func.count(User.id)).where(User.is_active.is_(True))
    ) or 0

    user_roles = db.execute(
        select(User.role, func.count(User.id)).group_by(User.role)
    ).all()

    users_by_role = {role: count for role, count in user_roles}

    # Store metrics
    total_stores = db.scalar(select(func.count(Store.id))) or 0
    active_stores = db.scalar(
        select(func.count(Store.id)).where(Store.is_active.is_(True))
    ) or 0

    # Order metrics
    total_orders = db.scalar(select(func.count(Order.id))) or 0
    order_statuses = db.execute(
        select(Order.status, func.count(Order.id)).group_by(Order.status)
    ).all()

    orders_by_status = {status: count for status, count in order_statuses}

    # Prescription metrics
    total_prescriptions = db.scalar(
        select(func.count(Prescription.id))
    ) or 0

    prescription_statuses = db.execute(
        select(
            Prescription.status,
            func.count(Prescription.id),
        ).group_by(Prescription.status)
    ).all()

    prescriptions_by_status = {
        status: count for status, count in prescription_statuses
    }

    # Inventory metrics
    inventory_records = db.scalar(
        select(func.count(Inventory.id))
    ) or 0

    available_quantity = db.scalar(
        select(func.coalesce(func.sum(Inventory.available_quantity), 0))
    ) or 0

    reserved_quantity = db.scalar(
        select(func.coalesce(func.sum(Inventory.reserved_quantity), 0))
    ) or 0

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "customers": users_by_role.get("customer", 0),
            "pharmacists": users_by_role.get("pharmacist", 0),
            "admins": users_by_role.get("admin", 0),
        },
        "stores": {
            "total": total_stores,
            "active": active_stores,
            "inactive": total_stores - active_stores,
        },
        "orders": {
            "total": total_orders,
            "pending_review": orders_by_status.get("pending_review", 0),
            "confirmed": orders_by_status.get("confirmed", 0),
            "preparing": orders_by_status.get("preparing", 0),
            "ready": orders_by_status.get("ready", 0),
            "dispatched": orders_by_status.get("dispatched", 0),
            "delivered": orders_by_status.get("delivered", 0),
            "cancelled": orders_by_status.get("cancelled", 0),
        },
        "prescriptions": {
            "total": total_prescriptions,
            "uploaded": prescriptions_by_status.get("uploaded", 0),
            "processing": prescriptions_by_status.get("processing", 0),
            "pending_review": prescriptions_by_status.get("pending_review", 0),
            "approved": prescriptions_by_status.get("approved", 0),
            "rejected": prescriptions_by_status.get("rejected", 0),
            "reupload_required": prescriptions_by_status.get(
                "reupload_required", 0
            ),
        },
        "inventory": {
            "records": inventory_records,
            "available_quantity": available_quantity,
            "reserved_quantity": reserved_quantity,
        },
    }