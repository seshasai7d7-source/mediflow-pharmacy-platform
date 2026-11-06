import pytest
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy.sql.dml import Update

from app.db.database import get_db
from app.main import app
from app.models import (
    Inventory,
    Medicine,
    Order,
    OrderItem,
    Prescription,
    PrescriptionItem,
    Store,
)
from app.services.order_service import (
    create_order_from_prescription,
    get_customer_order,
)


def register_customer(client, email, phone):
    return client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Customer",
            "email": email,
            "phone": phone,
            "password": "TestPassword#2026",
        },
    )


def login_customer(client, email):
    return client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword#2026",
        },
    )


def get_token(client, email, phone):
    register_response = register_customer(client, email, phone)
    assert register_response.status_code == 201

    login_response = login_customer(client, email)
    assert login_response.status_code == 200

    return login_response.json()["access_token"]


def create_test_order(customer_id):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Test Store",
            address="Test Address",
            city="Kolkata",
            pincode="700001",
            latitude=22.5726,
            longitude=88.3639,
            is_active=True,
        )

        medicine = Medicine(
            name="Test Medicine",
            generic_name="Test Generic",
            brand_name="Test Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="OTC",
            requires_prescription=False,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.flush()

        order = Order(
            order_number=f"TEST-ORDER-{customer_id}",
            customer_id=customer_id,
            store_id=store.id,
            status="confirmed",
            total_amount=Decimal("0.00"),
        )

        db.add(order)
        db.flush()

        order_item = OrderItem(
            order_id=order.id,
            medicine_id=medicine.id,
            quantity=1,
            unit_price=Decimal("0.00"),
        )

        db.add(order_item)
        db.commit()

        return order.id

    finally:
        db_generator.close()


def test_customer_can_view_own_orders(client):
    token = get_token(
        client,
        "orders_customer@example.com",
        "9876543210",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    customer_id = profile.json()["id"]
    create_test_order(customer_id)

    response = client.get(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_customer_cannot_view_another_customers_order(client):
    token1 = get_token(
        client,
        "customer_one@example.com",
        "9876543211",
    )

    token2 = get_token(
        client,
        "customer_two@example.com",
        "9876543212",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token1}"},
    )

    order_id = create_test_order(profile.json()["id"])

    response = client.get(
        f"/api/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert response.status_code == 404


def test_customer_gets_404_for_nonexistent_order(client):
    token = get_token(
        client,
        "missing_order@example.com",
        "9876543213",
    )

    response = client.get(
        "/api/v1/orders/99999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_orders_require_authentication(client):
    response = client.get("/api/v1/orders")

    assert response.status_code == 401


def test_create_order_from_approved_prescription(client):
    token = get_token(
        client,
        "approved_prescription@example.com",
        "9876543214",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    customer_id = profile.json()["id"]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Test Store",
            address="Test Address",
            city="Kolkata",
            pincode="700001",
            latitude=22.5726,
            longitude=88.3639,
            is_active=True,
        )

        medicine = Medicine(
            name="Test Medicine",
            generic_name="Test Generic",
            brand_name="Test Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="H",
            requires_prescription=True,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.flush()

        prescription = Prescription(
            customer_id=customer_id,
            file_object_key="test/approved_prescription.pdf",
            status="approved",
        )

        db.add(prescription)
        db.flush()

        prescription_item = PrescriptionItem(
            prescription_id=prescription.id,
            medicine_id=medicine.id,
            extracted_name="Test Medicine",
            dosage="500mg",
            quantity=2,
            pharmacist_approved=True,
        )

        inventory = Inventory(
            store_id=store.id,
            medicine_id=medicine.id,
            available_quantity=20,
            reserved_quantity=0,
        )

        db.add_all([prescription_item, inventory])
        db.commit()

        prescription_id = prescription.id

        result = create_order_from_prescription(
            db,
            customer_id,
            prescription_id,
        )

        assert result["status"] == "confirmed"
        assert len(result["items"]) == 1

        db.refresh(inventory)
        assert inventory.reserved_quantity == 2

    finally:
        db_generator.close()


def test_create_order_rejects_unapproved_prescription(client):
    token = get_token(
        client,
        "unapproved_prescription@example.com",
        "9876543215",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    customer_id = profile.json()["id"]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        prescription = Prescription(
            customer_id=customer_id,
            file_object_key="test/unapproved_prescription.pdf",
            status="pending_review",
        )

        db.add(prescription)
        db.commit()

        with pytest.raises(ValueError):
            create_order_from_prescription(
                db,
                customer_id,
                prescription.id,
            )

    finally:
        db_generator.close()


def test_create_order_rejects_another_customers_prescription(client):
    token1 = get_token(
        client,
        "prescription_owner@example.com",
        "9876543216",
    )

    token2 = get_token(
        client,
        "different_customer@example.com",
        "9876543217",
    )

    profile1 = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token1}"},
    )

    profile2 = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token2}"},
    )

    customer1_id = profile1.json()["id"]
    customer2_id = profile2.json()["id"]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        prescription = Prescription(
            customer_id=customer1_id,
            file_object_key="test/other_customer_prescription.pdf",
            status="approved",
        )

        db.add(prescription)
        db.commit()

        with pytest.raises(ValueError):
            create_order_from_prescription(
                db,
                customer2_id,
                prescription.id,
            )

    finally:
        db_generator.close()


def test_create_order_rejects_duplicate_active_order(client):
    token = get_token(
        client,
        "duplicate_order@example.com",
        "9876543218",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    customer_id = profile.json()["id"]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Test Store",
            address="Test Address",
            city="Kolkata",
            pincode="700001",
            latitude=22.5726,
            longitude=88.3639,
            is_active=True,
        )

        medicine = Medicine(
            name="Test Medicine",
            generic_name="Test Generic",
            brand_name="Test Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="OTC",
            requires_prescription=False,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.flush()

        prescription = Prescription(
            customer_id=customer_id,
            file_object_key="test/duplicate_prescription.pdf",
            status="approved",
        )

        db.add(prescription)
        db.flush()

        db.add(
            PrescriptionItem(
                prescription_id=prescription.id,
                medicine_id=medicine.id,
                extracted_name="Test Medicine",
                dosage="500mg",
                quantity=1,
                pharmacist_approved=True,
            )
        )

        db.add(
            Inventory(
                store_id=store.id,
                medicine_id=medicine.id,
                available_quantity=20,
                reserved_quantity=0,
            )
        )

        db.add(
            Order(
                order_number="TEST-DUPLICATE-ORDER",
                customer_id=customer_id,
                store_id=store.id,
                prescription_id=prescription.id,
                status="confirmed",
                total_amount=Decimal("0.00"),
            )
        )

        db.commit()

        with pytest.raises(ValueError):
            create_order_from_prescription(
                db,
                customer_id,
                prescription.id,
            )

    finally:
        db_generator.close()


def test_create_order_rejects_insufficient_inventory(client):
    token = get_token(
        client,
        "insufficient_stock@example.com",
        "9876543219",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    customer_id = profile.json()["id"]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Test Store",
            address="Test Address",
            city="Kolkata",
            pincode="700001",
            latitude=22.5726,
            longitude=88.3639,
            is_active=True,
        )

        medicine = Medicine(
            name="Test Medicine",
            generic_name="Test Generic",
            brand_name="Test Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="H",
            requires_prescription=True,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.flush()

        prescription = Prescription(
            customer_id=customer_id,
            file_object_key="test/insufficient_stock_prescription.pdf",
            status="approved",
        )

        db.add(prescription)
        db.flush()

        db.add(
            PrescriptionItem(
                prescription_id=prescription.id,
                medicine_id=medicine.id,
                extracted_name="Test Medicine",
                dosage="500mg",
                quantity=10,
                pharmacist_approved=True,
            )
        )

        db.add(
            Inventory(
                store_id=store.id,
                medicine_id=medicine.id,
                available_quantity=5,
                reserved_quantity=0,
            )
        )

        db.commit()

        with pytest.raises(ValueError):
            create_order_from_prescription(
                db,
                customer_id,
                prescription.id,
            )

    finally:
        db_generator.close()


def test_create_order_rejects_prescription_without_items(client):
    token = get_token(
        client,
        "empty_prescription@example.com",
        "9876543220",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    customer_id = profile.json()["id"]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        prescription = Prescription(
            customer_id=customer_id,
            file_object_key="test/empty_prescription.pdf",
            status="approved",
        )

        db.add(prescription)
        db.commit()

        with pytest.raises(ValueError):
            create_order_from_prescription(
                db,
                customer_id,
                prescription.id,
            )

    finally:
        db_generator.close()


def test_create_order_rejects_unapproved_medicine_item(client):
    token = get_token(
        client,
        "unapproved_item@example.com",
        "9876543221",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    customer_id = profile.json()["id"]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        medicine = Medicine(
            name="Test Medicine",
            generic_name="Test Generic",
            brand_name="Test Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="H",
            requires_prescription=True,
            is_active=True,
        )

        db.add(medicine)
        db.flush()

        prescription = Prescription(
            customer_id=customer_id,
            file_object_key="test/unapproved_item_prescription.pdf",
            status="approved",
        )

        db.add(prescription)
        db.flush()

        db.add(
            PrescriptionItem(
                prescription_id=prescription.id,
                medicine_id=medicine.id,
                extracted_name="Test Medicine",
                dosage="500mg",
                quantity=2,
                pharmacist_approved=False,
            )
        )

        db.commit()

        with pytest.raises(ValueError):
            create_order_from_prescription(
                db,
                customer_id,
                prescription.id,
            )

    finally:
        db_generator.close()


def test_create_order_rejects_missing_medicine_id(client):
    token = get_token(
        client,
        "missing_medicine@example.com",
        "9876543222",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    customer_id = profile.json()["id"]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        prescription = Prescription(
            customer_id=customer_id,
            file_object_key="test/missing_medicine_prescription.pdf",
            status="approved",
        )

        db.add(prescription)
        db.flush()

        db.add(
            PrescriptionItem(
                prescription_id=prescription.id,
                medicine_id=None,
                extracted_name="Unknown Medicine",
                dosage="500mg",
                quantity=2,
                pharmacist_approved=True,
            )
        )

        db.commit()

        with pytest.raises(ValueError):
            create_order_from_prescription(
                db,
                customer_id,
                prescription.id,
            )

    finally:
        db_generator.close()


def test_get_customer_order_returns_order_with_items(client):
    token = get_token(
        client,
        "get_order_items@example.com",
        "9876543223",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    customer_id = profile.json()["id"]
    order_id = create_test_order(customer_id)

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        result = get_customer_order(
            db,
            order_id,
            customer_id,
        )

        assert result is not None
        assert result["id"] == order_id
        assert len(result["items"]) == 1

    finally:
        db_generator.close()


def test_create_order_rejects_stock_changed_during_creation(client):
    token = get_token(
        client,
        "stock_changed@example.com",
        "9876543230",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    customer_id = profile.json()["id"]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Test Store",
            address="Test Address",
            city="Kolkata",
            pincode="700001",
            latitude=22.5726,
            longitude=88.3639,
            is_active=True,
        )

        medicine = Medicine(
            name="Test Medicine",
            generic_name="Test Generic",
            brand_name="Test Brand",
            strength="500mg",
            dosage_form="tablet",
            schedule_category="H",
            requires_prescription=True,
            is_active=True,
        )

        db.add_all([store, medicine])
        db.flush()

        prescription = Prescription(
            customer_id=customer_id,
            file_object_key="test/stock_changed_prescription.pdf",
            status="approved",
        )

        db.add(prescription)
        db.flush()

        db.add(
            PrescriptionItem(
                prescription_id=prescription.id,
                medicine_id=medicine.id,
                extracted_name="Test Medicine",
                dosage="500mg",
                quantity=5,
                pharmacist_approved=True,
            )
        )

        inventory = Inventory(
            store_id=store.id,
            medicine_id=medicine.id,
            available_quantity=20,
            reserved_quantity=0,
        )

        db.add(inventory)
        db.commit()

        prescription_id = prescription.id

        # Intercept only UPDATE statements. Allow normal SELECT queries.
        original_execute = db.execute

        def simulate_stock_conflict(statement, *args, **kwargs):
            if isinstance(statement, Update):
                return SimpleNamespace(rowcount=0)

            return original_execute(statement, *args, **kwargs)

        db.execute = simulate_stock_conflict

        with pytest.raises(
            ValueError,
            match="Stock changed during order creation. Please retry.",
        ):
            create_order_from_prescription(
                db,
                customer_id,
                prescription_id,
            )

        db.refresh(inventory)

        assert inventory.reserved_quantity == 0
        assert (
            db.query(Order)
            .filter_by(prescription_id=prescription_id)
            .count()
            == 0
        )

    finally:
        db_generator.close()
