def test_root_endpoint_returns_welcome_message(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to MediFlow API"


def test_health_endpoint_returns_ok(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"