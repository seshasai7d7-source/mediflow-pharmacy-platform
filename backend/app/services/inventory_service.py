
import csv
import io
from sqlalchemy import update
from math import radians, sin, cos, sqrt, atan2
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Inventory, Medicine, Store


def import_inventory_csv(
    db: Session,
    file_content: bytes,
) -> dict:
    try:
        content = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("CSV file must use UTF-8 encoding.")

    reader = csv.DictReader(io.StringIO(content))

    required_columns = {
        "store_id",
        "medicine_id",
        "available_quantity",
    }

    if not reader.fieldnames or not required_columns.issubset(
        set(reader.fieldnames)
    ):
        raise ValueError(
            "CSV must contain store_id, medicine_id, and available_quantity columns."
        )

    processed = 0
    created = 0
    updated = 0
    skipped = 0

    try:
        for row in reader:
            processed += 1

            try:
                store_id = int(row["store_id"])
                medicine_id = int(row["medicine_id"])
                quantity = int(row["available_quantity"])

                if store_id <= 0 or medicine_id <= 0 or quantity < 0:
                    skipped += 1
                    continue

                store = db.get(Store, store_id)
                medicine = db.get(Medicine, medicine_id)

                if (
                    store is None
                    or not store.is_active
                    or medicine is None
                    or not medicine.is_active
                ):
                    skipped += 1
                    continue

                inventory = db.scalar(
                    select(Inventory).where(
                        Inventory.store_id == store_id,
                        Inventory.medicine_id == medicine_id,
                    )
                )

                if inventory:
                    inventory.available_quantity = quantity
                    updated += 1
                else:
                    inventory = Inventory(
                        store_id=store_id,
                        medicine_id=medicine_id,
                        available_quantity=quantity,
                        reserved_quantity=0,
                    )
                    db.add(inventory)
                    created += 1

            except (ValueError, TypeError, KeyError):
                skipped += 1

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Inventory import completed.",
        "records_processed": processed,
        "records_created": created,
        "records_updated": updated,
        "records_skipped": skipped,
    }


def calculate_distance_km(
    latitude1: float,
    longitude1: float,
    latitude2: float,
    longitude2: float,
) -> float:
    """Calculate distance between two geographical coordinates."""

    earth_radius_km = 6371.0

    lat1 = radians(latitude1)
    lat2 = radians(latitude2)

    delta_lat = radians(latitude2 - latitude1)
    delta_lon = radians(longitude2 - longitude1)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_km * c


def find_available_stores(
    db: Session,
    medicine_id: int,
    quantity: int,
    customer_latitude: float | None = None,
    customer_longitude: float | None = None,
) -> list[dict]:
    """Find active stores with enough unreserved stock."""

    if quantity <= 0:
        raise ValueError("Requested quantity must be greater than zero.")

    medicine = db.get(Medicine, medicine_id)

    if medicine is None or not medicine.is_active:
        raise ValueError("Medicine not found or inactive.")

    query = (
        select(Inventory, Store)
        .join(Store, Inventory.store_id == Store.id)
        .where(
            Inventory.medicine_id == medicine_id,
            Store.is_active.is_(True),
            Inventory.available_quantity - Inventory.reserved_quantity >= quantity,
        )
    )

    results = db.execute(query).all()

    stores = []

    for inventory, store in results:
        distance = None

        if (
            customer_latitude is not None
            and customer_longitude is not None
            and store.latitude is not None
            and store.longitude is not None
        ):
            distance = calculate_distance_km(
                customer_latitude,
                customer_longitude,
                store.latitude,
                store.longitude,
            )

        stores.append({
            "store_id": store.id,
            "store_name": store.name,
            "address": store.address,
            "city": store.city,
            "available_quantity": (
                inventory.available_quantity - inventory.reserved_quantity
            ),
            "distance_km": round(distance, 2) if distance is not None else None,
        })

    if customer_latitude is not None and customer_longitude is not None:
        stores.sort(
            key=lambda store: (
                store["distance_km"] is None,
                store["distance_km"] or 0,
            )
        )

    return stores


def reserve_inventory(
    db: Session,
    store_id: int,
    medicine_id: int,
    quantity: int,
) -> dict:
    """Reserve stock safely using an atomic database update."""

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    inventory = db.scalar(
        select(Inventory).where(
            Inventory.store_id == store_id,
            Inventory.medicine_id == medicine_id,
        )
    )

    if inventory is None:
        raise ValueError("Inventory record not found.")

    store = db.get(Store, store_id)
    medicine = db.get(Medicine, medicine_id)

    if store is None or not store.is_active:
        raise ValueError("Store not found or inactive.")

    if medicine is None or not medicine.is_active:
        raise ValueError("Medicine not found or inactive.")

    try:
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
            db.rollback()
            raise ValueError("Insufficient available stock.")

        db.commit()

        db.refresh(inventory)

        return {
            "store_id": inventory.store_id,
            "medicine_id": inventory.medicine_id,
            "reserved_quantity": inventory.reserved_quantity,
            "available_quantity": (
                inventory.available_quantity - inventory.reserved_quantity
            ),
            "message": "Stock reserved successfully.",
        }

    except Exception:
        db.rollback()
        raise
