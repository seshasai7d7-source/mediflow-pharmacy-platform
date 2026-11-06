
from decimal import Decimal

import pytest

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
    User,
)


def register_customer(client, email, phone):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Customer",
            "email": email,
            "phone": phone,
            "password": "TestPassword#2026",
        },
    )
    assert response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword#2026",
        },
    )
    assert login_response.status_code == 200

    return login_response.json()["access_token"]


def promote_user_to_role(email, role):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None

        user.role = role
        db.commit()
    finally:
        db_generator.close()


def get_pharmacist_token(client, email, phone):
    token = register_customer(client, email, phone)
    promote_user_to_role(email, "pharmacist")
    return token


def create_test_order(customer_id):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="API Test Store",
            address="Test Address",
            city="Kolkata",
            pincode="700001",
            is_active=True,
        )

        medicine = Medicine(
            name="API Test Medicine",
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
            order_number=f"API-TEST-{customer_id}",
            customer_id=customer_id,
            store_id=store.id,
            status="confirmed",
            total_amount=Decimal("0.00"),
        )

        db.add(order)
        db.flush()

        db.add(
            OrderItem(
                order_id=order.id,
                medicine_id=medicine.id,
                quantity=1,
                unit_price=Decimal("0.00"),
            )
        )

        db.commit()
        return order.id

    finally:
        db_generator.close()


def create_approved_prescription(customer_id):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name="Prescription Test Store",
            address="Test Address",
            city="Kolkata",
            pincode="700001",
            is_active=True,
        )

        medicine = Medicine(
            name="Prescription Test Medicine",
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
            file_object_key="test/api_approved_prescription.pdf",
            status="approved",
        )

        db.add(prescription)
        db.flush()

        db.add(
            PrescriptionItem(
                prescription_id=prescription.id,
                medicine_id=medicine.id,
                extracted_name="Prescription Test Medicine",
                dosage="500mg",
                quantity=2,
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

        db.commit()
        return prescription.id

    finally:
        db_generator.close()


def test_customer_can_create_order_through_api(client):
    email = "api_create_order@example.com"
    token = register_customer(client, email, "9876500001")

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    customer_id = profile.json()["id"]

    prescription_id = create_approved_prescription(customer_id)

    response = client.post(
        "/api/v1/orders",
        json={"prescription_id": prescription_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "confirmed"
    assert response.json()["prescription_id"] == prescription_id
    assert len(response.json()["items"]) == 1


def test_create_order_requires_customer_role(client):
    email = "api_pharmacist_order@example.com"
    token = get_pharmacist_token(
        client,
        email,
        "9876500002",
    )

    response = client.post(
        "/api/v1/orders",
        json={"prescription_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("error_message", "expected_status"),
    [
        ("Prescription not found.", 404),
        ("An active order already exists for this prescription.", 409),
        ("Insufficient stock for the requested medicines.", 409),
        ("Some other validation error.", 400),
    ],
)
def test_create_order_maps_service_errors(
    client,
    monkeypatch,
    error_message,
    expected_status,
):
    import app.api.v1.orders as orders_api

    email = "api_order_errors@example.com"
    token = register_customer(client, email, "9876500003")

    def raise_error(**kwargs):
        raise ValueError(error_message)

    monkeypatch.setattr(
        orders_api,
        "create_order_from_prescription",
        raise_error,
    )

    response = client.post(
        "/api/v1/orders",
        json={"prescription_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == expected_status
    assert response.json()["detail"] == error_message


def test_create_order_rejects_invalid_request_body(client):
    token = register_customer(
        client,
        "api_invalid_order@example.com",
        "9876500004",
    )

    response = client.post(
        "/api/v1/orders",
        json={"prescription_id": 0},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_customer_can_get_own_order_through_api(client):
    email = "api_get_own_order@example.com"
    token = register_customer(client, email, "9876500005")

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    order_id = create_test_order(profile.json()["id"])

    response = client.get(
        f"/api/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == order_id
    assert len(response.json()["items"]) == 1


def test_pharmacist_can_update_order_status(client):
    email = "api_status_pharmacist@example.com"
    token = get_pharmacist_token(
        client,
        email,
        "9876500006",
    )

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    order_id = create_test_order(profile.json()["id"])

    response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "preparing"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "preparing"


def test_customer_cannot_update_order_status(client):
    email = "api_customer_status@example.com"
    token = register_customer(client, email, "9876500007")

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    order_id = create_test_order(profile.json()["id"])

    response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "preparing"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_update_order_status_requires_authentication(client):
    response = client.patch(
        "/api/v1/orders/1/status",
        json={"status": "preparing"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("error_message", "expected_status"),
    [
        ("Order not found.", 404),
        ("Invalid order status transition.", 409),
    ],
)
def test_update_order_status_maps_service_errors(
    client,
    monkeypatch,
    error_message,
    expected_status,
):
    import app.api.v1.orders as orders_api

    email = "api_status_errors@example.com"
    token = get_pharmacist_token(
        client,
        email,
        "9876500008",
    )

    def raise_error(**kwargs):
        raise ValueError(error_message)

    monkeypatch.setattr(
        orders_api,
        "update_order_status",
        raise_error,
    )

    response = client.patch(
        "/api/v1/orders/99999/status",
        json={"status": "preparing"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == expected_status
    assert response.json()["detail"] == error_message


def test_update_order_status_rejects_invalid_status(client):
    email = "api_invalid_status@example.com"
    token = get_pharmacist_token(
        client,
        email,
        "9876500009",
    )

    response = client.patch(
        "/api/v1/orders/1/status",
        json={"status": "unknown"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
