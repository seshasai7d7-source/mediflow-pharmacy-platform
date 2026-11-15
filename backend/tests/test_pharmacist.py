
from sqlalchemy import select
from sqlalchemy.orm import Session
import pytest

from app.core.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.models import (
    AuditLog,
    Medicine,
    Prescription,
    PrescriptionItem,
    User,
)


def create_test_data(client, schedule_category="H"):
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        customer = User(
            full_name="Test Customer",
            email="test.customer@example.com",
            password_hash=hash_password("CustomerTest#2026"),
            role="customer",
            is_active=True,
        )

        pharmacist = User(
            full_name="Test Pharmacist",
            email="test.pharmacist@example.com",
            password_hash=hash_password("PharmacistTest#2026"),
            role="pharmacist",
            is_active=True,
        )

        medicine = Medicine(
            name="Test Medicine",
            strength="250 mg",
            dosage_form="Tablet",
            schedule_category=schedule_category,
            requires_prescription=True,
            is_active=True,
        )

        db.add_all([customer, pharmacist, medicine])
        db.flush()

        prescription = Prescription(
            customer_id=customer.id,
            file_object_key="prescriptions/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
            status="uploaded",
            ai_extraction_json={
                "medicines": [],
                "needs_manual_review": True,
            },
        )

        db.add(prescription)
        db.commit()

        return {
            "prescription_id": prescription.id,
            "medicine_id": medicine.id,
            "customer_token": create_access_token(customer.id),
            "pharmacist_token": create_access_token(pharmacist.id),
            "pharmacist_id": pharmacist.id,
        }

    finally:
        db.close()
        db_generator.close()


def approval_payload(medicine_id):
    return {
        "decision": "approved",
        "medicines": [
            {
                "medicine_id": medicine_id,
                "dosage": "Test dosage only",
                "quantity": 10,
                "generic_substitution": False,
                "customer_consent": False,
            }
        ],
        "rejection_reason": None,
    }


def test_pharmacist_can_approve_prescription(client):
    data = create_test_data(client)

    response = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
        json=approval_payload(data["medicine_id"]),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["pharmacist_id"] == data["pharmacist_id"]

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        item = db.scalar(
            select(PrescriptionItem).where(
                PrescriptionItem.prescription_id == data["prescription_id"]
            )
        )

        assert item is not None
        assert item.medicine_id == data["medicine_id"]
        assert item.pharmacist_approved is True
        assert item.quantity == 10

        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "prescription",
                AuditLog.entity_id == data["prescription_id"],
                AuditLog.action == "prescription.approved",
            )
        )

        assert audit is not None
        assert audit.actor_id == data["pharmacist_id"]

    finally:
        db.close()
        db_generator.close()


def test_pharmacist_can_reject_prescription(client):
    data = create_test_data(client)

    response = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
        json={
            "decision": "rejected",
            "medicines": [],
            "rejection_reason": "Prescription is unclear.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["rejection_reason"] == "Prescription is unclear."


def test_schedule_x_medicine_cannot_be_approved(client):
    data = create_test_data(client, schedule_category="X")

    response = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
        json=approval_payload(data["medicine_id"]),
    )

    assert response.status_code == 400
    assert "prohibited category" in response.json()["detail"]

    # The failed review must not approve the prescription.
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        prescription = db.get(
            Prescription,
            data["prescription_id"],
        )
        assert prescription.status == "uploaded"
        assert prescription.pharmacist_id is None
    finally:
        db.close()
        db_generator.close()


def test_customer_cannot_review_prescription(client):
    data = create_test_data(client)

    response = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers={"Authorization": f"Bearer {data['customer_token']}"},
        json=approval_payload(data["medicine_id"]),
    )

    assert response.status_code == 403


def test_prescription_cannot_be_reviewed_twice(client):
    data = create_test_data(client)

    headers = {
        "Authorization": f"Bearer {data['pharmacist_token']}"
    }

    first_response = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers=headers,
        json={
            "decision": "rejected",
            "medicines": [],
            "rejection_reason": "Test rejection.",
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers=headers,
        json=approval_payload(data["medicine_id"]),
    )

    assert second_response.status_code == 409


def test_review_requires_at_least_one_medicine_for_approval(client):
    data = create_test_data(client)

    response = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
        json={
            "decision": "approved",
            "medicines": [],
            "rejection_reason": None,
        },
    )

    assert response.status_code == 422


def test_pharmacist_can_list_active_medicines_and_customers_cannot(client):
    data = create_test_data(client)

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        db.add(
            Medicine(
                name="Inactive Medicine",
                strength="100 mg",
                dosage_form="Tablet",
                schedule_category="OTC",
                requires_prescription=False,
                is_active=False,
            )
        )
        db.add(
            Medicine(
                name="Aspirin Demo",
                strength="75 mg",
                dosage_form="Tablet",
                schedule_category="OTC",
                requires_prescription=False,
                is_active=True,
            )
        )
        db.commit()
    finally:
        db.close()
        db_generator.close()

    response = client.get(
        "/api/v1/pharmacist/medicines",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
    )
    assert response.status_code == 200
    names = [medicine["name"] for medicine in response.json()]
    assert names == sorted(names)
    assert "Aspirin Demo" in names
    assert "Inactive Medicine" not in names
    assert all("id" in medicine for medicine in response.json())

    customer_response = client.get(
        "/api/v1/pharmacist/medicines",
        headers={"Authorization": f"Bearer {data['customer_token']}"},
    )
    assert customer_response.status_code == 403

    unauthenticated_response = client.get(
        "/api/v1/pharmacist/medicines"
    )
    assert unauthenticated_response.status_code == 401


def test_pharmacist_can_list_prescription_queue_with_pagination(client):
    data = create_test_data(client)

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        second_prescription = Prescription(
            customer_id=data["customer_id"]
            if "customer_id" in data
            else db.get(Prescription, data["prescription_id"]).customer_id,
            file_object_key="prescriptions/second.pdf",
            original_filename="second.pdf",
            mime_type="application/pdf",
            status="uploaded",
            ai_extraction_json={"medicines": [], "needs_manual_review": True},
        )
        db.add(second_prescription)
        db.commit()
        second_id = second_prescription.id
    finally:
        db.close()
        db_generator.close()

    response = client.get(
        "/api/v1/pharmacist/prescriptions/queue?limit=1&offset=1",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    item = response.json()[0]
    assert item["id"] == second_id
    assert item["customer_name"] == "Test Customer"
    assert item["customer_email"] == "test.customer@example.com"
    assert item["status"] == "uploaded"
    assert item["ai_extraction_json"]["needs_manual_review"] is True

    customer_response = client.get(
        "/api/v1/pharmacist/prescriptions/queue",
        headers={"Authorization": f"Bearer {data['customer_token']}"},
    )
    assert customer_response.status_code == 403

    invalid_limit = client.get(
        "/api/v1/pharmacist/prescriptions/queue?limit=0",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
    )
    assert invalid_limit.status_code == 422


def test_pharmacist_can_retrieve_prescription_details(client):
    data = create_test_data(client)

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        item = PrescriptionItem(
            prescription_id=data["prescription_id"],
            medicine_id=data["medicine_id"],
            extracted_name="Test Medicine",
            dosage="One tablet daily",
            quantity=10,
            pharmacist_approved=False,
            generic_substitution=True,
            customer_consent=True,
        )
        db.add(item)
        db.commit()
        item_id = item.id
    finally:
        db.close()
        db_generator.close()

    response = client.get(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == data["prescription_id"]
    assert body["customer_email"] == "test.customer@example.com"
    assert body["items"] == [
        {
            "id": item_id,
            "medicine_id": data["medicine_id"],
            "extracted_name": "Test Medicine",
            "dosage": "One tablet daily",
            "quantity": 10,
            "pharmacist_approved": False,
            "generic_substitution": True,
            "customer_consent": True,
        }
    ]

    missing = client.get(
        "/api/v1/pharmacist/prescriptions/999999",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
    )
    assert missing.status_code == 404

    customer_response = client.get(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}",
        headers={"Authorization": f"Bearer {data['customer_token']}"},
    )
    assert customer_response.status_code == 403


def test_review_rejects_missing_or_inactive_medicines(client):
    data = create_test_data(client)
    headers = {"Authorization": f"Bearer {data['pharmacist_token']}"}

    missing_medicine = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers=headers,
        json=approval_payload(999999),
    )
    assert missing_medicine.status_code == 400
    assert "Active medicine" in missing_medicine.json()["detail"]

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        medicine = db.get(Medicine, data["medicine_id"])
        medicine.is_active = False
        db.commit()
    finally:
        db.close()
        db_generator.close()

    inactive_medicine = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers=headers,
        json=approval_payload(data["medicine_id"]),
    )
    assert inactive_medicine.status_code == 400
    assert "Active medicine" in inactive_medicine.json()["detail"]


@pytest.mark.parametrize("schedule_category", ["NARCOTIC", "UNKNOWN"])
def test_prohibited_and_unknown_medicine_schedules_cannot_be_approved(
    client, schedule_category
):
    data = create_test_data(client, schedule_category=schedule_category)

    response = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
        json=approval_payload(data["medicine_id"]),
    )
    assert response.status_code == 400
    if schedule_category == "NARCOTIC":
        assert "prohibited category" in response.json()["detail"]
    else:
        assert "unknown schedule" in response.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        {
            "decision": "approved",
            "medicines": [
                {
                    "medicine_id": 1,
                    "dosage": "Test",
                    "quantity": 1,
                    "generic_substitution": True,
                    "customer_consent": False,
                }
            ],
        },
        {
            "decision": "rejected",
            "medicines": [],
        },
        {
            "decision": "approved",
            "medicines": [
                {
                    "medicine_id": 1,
                    "dosage": "Test",
                    "quantity": 0,
                }
            ],
        },
    ],
)
def test_review_payload_validation_returns_unprocessable_entity(client, payload):
    data = create_test_data(client)

    response = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
        json=payload,
    )
    assert response.status_code == 422


def test_rejection_persists_and_creates_audit_log(client):
    data = create_test_data(client)
    reason = "The uploaded prescription is not legible."

    response = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
        json={
            "decision": "rejected",
            "medicines": [],
            "rejection_reason": reason,
        },
    )
    assert response.status_code == 200

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        prescription = db.get(Prescription, data["prescription_id"])
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "prescription",
                AuditLog.entity_id == data["prescription_id"],
                AuditLog.action == "prescription.rejected",
            )
        )
        assert prescription.status == "rejected"
        assert prescription.rejection_reason == reason
        assert prescription.pharmacist_id == data["pharmacist_id"]
        assert prescription.reviewed_at is not None
        assert audit is not None
        assert audit.actor_id == data["pharmacist_id"]
        assert audit.details["decision"] == "rejected"
        assert audit.details["medicine_count"] == 0
    finally:
        db.close()
        db_generator.close()


def test_review_missing_prescription_returns_not_found(client):
    data = create_test_data(client)

    response = client.post(
        "/api/v1/pharmacist/prescriptions/999999/review",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
        json={
            "decision": "rejected",
            "medicines": [],
            "rejection_reason": "Not found test.",
        },
    )
    assert response.status_code == 404


def test_review_commit_failure_returns_server_error_and_rolls_back(
    client, monkeypatch
):
    data = create_test_data(client)
    original_commit = Session.commit

    def fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(Session, "commit", fail_commit)
    response = client.post(
        f"/api/v1/pharmacist/prescriptions/{data['prescription_id']}/review",
        headers={"Authorization": f"Bearer {data['pharmacist_token']}"},
        json={
            "decision": "rejected",
            "medicines": [],
            "rejection_reason": "Commit failure test.",
        },
    )
    monkeypatch.setattr(Session, "commit", original_commit)

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to save the prescription review."

    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        prescription = db.get(Prescription, data["prescription_id"])
        assert prescription.status == "uploaded"
        assert prescription.pharmacist_id is None
        assert db.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == data["prescription_id"],
                AuditLog.action == "prescription.rejected",
            )
        ) is None
    finally:
        db.close()
        db_generator.close()
