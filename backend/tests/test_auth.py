def register_customer(client, email="customer@example.com"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Customer",
            "email": email,
            "phone": "9876543210",
            "password": "TestPassword123",
        },
    )


def login_customer(client, email="customer@example.com"):
    return client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )


def test_customer_registration_success(client):
    response = register_customer(client)

    assert response.status_code == 201
    assert response.json()["email"] == "customer@example.com"
    assert response.json()["role"] == "customer"
    assert "password" not in response.json()
    assert "password_hash" not in response.json()


def test_duplicate_email_registration(client):
    register_customer(client)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Another Customer",
            "email": "customer@example.com",
            "phone": "9876543211",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 409


def test_customer_login_success(client):
    register_customer(client)

    response = login_customer(client)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == 1800
    assert response.json()["access_token"]


def test_customer_login_invalid_password(client):
    register_customer(client)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "customer@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401


def test_profile_without_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_profile_with_valid_token(client):
    register_customer(client)

    login_response = login_customer(client)
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "customer@example.com"
    assert response.json()["role"] == "customer"


def test_profile_with_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401

from types import SimpleNamespace

import app.api.v1.auth as auth_module


def test_dev_login_success(client, monkeypatch):
    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: SimpleNamespace(
            app_env="development",
            enable_dev_auth=True,
            access_token_expire_minutes=30,
        ),
    )

    response = client.post("/api/v1/auth/dev-login")

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == 1800
    assert response.json()["access_token"]


def test_dev_login_reuses_existing_customer(client, monkeypatch):
    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: SimpleNamespace(
            app_env="development",
            enable_dev_auth=True,
            access_token_expire_minutes=30,
        ),
    )

    first_response = client.post("/api/v1/auth/dev-login")
    second_response = client.post("/api/v1/auth/dev-login")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_token = first_response.json()["access_token"]
    second_token = second_response.json()["access_token"]

    first_profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    second_profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert first_profile.status_code == 200
    assert second_profile.status_code == 200
    assert first_profile.json()["id"] == second_profile.json()["id"]
    assert first_profile.json()["email"] == "demo.customer@example.com"


def test_dev_login_blocked_outside_development(client, monkeypatch):
    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: SimpleNamespace(
            app_env="production",
            enable_dev_auth=True,
            access_token_expire_minutes=30,
        ),
    )

    response = client.post("/api/v1/auth/dev-login")

    assert response.status_code == 404

def test_dev_login_rejects_inactive_customer(client, monkeypatch):
    from app.db.database import get_db
    from app.main import app
    from app.models import User

    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: SimpleNamespace(
            app_env="development",
            enable_dev_auth=True,
            access_token_expire_minutes=30,
        ),
    )

    # Create the demo customer.
    first_response = client.post("/api/v1/auth/dev-login")
    assert first_response.status_code == 200

    # Deactivate the demo customer in the test database.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        demo_user = db.query(User).filter_by(
            email="demo.customer@example.com"
        ).first()

        assert demo_user is not None

        demo_user.is_active = False
        db.commit()
    finally:
        db_generator.close()

    # Inactive demo customer must be rejected.
    response = client.post("/api/v1/auth/dev-login")

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Development customer account is unavailable."
    )