
from sqlalchemy import select

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
