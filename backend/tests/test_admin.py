
from sqlalchemy import select

from app.db.database import get_db
from app.main import app
from app.models import AuditLog, Store, User


def register_and_login(client, email, phone):
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin Test User",
            "email": email,
            "phone": phone,
            "password": "TestPassword123",
        },
    )
    assert registration.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )
    assert login.status_code == 200

    return login.json()["access_token"]


def promote_to_admin(email):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        user = db.scalar(
            select(User).where(User.email == email)
        )
        user.role = "admin"
        db.commit()
        return user.id
    finally:
        db_generator.close()


def admin_headers(client, email="admin@example.com"):
    token = register_and_login(
        client,
        email,
        "9876543210",
    )
    promote_to_admin(email)

    return {"Authorization": f"Bearer {token}"}


def test_admin_user_list_requires_admin(client):
    token = register_and_login(
        client,
        "customer@example.com",
        "9876543211",
    )

    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_list_users(client):
    headers = admin_headers(client)

    register_and_login(
        client,
        "another@example.com",
        "9876543212",
    )

    response = client.get(
        "/api/v1/admin/users",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert len(data["users"]) == 2

    for user in data["users"]:
        assert "password" not in user
        assert "password_hash" not in user


def test_admin_can_search_users(client):
    headers = admin_headers(client)

    register_and_login(
        client,
        "sesha@example.com",
        "9876543212",
    )

    response = client.get(
        "/api/v1/admin/users?search=sesha",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["users"][0]["email"] == "sesha@example.com"


def test_admin_can_update_user_role_and_status(client):
    headers = admin_headers(client)

    register_and_login(
        client,
        "pharmacist@example.com",
        "9876543212",
    )

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        target = db.scalar(
            select(User).where(
                User.email == "pharmacist@example.com"
            )
        )
        target_id = target.id
    finally:
        db_generator.close()

    response = client.patch(
        f"/api/v1/admin/users/{target_id}",
        headers=headers,
        json={
            "role": "pharmacist",
            "is_active": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["role"] == "pharmacist"
    assert response.json()["is_active"] is False

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "user.updated",
                AuditLog.entity_id == target_id,
            )
        )

        assert audit is not None
        assert audit.entity_type == "user"
        assert audit.details["new_values"]["role"] == "pharmacist"
        assert audit.details["new_values"]["is_active"] is False
    finally:
        db_generator.close()


def test_admin_cannot_demote_own_account(client):
    headers = admin_headers(client)

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        admin = db.scalar(
            select(User).where(
                User.email == "admin@example.com"
            )
        )
        admin_id = admin.id
    finally:
        db_generator.close()

    response = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        headers=headers,
        json={"role": "customer"},
    )

    assert response.status_code == 400


def test_admin_cannot_deactivate_own_account(client):
    headers = admin_headers(client)

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        admin = db.scalar(
            select(User).where(
                User.email == "admin@example.com"
            )
        )
        admin_id = admin.id
    finally:
        db_generator.close()

    response = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        headers=headers,
        json={"is_active": False},
    )

    assert response.status_code == 400


def test_admin_update_unknown_user_returns_404(client):
    headers = admin_headers(client)

    response = client.patch(
        "/api/v1/admin/users/99999",
        headers=headers,
        json={"is_active": False},
    )

    assert response.status_code == 404


def test_admin_rejects_empty_update(client):
    headers = admin_headers(client)

    response = client.patch(
        "/api/v1/admin/users/1",
        headers=headers,
        json={},
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# Admin Store Management Tests
# ---------------------------------------------------------


def create_admin_test_store(
    name="Test Pharmacy",
    is_active=True,
):
    db_generator = app.dependency_overrides[get_db]()
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
        db_generator.close()


def test_admin_store_list_requires_admin(client):
    token = register_and_login(
        client,
        "store_customer@example.com",
        "9876543211",
    )

    response = client.get(
        "/api/v1/admin/stores",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_list_active_and_inactive_stores(client):
    headers = admin_headers(client)

    create_admin_test_store("Active Pharmacy", True)
    create_admin_test_store("Inactive Pharmacy", False)

    response = client.get(
        "/api/v1/admin/stores",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2

    store_statuses = {
        store["name"]: store["is_active"]
        for store in data["stores"]
    }

    assert store_statuses["Active Pharmacy"] is True
    assert store_statuses["Inactive Pharmacy"] is False


def test_admin_can_filter_stores_by_status(client):
    headers = admin_headers(client)

    create_admin_test_store("Active Pharmacy", True)
    create_admin_test_store("Inactive Pharmacy", False)

    response = client.get(
        "/api/v1/admin/stores?is_active=false",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["stores"][0]["name"] == "Inactive Pharmacy"


def test_admin_can_search_stores(client):
    headers = admin_headers(client)

    create_admin_test_store("Central Pharmacy")
    create_admin_test_store("North Pharmacy")

    response = client.get(
        "/api/v1/admin/stores?search=Central",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["stores"][0]["name"] == "Central Pharmacy"


def test_admin_can_get_store_details(client):
    headers = admin_headers(client)
    store_id = create_admin_test_store(
        "Details Pharmacy",
        is_active=False,
    )

    response = client.get(
        f"/api/v1/admin/stores/{store_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Details Pharmacy"
    assert response.json()["is_active"] is False


def test_admin_can_update_store_and_audit_is_created(client):
    headers = admin_headers(client)
    store_id = create_admin_test_store()

    response = client.patch(
        f"/api/v1/admin/stores/{store_id}",
        headers=headers,
        json={
            "name": "Updated Pharmacy",
            "city": "Kolkata",
            "is_active": False,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Updated Pharmacy"
    assert data["city"] == "Kolkata"
    assert data["is_active"] is False

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "store.updated",
                AuditLog.entity_id == store_id,
            )
        )

        assert audit is not None
        assert audit.entity_type == "store"
        assert audit.details["old_values"]["name"] == "Test Pharmacy"
        assert audit.details["new_values"]["name"] == "Updated Pharmacy"
        assert audit.details["new_values"]["is_active"] is False
    finally:
        db_generator.close()


def test_admin_can_clear_store_coordinates(client):
    headers = admin_headers(client)
    store_id = create_admin_test_store()

    response = client.patch(
        f"/api/v1/admin/stores/{store_id}",
        headers=headers,
        json={
            "latitude": None,
            "longitude": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["latitude"] is None
    assert response.json()["longitude"] is None


def test_admin_rejects_empty_store_update(client):
    headers = admin_headers(client)
    store_id = create_admin_test_store()

    response = client.patch(
        f"/api/v1/admin/stores/{store_id}",
        headers=headers,
        json={},
    )

    assert response.status_code == 422


def test_admin_cannot_clear_required_store_name(client):
    headers = admin_headers(client)
    store_id = create_admin_test_store()

    response = client.patch(
        f"/api/v1/admin/stores/{store_id}",
        headers=headers,
        json={"name": None},
    )

    assert response.status_code == 422


def test_admin_update_unknown_store_returns_404(client):
    headers = admin_headers(client)

    response = client.patch(
        "/api/v1/admin/stores/99999",
        headers=headers,
        json={"is_active": False},
    )

    assert response.status_code == 404


def test_non_admin_cannot_update_store(client):
    token = register_and_login(
        client,
        "store_update_customer@example.com",
        "9876543212",
    )
    store_id = create_admin_test_store()

    response = client.patch(
        f"/api/v1/admin/stores/{store_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )

    assert response.status_code == 403

# ---------------------------------------------------------
# Admin Platform Overview Tests
# ---------------------------------------------------------


def test_platform_overview_requires_admin(client):
    token = register_and_login(
        client,
        "overview_customer@example.com",
        "9876543213",
    )

    response = client.get(
        "/api/v1/admin/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_view_platform_overview(client):
    headers = admin_headers(client)

    create_admin_test_store("Overview Active Store", True)
    create_admin_test_store("Overview Inactive Store", False)

    response = client.get(
        "/api/v1/admin/overview",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    # User metrics
    assert data["users"]["total"] == 1
    assert data["users"]["active"] == 1
    assert data["users"]["inactive"] == 0
    assert data["users"]["admins"] == 1

    # Store metrics
    assert data["stores"]["total"] == 2
    assert data["stores"]["active"] == 1
    assert data["stores"]["inactive"] == 1

    # No orders, prescriptions, or inventory in this test
    assert data["orders"]["total"] == 0
    assert data["prescriptions"]["total"] == 0
    assert data["inventory"]["records"] == 0
    assert data["inventory"]["available_quantity"] == 0
    assert data["inventory"]["reserved_quantity"] == 0