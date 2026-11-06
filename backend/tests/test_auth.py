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