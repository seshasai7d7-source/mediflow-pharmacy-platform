
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Inventory,
    Order,
    OrderItem,
    Prescription,
    PrescriptionItem,
    Store,
)
from app.services.inventory_service import calculate_distance_km


def create_order_from_prescription(
    db: Session,
    customer_id: int,
    prescription_id: int,
    customer_latitude: float | None = None,
    customer_longitude: float | None = None,
) -> dict:
    """Create an order using approved items from the nearest eligible store."""

    try:
        # Validate coordinates when supplied.
        if (customer_latitude is None) != (customer_longitude is None):
            raise ValueError(
                "Both customer latitude and longitude must be provided together."
            )

        if customer_latitude is not None and not -90 <= customer_latitude <= 90:
            raise ValueError("Customer latitude must be between -90 and 90.")

        if customer_longitude is not None and not -180 <= customer_longitude <= 180:
            raise ValueError("Customer longitude must be between -180 and 180.")

        prescription = db.scalar(
            select(Prescription)
            .where(
                Prescription.id == prescription_id,
                Prescription.customer_id == customer_id,
            )
            .with_for_update()
        )

        if prescription is None:
            raise ValueError("Prescription not found.")

        if prescription.status != "approved":
            raise ValueError("Prescription must be approved by a pharmacist.")

        existing_order = db.scalar(
            select(Order).where(
                Order.prescription_id == prescription_id,
                Order.status != "cancelled",
            )
        )

        if existing_order:
            raise ValueError(
                "An active order already exists for this prescription."
            )

        items = db.scalars(
            select(PrescriptionItem).where(
                PrescriptionItem.prescription_id == prescription_id
            )
        ).all()

        if not items:
            raise ValueError("Prescription has no verified medicine items.")

        if any(not item.pharmacist_approved for item in items):
            raise ValueError("Every medicine requires pharmacist approval.")

        if any(
            item.medicine_id is None
            or item.quantity is None
            or item.quantity <= 0
            for item in items
        ):
            raise ValueError("Prescription contains invalid medicine details.")

        # Aggregate quantities when a medicine appears more than once.
        medicine_quantities = {}

        for item in items:
            medicine_quantities[item.medicine_id] = (
                medicine_quantities.get(item.medicine_id, 0)
                + item.quantity
            )

        candidate_stores = db.scalars(
            select(Store)
            .where(Store.is_active.is_(True))
            .order_by(Store.id)
        ).all()

        # Rank stores by distance when customer coordinates are available.
        # Stores without coordinates are placed after stores with known distances.
        if customer_latitude is not None and customer_longitude is not None:
            candidate_stores.sort(
                key=lambda store: (
                    store.latitude is None or store.longitude is None,
                    calculate_distance_km(
                        customer_latitude,
                        customer_longitude,
                        store.latitude,
                        store.longitude,
                    )
                    if (
                        store.latitude is not None
                        and store.longitude is not None
                    )
                    else float("inf"),
                )
            )

        selected_store = None
        selected_inventory = None

        # Select the nearest store that can fulfil the complete prescription.
        for store in candidate_stores:
            inventory_rows = db.scalars(
                select(Inventory)
                .where(
                    Inventory.store_id == store.id,
                    Inventory.medicine_id.in_(medicine_quantities.keys()),
                )
                .order_by(Inventory.medicine_id)
                .with_for_update()
            ).all()

            inventory_by_medicine = {
                inventory.medicine_id: inventory
                for inventory in inventory_rows
            }

            has_all_stock = all(
                medicine_id in inventory_by_medicine
                and (
                    inventory_by_medicine[medicine_id].available_quantity
                    - inventory_by_medicine[medicine_id].reserved_quantity
                ) >= quantity
                for medicine_id, quantity in medicine_quantities.items()
            )

            if has_all_stock:
                selected_store = store
                selected_inventory = inventory_by_medicine
                break

        if selected_store is None:
            raise ValueError(
                "No single store has sufficient stock for all medicines."
            )

        # Reserve every medicine atomically within this transaction.
        for medicine_id, quantity in medicine_quantities.items():
            inventory = selected_inventory[medicine_id]

            result = db.execute(
                update(Inventory)
                .where(
                    Inventory.id == inventory.id,
                    Inventory.available_quantity
                    - Inventory.reserved_quantity >= quantity,
                )
                .values(
                    reserved_quantity=Inventory.reserved_quantity + quantity
                )
            )

            if result.rowcount != 1:
                raise ValueError(
                    "Stock changed during order creation. Please retry."
                )

        order = Order(
            order_number=f"MED-{uuid4().hex[:12].upper()}",
            customer_id=customer_id,
            store_id=selected_store.id,
            prescription_id=prescription_id,
            status="confirmed",
            total_amount=Decimal("0.00"),
        )

        db.add(order)
        db.flush()

        for medicine_id, quantity in medicine_quantities.items():
            db.add(
                OrderItem(
                    order_id=order.id,
                    medicine_id=medicine_id,
                    quantity=quantity,
                    unit_price=Decimal("0.00"),
                )
            )

        db.commit()
        db.refresh(order)

        order_items = db.scalars(
            select(OrderItem).where(OrderItem.order_id == order.id)
        ).all()

        return {
            "id": order.id,
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "store_id": order.store_id,
            "prescription_id": order.prescription_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "items": [
                {
                    "id": order_item.id,
                    "medicine_id": order_item.medicine_id,
                    "quantity": order_item.quantity,
                    "unit_price": order_item.unit_price,
                }
                for order_item in order_items
            ],
        }

    except Exception:
        db.rollback()
        raise


def get_customer_orders(db: Session, customer_id: int):
    orders = db.scalars(
        select(Order)
        .where(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
    ).all()

    result = []

    for order in orders:
        items = db.scalars(
            select(OrderItem).where(OrderItem.order_id == order.id)
        ).all()

        result.append({
            "id": order.id,
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "store_id": order.store_id,
            "prescription_id": order.prescription_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "items": items,
        })

    return result


def get_all_orders(db: Session):
    """Return all pharmacy orders for pharmacist/admin management."""

    orders = db.scalars(
        select(Order).order_by(Order.created_at.desc())
    ).all()

    result = []

    for order in orders:
        items = db.scalars(
            select(OrderItem).where(OrderItem.order_id == order.id)
        ).all()

        result.append({
            "id": order.id,
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "store_id": order.store_id,
            "prescription_id": order.prescription_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "items": items,
        })

    return result


def get_customer_order(db: Session, customer_id: int, order_id: int):
    order = db.scalar(
        select(Order).where(
            Order.id == order_id,
            Order.customer_id == customer_id,
        )
    )

    if order is None:
        return None

    items = db.scalars(
        select(OrderItem).where(OrderItem.order_id == order.id)
    ).all()

    return {
        "id": order.id,
        "order_number": order.order_number,
        "customer_id": order.customer_id,
        "store_id": order.store_id,
        "prescription_id": order.prescription_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "created_at": order.created_at,
        "items": items,
    }


ORDER_STATUS_TRANSITIONS = {
    "confirmed": ["preparing", "cancelled"],
    "preparing": ["ready", "cancelled"],
    "ready": ["dispatched", "cancelled"],
    "dispatched": ["delivered"],
    "delivered": [],
    "cancelled": [],
}


def update_order_status(db, order_id, new_status, pharmacist_id):
    try:
        order = db.scalar(
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
        )

        if order is None:
            raise ValueError("Order not found.")

        allowed_statuses = ORDER_STATUS_TRANSITIONS.get(
            order.status, []
        )

        if new_status not in allowed_statuses:
            raise ValueError(
                f"Cannot change order status from "
                f"{order.status} to {new_status}."
            )

        old_status = order.status
        released_items = []

        # Release reserved inventory when cancelling an order.
        if new_status == "cancelled":
            if order.store_id is None:
                raise ValueError("Order has no assigned store.")

            order_items = db.scalars(
                select(OrderItem)
                .where(OrderItem.order_id == order.id)
                .order_by(OrderItem.medicine_id)
            ).all()

            quantities = {}

            for item in order_items:
                quantities[item.medicine_id] = (
                    quantities.get(item.medicine_id, 0)
                    + item.quantity
                )

            for medicine_id, quantity in quantities.items():
                result = db.execute(
                    update(Inventory)
                    .where(
                        Inventory.store_id == order.store_id,
                        Inventory.medicine_id == medicine_id,
                        Inventory.reserved_quantity >= quantity,
                    )
                    .values(
                        reserved_quantity=(
                            Inventory.reserved_quantity - quantity
                        )
                    )
                )

                if result.rowcount != 1:
                    raise ValueError(
                        f"Unable to release reserved stock "
                        f"for medicine ID {medicine_id}."
                    )

                released_items.append({
                    "medicine_id": medicine_id,
                    "quantity": quantity,
                })

        order.status = new_status

        audit_log = AuditLog(
            actor_id=pharmacist_id,
            action="order.status_updated",
            entity_type="order",
            entity_id=order.id,
            details={
                "old_status": old_status,
                "new_status": new_status,
                "released_inventory": released_items,
            },
        )

        db.add(audit_log)
        db.commit()
        db.refresh(order)

        return order

    except Exception:
        db.rollback()
        raise
