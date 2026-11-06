import asyncio
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import select

from app.core.dependencies import get_db
from app.models import Inventory, Medicine, Store
from app.services.inventory_service import reserve_inventory
import app.api.v1.inventory as inventory_api


def create_inventory_data(client):
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Test Pharmacy",
            address="Test Street",
            city="Kolkata",
            pincode="700016",
            latitude=22.5535,
            longitude=88.3530,
            is_active=True,
        )

        medicine = Medicine(
            name="Reservation Test Medicine",
            strength="500 mg",
            dosage_form="Tablet",
            schedule_category="H",
            requires_prescription=True,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.flush()

        inventory = Inventory(
            store_id=store.id,
            medicine_id=medicine.id,
            available_quantity=100,
            reserved_quantity=0,
        )

        db.add(inventory)
        db.commit()

        return {
            "store_id": store.id,
            "medicine_id": medicine.id,
            "inventory_id": inventory.id,
        }

    finally:
        db.close()
        db_generator.close()


# ---------------------------------------------------------
# Inventory service tests
# ---------------------------------------------------------

def test_reserve_inventory_success(client):
    data = create_inventory_data(client)

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        result = reserve_inventory(
            db,
            data["store_id"],
            data["medicine_id"],
            10,
        )

        assert result["reserved_quantity"] == 10
        assert result["available_quantity"] == 90
        assert result["message"] == "Stock reserved successfully."

    finally:
        db.close()
        db_generator.close()


def test_reserve_inventory_insufficient_stock(client):
    data = create_inventory_data(client)

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        with pytest.raises(ValueError, match="Insufficient available stock"):
            reserve_inventory(
                db,
                data["store_id"],
                data["medicine_id"],
                150,
            )

        inventory = db.scalar(
            select(Inventory).where(
                Inventory.id == data["inventory_id"]
            )
        )

        assert inventory.reserved_quantity == 0

    finally:
        db.close()
        db_generator.close()


def test_reserve_inventory_repeated_requests(client):
    data = create_inventory_data(client)

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        first = reserve_inventory(
            db,
            data["store_id"],
            data["medicine_id"],
            60,
        )

        assert first["reserved_quantity"] == 60

        with pytest.raises(ValueError, match="Insufficient available stock"):
            reserve_inventory(
                db,
                data["store_id"],
                data["medicine_id"],
                50,
            )

        inventory = db.scalar(
            select(Inventory).where(
                Inventory.id == data["inventory_id"]
            )
        )

        assert inventory.available_quantity == 100
        assert inventory.reserved_quantity == 60

    finally:
        db.close()
        db_generator.close()


def test_reserve_inventory_rejects_zero_quantity(client):
    data = create_inventory_data(client)

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        with pytest.raises(ValueError, match="greater than zero"):
            reserve_inventory(
                db,
                data["store_id"],
                data["medicine_id"],
                0,
            )

    finally:
        db.close()
        db_generator.close()


# ---------------------------------------------------------
# Inventory CSV upload API tests
# ---------------------------------------------------------

def test_inventory_upload_rejects_non_csv_file(monkeypatch):
    file = UploadFile(
        filename="inventory.txt",
        file=BytesIO(b"test"),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            inventory_api.upload_inventory_csv(
                file=file,
                db=None,
                current_user=SimpleNamespace(id=1),
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Only CSV files are supported."


def test_inventory_upload_rejects_empty_file():
    file = UploadFile(
        filename="inventory.csv",
        file=BytesIO(b""),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            inventory_api.upload_inventory_csv(
                file=file,
                db=None,
                current_user=SimpleNamespace(id=1),
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "The CSV file is empty."


def test_inventory_upload_rejects_large_file():
    file = UploadFile(
        filename="inventory.csv",
        file=BytesIO(b"a" * (inventory_api.MAX_CSV_SIZE + 1)),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            inventory_api.upload_inventory_csv(
                file=file,
                db=None,
                current_user=SimpleNamespace(id=1),
            )
        )

    assert exc.value.status_code == 413
    assert exc.value.detail == "CSV file exceeds the 5 MB size limit."


def test_inventory_upload_success(monkeypatch):
    expected_result = {
        "message": "Inventory imported successfully.",
        "created": 2,
        "updated": 0,
    }

    def mock_import(db, content):
        assert db == "test_db"
        assert content == b"medicine,quantity"
        return expected_result

    monkeypatch.setattr(
        inventory_api,
        "import_inventory_csv",
        mock_import,
    )

    file = UploadFile(
        filename="inventory.csv",
        file=BytesIO(b"medicine,quantity"),
    )

    result = asyncio.run(
        inventory_api.upload_inventory_csv(
            file=file,
            db="test_db",
            current_user=SimpleNamespace(id=1),
        )
    )

    assert result == expected_result


def test_inventory_upload_handles_invalid_csv(monkeypatch):
    def mock_import(db, content):
        raise ValueError("Invalid CSV format.")

    monkeypatch.setattr(
        inventory_api,
        "import_inventory_csv",
        mock_import,
    )

    file = UploadFile(
        filename="inventory.csv",
        file=BytesIO(b"invalid,data"),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            inventory_api.upload_inventory_csv(
                file=file,
                db=None,
                current_user=SimpleNamespace(id=1),
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid CSV format."


def test_inventory_upload_rejects_missing_filename():
    file = UploadFile(
        filename="",
        file=BytesIO(b"medicine,quantity"),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            inventory_api.upload_inventory_csv(
                file=file,
                db=None,
                current_user=SimpleNamespace(id=1),
            )
        )

    assert exc.value.status_code == 400


# ---------------------------------------------------------
# Store routing API tests
# ---------------------------------------------------------

def test_route_to_available_store_success(monkeypatch):
    expected_stores = [
        {"store_id": 1, "available_quantity": 20}
    ]

    def mock_find_stores(db, medicine_id, quantity):
        assert medicine_id == 1
        assert quantity == 5
        return expected_stores

    monkeypatch.setattr(
        inventory_api,
        "find_available_stores",
        mock_find_stores,
    )

    request = SimpleNamespace(
        medicine_id=1,
        quantity=5,
    )

    result = inventory_api.route_to_available_store(
        request=request,
        db=None,
        current_user=SimpleNamespace(id=1),
    )

    assert result == expected_stores


def test_route_to_available_store_not_found(monkeypatch):
    def mock_find_stores(db, medicine_id, quantity):
        raise ValueError("Medicine not found.")

    monkeypatch.setattr(
        inventory_api,
        "find_available_stores",
        mock_find_stores,
    )

    request = SimpleNamespace(
        medicine_id=999,
        quantity=5,
    )

    with pytest.raises(HTTPException) as exc:
        inventory_api.route_to_available_store(
            request=request,
            db=None,
            current_user=SimpleNamespace(id=1),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Medicine not found."


# ---------------------------------------------------------
# Inventory reservation API tests
# ---------------------------------------------------------

def test_reserve_store_inventory_success(monkeypatch):
    expected_result = {
        "message": "Stock reserved successfully.",
        "reserved_quantity": 5,
        "available_quantity": 95,
    }

    def mock_reserve(db, store_id, medicine_id, quantity):
        assert store_id == 1
        assert medicine_id == 2
        assert quantity == 5
        return expected_result

    monkeypatch.setattr(
        inventory_api,
        "reserve_inventory",
        mock_reserve,
    )

    request = SimpleNamespace(
        medicine_id=2,
        quantity=5,
    )

    result = inventory_api.reserve_store_inventory(
        store_id=1,
        request=request,
        db=None,
        current_user=SimpleNamespace(id=1),
    )

    assert result == expected_result


def test_reserve_store_inventory_insufficient_stock(monkeypatch):
    def mock_reserve(db, store_id, medicine_id, quantity):
        raise ValueError("Insufficient available stock.")

    monkeypatch.setattr(
        inventory_api,
        "reserve_inventory",
        mock_reserve,
    )

    request = SimpleNamespace(
        medicine_id=2,
        quantity=150,
    )

    with pytest.raises(HTTPException) as exc:
        inventory_api.reserve_store_inventory(
            store_id=1,
            request=request,
            db=None,
            current_user=SimpleNamespace(id=1),
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Insufficient available stock."


def test_reserve_store_inventory_record_not_found(monkeypatch):
    def mock_reserve(db, store_id, medicine_id, quantity):
        raise ValueError("Inventory record not found.")

    monkeypatch.setattr(
        inventory_api,
        "reserve_inventory",
        mock_reserve,
    )

    request = SimpleNamespace(
        medicine_id=999,
        quantity=5,
    )

    with pytest.raises(HTTPException) as exc:
        inventory_api.reserve_store_inventory(
            store_id=1,
            request=request,
            db=None,
            current_user=SimpleNamespace(id=1),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Inventory record not found."


def test_reserve_store_inventory_other_validation_error(monkeypatch):
    def mock_reserve(db, store_id, medicine_id, quantity):
        raise ValueError("Quantity must be greater than zero.")

    monkeypatch.setattr(
        inventory_api,
        "reserve_inventory",
        mock_reserve,
    )

    request = SimpleNamespace(
        medicine_id=2,
        quantity=0,
    )

    with pytest.raises(HTTPException) as exc:
        inventory_api.reserve_store_inventory(
            store_id=1,
            request=request,
            db=None,
            current_user=SimpleNamespace(id=1),
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Quantity must be greater than zero."
