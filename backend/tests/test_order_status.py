import pytest
from decimal import Decimal
from app.db.database import get_db
from app.main import app
from app.models import Inventory, Medicine, Order, OrderItem, Store, User
from app.services.order_service import update_order_status

def create_test_order(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Test Pharmacy",
            address="Test Address",
            city="Kolkata",
            pincode="700016",
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

        inventory = Inventory(
            store_id=store.id,
            medicine_id=medicine.id,
            available_quantity=100,
            reserved_quantity=5,
        )

        customer_response = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Test Customer",
                "email": "status.customer@example.com",
                "phone": "9876543220",
                "password": "TestPassword123",
            },
        )

        assert customer_response.status_code in (200, 201)

        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "status.customer@example.com",
                "password": "TestPassword123",
            },
        )

        assert login_response.status_code == 200, login_response.text

        customer = db.query(User).filter_by(
            email="status.customer@example.com"
        ).first()

        assert customer is not None
        customer_id = customer.id

        order = Order(
            order_number="MED-STATUS-TEST-001",
            customer_id=customer_id,
            store_id=store.id,
            prescription_id=None,
            status="confirmed",
            total_amount=Decimal("0.00"),
        )

        db.add_all([inventory, order])
        db.flush()

        order_item = OrderItem(
            order_id=order.id,
            medicine_id=medicine.id,
            quantity=5,
            unit_price=Decimal("0.00"),
        )

        db.add(order_item)
        db.commit()

        return {
            "order_id": order.id,
            "customer_id": customer_id,
            "medicine_id": medicine.id,
            "store_id": store.id,
            "token": login_response.json()["access_token"],
        }

    finally:
        db_generator.close()


def create_pharmacist_token(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        from app.core.security import hash_password

        pharmacist = db.query(User).filter_by(
            email="status.pharmacist@example.com"
        ).first()

        if pharmacist is None:
            pharmacist = User(
                full_name="Test Pharmacist",
                email="status.pharmacist@example.com",
                phone="9876543221",
                password_hash=hash_password("TestPassword123"),
                role="pharmacist",
                is_active=True,
            )
            db.add(pharmacist)
            db.commit()

    finally:
        db_generator.close()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "status.pharmacist@example.com",
            "password": "TestPassword123",
        },
    )

    assert login.status_code == 200, login.text
    return login.json()["access_token"]

def get_inventory_values(medicine_id, store_id):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        inventory = db.query(Inventory).filter_by(
            medicine_id=medicine_id,
            store_id=store_id,
        ).one()

        return (
            inventory.available_quantity,
            inventory.reserved_quantity,
        )

    finally:
        db_generator.close()


def test_pharmacist_can_cancel_order_and_release_stock(client):
    data = create_test_order(client)
    pharmacist_token = create_pharmacist_token(client)

    response = client.patch(
        f"/api/v1/orders/{data['order_id']}/status",
        json={"status": "cancelled"},
        headers={"Authorization": f"Bearer {pharmacist_token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    available, reserved = get_inventory_values(
        data["medicine_id"],
        data["store_id"],
    )

    assert available == 100
    assert reserved == 0


def test_customer_cannot_update_order_status(client):
    data = create_test_order(client)

    response = client.patch(
        f"/api/v1/orders/{data['order_id']}/status",
        json={"status": "preparing"},
        headers={"Authorization": f"Bearer {data['token']}"},
    )

    assert response.status_code == 403


def test_invalid_order_status_transition_is_rejected(client):
    data = create_test_order(client)
    pharmacist_token = create_pharmacist_token(client)

    response = client.patch(
        f"/api/v1/orders/{data['order_id']}/status",
        json={"status": "delivered"},
        headers={"Authorization": f"Bearer {pharmacist_token}"},
    )

    assert response.status_code == 409


def test_update_order_status_rejects_nonexistent_order(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        with pytest.raises(
            ValueError,
            match="Order not found.",
        ):
            update_order_status(
                db=db,
                order_id=999999,
                new_status="preparing",
                pharmacist_id=1,
            )
    finally:
        db_generator.close()


def test_update_order_status_rejects_invalid_transition(client):
    from app.models import Order

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        order = Order(
            order_number="MED-INVALID-001",
            customer_id=1,
            status="confirmed",
            total_amount=0,
        )
        db.add(order)
        db.commit()
        order_id = order.id

        with pytest.raises(
            ValueError,
            match="Cannot change order status from confirmed to delivered.",
        ):
            update_order_status(
                db=db,
                order_id=order_id,
                new_status="delivered",
                pharmacist_id=1,
            )

        db.refresh(order)
        assert order.status == "confirmed"

    finally:
        db_generator.close()


def test_update_order_status_rejects_cancellation_without_store(client):
    from app.models import Order

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        order = Order(
            order_number="MED-NOSTORE-001",
            customer_id=1,
            store_id=None,
            status="confirmed",
            total_amount=0,
        )

        db.add(order)
        db.commit()
        order_id = order.id

        with pytest.raises(
            ValueError,
            match="Order has no assigned store.",
        ):
            update_order_status(
                db=db,
                order_id=order_id,
                new_status="cancelled",
                pharmacist_id=1,
            )

        db.refresh(order)
        assert order.status == "confirmed"

    finally:
        db_generator.close()


def test_cancellation_fails_when_reserved_stock_is_insufficient(client):
    from app.models import Inventory, Medicine, Order, OrderItem, Store

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Cancellation Test Pharmacy",
            address="Test Street",
            city="Kolkata",
            pincode="700016",
        )

        medicine = Medicine(
            name="Cancellation Test Medicine",
            strength="500 mg",
            dosage_form="Tablet",
            schedule_category="OTC",
            requires_prescription=False,
        )

        db.add_all([store, medicine])
        db.flush()

        order = Order(
            order_number="MED-RELEASE-001",
            customer_id=1,
            store_id=store.id,
            status="confirmed",
            total_amount=0,
        )
        db.add(order)
        db.flush()

        db.add(
            OrderItem(
                order_id=order.id,
                medicine_id=medicine.id,
                quantity=5,
                unit_price=0,
            )
        )

        inventory = Inventory(
            store_id=store.id,
            medicine_id=medicine.id,
            available_quantity=10,
            reserved_quantity=2,
        )
        db.add(inventory)
        db.commit()

        order_id = order.id

        with pytest.raises(
            ValueError,
            match="Unable to release reserved stock",
        ):
            update_order_status(
                db=db,
                order_id=order_id,
                new_status="cancelled",
                pharmacist_id=1,
            )

        db.refresh(order)
        db.refresh(inventory)

        assert order.status == "confirmed"
        assert inventory.reserved_quantity == 2

    finally:
        db_generator.close()

