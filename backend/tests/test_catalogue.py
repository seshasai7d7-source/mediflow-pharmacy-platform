from fastapi.testclient import TestClient

from app.core.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.models import Inventory, Medicine, Store, User


def create_user(client: TestClient, role: str = "customer") -> str:
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        user = User(
            full_name=f"Catalogue {role.title()}",
            email=f"catalogue_{role}@example.com",
            password_hash=hash_password("TestPassword#2026"),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return create_access_token(user.id)
    finally:
        db.close()
        db_generator.close()


def create_catalogue_data(client: TestClient) -> dict:
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        active_store = Store(
            name="Synthetic Central",
            address="1 Test Road",
            city="Test City",
            pincode="123456",
            is_active=True,
        )
        inactive_store = Store(
            name="Synthetic Closed",
            address="2 Test Road",
            city="Test City",
            pincode="123456",
            is_active=False,
        )
        active_medicine = Medicine(
            name="Test Amox Tablet",
            generic_name="Amoxicillin",
            brand_name="SyntheticBrand",
            strength="500 mg",
            dosage_form="Tablet",
            schedule_category="H",
            requires_prescription=True,
            is_active=True,
        )
        inactive_medicine = Medicine(
            name="Inactive Test Medicine",
            generic_name="Inactive Generic",
            brand_name="Inactive Brand",
            is_active=False,
        )
        db.add_all([active_store, inactive_store, active_medicine, inactive_medicine])
        db.flush()
        db.add_all([
            Inventory(
                store_id=active_store.id,
                medicine_id=active_medicine.id,
                available_quantity=10,
                reserved_quantity=7,
            ),
            Inventory(
                store_id=inactive_store.id,
                medicine_id=inactive_medicine.id,
                available_quantity=50,
                reserved_quantity=0,
            ),
        ])
        db.commit()
        return {
            "store_id": active_store.id,
            "inactive_store_id": inactive_store.id,
            "medicine_id": active_medicine.id,
        }
    finally:
        db.close()
        db_generator.close()


def customer_headers(client: TestClient) -> dict:
    token = create_user(client)
    return {"Authorization": f"Bearer {token}"}


def test_catalogue_requires_authentication(client: TestClient):
    response = client.get("/api/v1/inventory/catalogue")
    assert response.status_code == 401


def test_customer_can_browse_active_medicine_without_reserved_quantity_leak(client: TestClient):
    data = create_catalogue_data(client)
    response = client.get(
        "/api/v1/inventory/catalogue",
        headers=customer_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == data["medicine_id"]
    assert body["items"][0]["available_quantity"] == 3
    assert body["items"][0]["is_available"] is True
    assert body["items"][0]["requires_prescription"] is True
    assert "reserved_quantity" not in str(body)
    assert "inventory_id" not in str(body)


def test_catalogue_searches_name_generic_and_brand(client: TestClient):
    create_catalogue_data(client)
    headers = customer_headers(client)

    for search in ("amox tablet", "amoxicillin", "syntheticbrand"):
        response = client.get(
            "/api/v1/inventory/catalogue",
            params={"search": search},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1


def test_catalogue_store_filter_and_unavailable_stock(client: TestClient):
    data = create_catalogue_data(client)
    headers = customer_headers(client)

    response = client.get(
        "/api/v1/inventory/catalogue",
        params={"store_id": data["store_id"]},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["available_quantity"] == 3

    response = client.get(
        "/api/v1/inventory/catalogue",
        params={"store_id": data["inactive_store_id"]},
        headers=headers,
    )
    assert response.status_code == 404


def test_catalogue_invalid_store_and_medicine_with_no_inventory(client: TestClient):
    data = create_catalogue_data(client)
    headers = customer_headers(client)

    invalid_store = client.get(
        "/api/v1/inventory/catalogue",
        params={"store_id": 999999},
        headers=headers,
    )
    assert invalid_store.status_code == 404

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        medicine = Medicine(
            name="Synthetic Unstocked Medicine",
            generic_name="Unstocked Generic",
            brand_name="Unstocked Brand",
            schedule_category="OTC",
            requires_prescription=False,
            is_active=True,
        )
        db.add(medicine)
        db.commit()
    finally:
        db.close()
        db_generator.close()

    response = client.get(
        "/api/v1/inventory/catalogue",
        params={
            "search": "Unstocked",
            "store_id": data["store_id"],
        },
        headers=headers,
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["is_available"] is False
    assert item["available_quantity"] == 0
    assert item["stores"] == [{
        "store_id": data["store_id"],
        "store_name": "Synthetic Central",
        "city": "Test City",
        "available_quantity": 0,
        "is_available": False,
    }]


def test_catalogue_paginates_distinct_medicines_with_total(client: TestClient):
    create_catalogue_data(client)
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        db.add_all([
            Medicine(
                name=f"Synthetic Pagination {index:02}",
                schedule_category="OTC",
                requires_prescription=False,
                is_active=True,
            )
            for index in range(21)
        ])
        db.commit()
    finally:
        db.close()
        db_generator.close()

    headers = customer_headers(client)
    first_page = client.get(
        "/api/v1/inventory/catalogue",
        params={"skip": 0, "limit": 20},
        headers=headers,
    )
    second_page = client.get(
        "/api/v1/inventory/catalogue",
        params={"skip": 20, "limit": 20},
        headers=headers,
    )

    assert first_page.status_code == second_page.status_code == 200
    first_body = first_page.json()
    second_body = second_page.json()
    assert first_body["total"] == second_body["total"] == 22
    assert first_body["skip"] == 0
    assert second_body["skip"] == 20
    assert len(first_body["items"]) == 20
    assert len(second_body["items"]) == 2
    first_ids = {item["id"] for item in first_body["items"]}
    second_ids = {item["id"] for item in second_body["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_catalogue_rejects_pharmacist_and_admin(client: TestClient):
    create_catalogue_data(client)
    for role in ("pharmacist", "admin"):
        response = client.get(
            "/api/v1/inventory/catalogue",
            headers={"Authorization": f"Bearer {create_user(client, role)}"},
        )
        assert response.status_code == 403


def test_catalogue_trims_search_whitespace(client: TestClient):
    create_catalogue_data(client)
    response = client.get(
        "/api/v1/inventory/catalogue",
        params={"search": "  Amoxicillin  "},
        headers=customer_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["generic_name"] == "Amoxicillin"


def test_catalogue_ignores_inventory_at_inactive_stores(client: TestClient):
    data = create_catalogue_data(client)
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        medicine = Medicine(
            name="Synthetic Inactive Store Stock",
            schedule_category="OTC",
            requires_prescription=False,
            is_active=True,
        )
        db.add(medicine)
        db.flush()
        db.add(Inventory(
            store_id=data["inactive_store_id"],
            medicine_id=medicine.id,
            available_quantity=80,
            reserved_quantity=0,
        ))
        db.commit()
    finally:
        db.close()
        db_generator.close()

    response = client.get(
        "/api/v1/inventory/catalogue",
        params={"search": "Synthetic Inactive Store Stock"},
        headers=customer_headers(client),
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["available_quantity"] == 0
    assert item["is_available"] is False
    assert item["stores"] == []


def test_catalogue_empty_and_pagination_boundaries(client: TestClient):
    create_catalogue_data(client)
    headers = customer_headers(client)

    empty = client.get(
        "/api/v1/inventory/catalogue",
        params={"search": "no-such-medicine"},
        headers=headers,
    )
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["total"] == 0

    invalid_limit = client.get(
        "/api/v1/inventory/catalogue",
        params={"limit": 0},
        headers=headers,
    )
    assert invalid_limit.status_code == 422
