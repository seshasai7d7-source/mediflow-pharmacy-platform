import pytest
from app.services.inventory_service import (
    calculate_distance_km,
    find_available_stores,
    import_inventory_csv,
    reserve_inventory,
)

from app.models import Inventory, Medicine, Store
from app.db.database import get_db
from app.main import app


def test_import_inventory_csv_creates_inventory_record(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="CSV Test Pharmacy",
            address="Test Address",
            city="Kolkata",
            pincode="700016",
            is_active=True,
        )

        medicine = Medicine(
            name="CSV Test Medicine",
            generic_name="CSV Generic",
            brand_name="CSV Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="OTC",
            requires_prescription=False,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.commit()

        csv_content = (
            "store_id,medicine_id,available_quantity\n"
            f"{store.id},{medicine.id},50\n"
        ).encode("utf-8")

        result = import_inventory_csv(db, csv_content)

        inventory = db.query(Inventory).filter_by(
            store_id=store.id,
            medicine_id=medicine.id,
        ).first()

        assert result["records_processed"] == 1
        assert result["records_created"] == 1
        assert result["records_updated"] == 0
        assert inventory is not None
        assert inventory.available_quantity == 50
        assert inventory.reserved_quantity == 0

    finally:
        db_generator.close()


def test_calculate_distance_between_same_coordinates():
    distance = calculate_distance_km(
        22.5726,
        88.3639,
        22.5726,
        88.3639,
    )

    assert distance == 0


def test_calculate_distance_between_two_locations():
    distance = calculate_distance_km(
        22.5726,
        88.3639,
        22.5535,
        88.3530,
    )

    assert 2.0 < distance < 2.5


def test_import_inventory_csv_rejects_invalid_encoding():
    with pytest.raises(ValueError, match="UTF-8"):
        import_inventory_csv(
            db=None,
            file_content=b"\xff\xfe\xfa",
        )


def test_import_inventory_csv_rejects_missing_columns():
    with pytest.raises(ValueError, match="CSV must contain"):
        import_inventory_csv(
            db=None,
            file_content=b"store_id,medicine_id\n1,1",
        )


def test_import_inventory_csv_rejects_empty_csv_headers():
    with pytest.raises(ValueError, match="CSV must contain"):
        import_inventory_csv(
            db=None,
            file_content=b"",
        )

def test_import_inventory_csv_updates_existing_record(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Update Test Pharmacy",
            address="Test Address",
            city="Kolkata",
            pincode="700016",
            is_active=True,
        )

        medicine = Medicine(
            name="Update Test Medicine",
            generic_name="Update Generic",
            brand_name="Update Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="OTC",
            requires_prescription=False,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.commit()

        inventory = Inventory(
            store_id=store.id,
            medicine_id=medicine.id,
            available_quantity=20,
            reserved_quantity=5,
        )

        db.add(inventory)
        db.commit()

        csv_content = (
            "store_id,medicine_id,available_quantity\n"
            f"{store.id},{medicine.id},80\n"
        ).encode("utf-8")

        result = import_inventory_csv(db, csv_content)

        db.refresh(inventory)

        assert result["records_processed"] == 1
        assert result["records_created"] == 0
        assert result["records_updated"] == 1
        assert inventory.available_quantity == 80
        assert inventory.reserved_quantity == 5

    finally:
        db_generator.close()

def test_import_inventory_csv_skips_invalid_rows(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        csv_content = (
            "store_id,medicine_id,available_quantity\n"
            "abc,1,50\n"
            "1,xyz,50\n"
            "1,1,-10\n"
            "0,1,50\n"
        ).encode("utf-8")

        result = import_inventory_csv(db, csv_content)

        assert result["records_processed"] == 4
        assert result["records_created"] == 0
        assert result["records_updated"] == 0
        assert result["records_skipped"] == 4

    finally:
        db_generator.close()

def test_find_available_stores_returns_store_with_sufficient_stock(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Availability Test Pharmacy",
            address="Test Address",
            city="Kolkata",
            pincode="700016",
            latitude=22.5535,
            longitude=88.3530,
            is_active=True,
        )

        medicine = Medicine(
            name="Availability Test Medicine",
            generic_name="Availability Generic",
            brand_name="Availability Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="OTC",
            requires_prescription=False,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.commit()

        inventory = Inventory(
            store_id=store.id,
            medicine_id=medicine.id,
            available_quantity=100,
            reserved_quantity=10,
        )

        db.add(inventory)
        db.commit()

        results = find_available_stores(
            db=db,
            medicine_id=medicine.id,
            quantity=50,
        )

        assert len(results) == 1
        assert results[0]["store_id"] == store.id
        assert results[0]["available_quantity"] == 90

    finally:
        db_generator.close()

def test_find_available_stores_excludes_insufficient_stock(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Low Stock Pharmacy",
            address="Test Address",
            city="Kolkata",
            pincode="700016",
            is_active=True,
        )

        medicine = Medicine(
            name="Low Stock Medicine",
            generic_name="Low Stock Generic",
            brand_name="Low Stock Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="OTC",
            requires_prescription=False,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.commit()

        inventory = Inventory(
            store_id=store.id,
            medicine_id=medicine.id,
            available_quantity=20,
            reserved_quantity=5,
        )

        db.add(inventory)
        db.commit()

        results = find_available_stores(
            db=db,
            medicine_id=medicine.id,
            quantity=50,
        )

        assert results == []

    finally:
        db_generator.close()

@pytest.mark.parametrize("quantity", [0, -5])
def test_find_available_stores_rejects_invalid_quantity(client, quantity):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        with pytest.raises(ValueError, match="Requested quantity must be greater than zero"):
            find_available_stores(
                db=db,
                medicine_id=1,
                quantity=quantity,
            )
    finally:
        db_generator.close()

def test_reserve_inventory_successfully(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Reservation Test Pharmacy",
            address="Test Address",
            city="Kolkata",
            pincode="700016",
            is_active=True,
        )

        medicine = Medicine(
            name="Reservation Test Medicine",
            generic_name="Reservation Generic",
            brand_name="Reservation Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="OTC",
            requires_prescription=False,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.commit()

        inventory = Inventory(
            store_id=store.id,
            medicine_id=medicine.id,
            available_quantity=100,
            reserved_quantity=10,
        )

        db.add(inventory)
        db.commit()

        result = reserve_inventory(
            db=db,
            store_id=store.id,
            medicine_id=medicine.id,
            quantity=20,
        )

        db.refresh(inventory)

        assert inventory.available_quantity == 100
        assert inventory.reserved_quantity == 30
        assert result["reserved_quantity"] == 30
        assert result["available_quantity"] == 70

    finally:
        db_generator.close()

def test_reserve_inventory_rejects_insufficient_stock(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Insufficient Stock Pharmacy",
            address="Test Address",
            city="Kolkata",
            pincode="700016",
            is_active=True,
        )

        medicine = Medicine(
            name="Insufficient Stock Medicine",
            generic_name="Insufficient Generic",
            brand_name="Insufficient Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="OTC",
            requires_prescription=False,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.commit()

        inventory = Inventory(
            store_id=store.id,
            medicine_id=medicine.id,
            available_quantity=20,
            reserved_quantity=5,
        )

        db.add(inventory)
        db.commit()

        with pytest.raises(ValueError):
            reserve_inventory(
                db=db,
                store_id=store.id,
                medicine_id=medicine.id,
                quantity=50,
            )

        db.refresh(inventory)

        assert inventory.available_quantity == 20
        assert inventory.reserved_quantity == 5

    finally:
        db_generator.close()

@pytest.mark.parametrize("quantity", [0, -10])
def test_reserve_inventory_rejects_invalid_quantity(client, quantity):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        with pytest.raises(ValueError):
            reserve_inventory(
                db=db,
                store_id=1,
                medicine_id=1,
                quantity=quantity,
            )
    finally:
        db_generator.close()

@pytest.mark.parametrize("inactive_entity", ["store", "medicine"])
def test_reserve_inventory_rejects_inactive_entities(client, inactive_entity):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Inactive Test Pharmacy",
            address="Test Address",
            city="Kolkata",
            pincode="700016",
            is_active=(inactive_entity != "store"),
        )

        medicine = Medicine(
            name="Inactive Test Medicine",
            generic_name="Inactive Generic",
            brand_name="Inactive Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="OTC",
            requires_prescription=False,
            is_active=(inactive_entity != "medicine"),
        )

        db.add_all([store, medicine])
        db.commit()

        inventory = Inventory(
            store_id=store.id,
            medicine_id=medicine.id,
            available_quantity=100,
            reserved_quantity=0,
        )

        db.add(inventory)
        db.commit()

        with pytest.raises(ValueError):
            reserve_inventory(
                db=db,
                store_id=store.id,
                medicine_id=medicine.id,
                quantity=10,
            )

        db.refresh(inventory)
        assert inventory.reserved_quantity == 0

    finally:
        db_generator.close()








