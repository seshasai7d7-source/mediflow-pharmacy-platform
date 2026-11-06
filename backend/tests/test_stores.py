
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.models import Store, User


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def create_test_user(client, role="customer", email=None):
    if email is None:
        email = f"store_{role}@example.com"

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        user = User(
            full_name=f"Test {role.title()}",
            email=email,
            password_hash=hash_password("TestPassword#2026"),
            role=role,
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(user.id)

        return token

    finally:
        db.close()
        db_generator.close()


def store_payload(name="Test Pharmacy"):
    return {
        "name": name,
        "address": "123 Test Street",
        "city": "Bengaluru",
        "pincode": "560001",
        "latitude": 12.9716,
        "longitude": 77.5946,
    }


def create_store_in_database(
    client,
    name,
    is_active=True,
):
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        store = Store(
            name=name,
            address="123 Test Street",
            city="Bengaluru",
            pincode="560001",
            latitude=12.9716,
            longitude=77.5946,
            is_active=is_active,
        )

        db.add(store)
        db.commit()
        db.refresh(store)

        return store.id

    finally:
        db.close()
        db_generator.close()


# ---------------------------------------------------------
# POST /api/v1/stores
# Store creation tests
# ---------------------------------------------------------

def test_admin_can_create_store(client):
    token = create_test_user(client, role="admin")

    response = client.post(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
        json=store_payload(),
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Test Pharmacy"
    assert response.json()["city"] == "Bengaluru"
    assert response.json()["pincode"] == "560001"
    assert response.json()["is_active"] is True


def test_customer_cannot_create_store(client):
    token = create_test_user(client, role="customer")

    response = client.post(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
        json=store_payload(),
    )

    assert response.status_code == 403


def test_pharmacist_cannot_create_store(client):
    token = create_test_user(client, role="pharmacist")

    response = client.post(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
        json=store_payload(),
    )

    assert response.status_code == 403


def test_unauthenticated_user_cannot_create_store(client):
    response = client.post(
        "/api/v1/stores",
        json=store_payload(),
    )

    assert response.status_code == 401


def test_create_store_rejects_invalid_payload(client):
    token = create_test_user(client, role="admin")

    response = client.post(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "A",
            "address": "123",
            "city": "B",
            "pincode": "1",
        },
    )

    assert response.status_code == 422


def test_create_store_rejects_invalid_coordinates(client):
    token = create_test_user(client, role="admin")

    payload = store_payload()
    payload["latitude"] = 100

    response = client.post(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 422


def test_create_store_returns_409_on_database_conflict(
    client,
    monkeypatch,
):
    token = create_test_user(client, role="admin")

    def fake_commit(self):
        raise IntegrityError(
            "INSERT INTO stores",
            {},
            Exception("Simulated database conflict"),
        )

    monkeypatch.setattr(Session, "commit", fake_commit)

    response = client.post(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
        json=store_payload(),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Unable to create store due to a database conflict."
    )


# ---------------------------------------------------------
# GET /api/v1/stores
# Store listing tests
# ---------------------------------------------------------

def test_authenticated_user_can_list_stores(client):
    token = create_test_user(client, role="customer")

    create_store_in_database(
        client,
        "Test Pharmacy",
        is_active=True,
    )

    response = client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Test Pharmacy"


def test_unauthenticated_user_cannot_list_stores(client):
    response = client.get("/api/v1/stores")

    assert response.status_code == 401


def test_list_stores_excludes_inactive_stores(client):
    token = create_test_user(client, role="customer")

    create_store_in_database(
        client,
        "Active Pharmacy",
        is_active=True,
    )

    create_store_in_database(
        client,
        "Inactive Pharmacy",
        is_active=False,
    )

    response = client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    store_names = [
        store["name"] for store in response.json()
    ]

    assert "Active Pharmacy" in store_names
    assert "Inactive Pharmacy" not in store_names


def test_list_stores_returns_stores_in_alphabetical_order(client):
    token = create_test_user(client, role="customer")

    create_store_in_database(client, "Zeta Pharmacy")
    create_store_in_database(client, "Alpha Pharmacy")
    create_store_in_database(client, "Beta Pharmacy")

    response = client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    store_names = [
        store["name"] for store in response.json()
    ]

    assert store_names == [
        "Alpha Pharmacy",
        "Beta Pharmacy",
        "Zeta Pharmacy",
    ]


def test_list_stores_returns_empty_list_when_no_active_stores(client):
    token = create_test_user(client, role="customer")

    create_store_in_database(
        client,
        "Inactive Pharmacy",
        is_active=False,
    )

    response = client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []
