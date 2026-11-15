
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.db.database import get_db
from app.main import app
from app.models import (
    AuditLog,
    Inventory,
    Medicine,
    Order,
    Prescription,
    PrescriptionItem,
    RefillPlan,
    RefillRequest,
    Store,
    User,
)
from app.services.refill_service import (
    approve_refill_request,
    create_refill_plan,
    create_refill_request,
    review_refill_plan,
    update_refill_plan_status,
)


def get_test_db():
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    return db, db_generator


def create_test_data(db, email="refill_customer@example.com"):
    customer = User(
        full_name="Refill Test Customer",
        email=email,
        phone=None,
        password_hash="test-password-hash",
        role="customer",
        is_active=True,
    )

    pharmacist = User(
        full_name="Refill Test Pharmacist",
        email=f"pharmacist_{email}",
        phone=None,
        password_hash="test-password-hash",
        role="pharmacist",
        is_active=True,
    )

    store = Store(
        name="Refill Test Store",
        address="Test Address",
        city="Kolkata",
        pincode="700001",
        latitude=22.5726,
        longitude=88.3639,
        is_active=True,
    )

    medicine = Medicine(
        name="Refill Test Medicine",
        generic_name="Test Generic",
        brand_name="Test Brand",
        strength="500mg",
        dosage_form="tablet",
        schedule_category="H",
        requires_prescription=True,
        is_active=True,
    )

    db.add_all([customer, pharmacist, store, medicine])
    db.flush()

    prescription = Prescription(
        customer_id=customer.id,
        file_object_key="test/refill_prescription.pdf",
        status="approved",
    )

    db.add(prescription)
    db.flush()

    prescription_item = PrescriptionItem(
        prescription_id=prescription.id,
        medicine_id=medicine.id,
        extracted_name=medicine.name,
        dosage="500mg",
        quantity=2,
        pharmacist_approved=True,
    )

    inventory = Inventory(
        store_id=store.id,
        medicine_id=medicine.id,
        available_quantity=20,
        reserved_quantity=0,
    )

    db.add_all([prescription_item, inventory])
    db.commit()

    return customer, pharmacist, prescription, inventory


def create_active_refill_plan(db, customer, pharmacist, prescription):
    plan = create_refill_plan(
        db=db,
        customer_id=customer.id,
        prescription_id=prescription.id,
        interval_days=30,
    )

    plan = review_refill_plan(
        db=db,
        plan_id=plan.id,
        pharmacist_id=pharmacist.id,
        decision="approved",
        review_note="Refill plan approved for testing.",
    )

    return plan


def make_plan_due(db, plan):
    plan.next_refill_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()
    db.refresh(plan)


def register_and_login(client, email, phone):
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Refill API Test User",
            "email": email,
            "phone": phone,
            "password": "TestPassword#2026",
        },
    )
    assert registration.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword#2026",
        },
    )
    assert login.status_code == 200

    return login.json()["access_token"]


def promote_user_to_role(email, role):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db.commit()
    finally:
        db_generator.close()


def role_headers(client, email, phone, role):
    register_and_login(client, email, phone)
    promote_user_to_role(email, role)
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword#2026",
        },
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_api_refill_data(db, customer_email):
    customer = db.scalar(select(User).where(User.email == customer_email))
    if customer is None:
        customer = User(
            full_name="Refill API Customer",
            email=customer_email,
            password_hash="test-password-hash",
            role="customer",
            is_active=True,
        )

    pharmacist = db.scalar(
        select(User).where(User.email == f"pharmacist_{customer_email}")
    )
    if pharmacist is None:
        pharmacist = User(
            full_name="Refill API Pharmacist",
            email=f"pharmacist_{customer_email}",
            password_hash="test-password-hash",
            role="pharmacist",
            is_active=True,
        )
    store = Store(
        name=f"API Refill Store {customer_email}",
        address="Test Address",
        city="Kolkata",
        pincode="700001",
        is_active=True,
    )
    medicine = Medicine(
        name=f"API Refill Medicine {customer_email}",
        generic_name="Test Generic",
        strength="500mg",
        dosage_form="tablet",
        schedule_category="H",
        requires_prescription=True,
        is_active=True,
    )
    db.add_all([customer, pharmacist, store, medicine])
    db.flush()

    prescription = Prescription(
        customer_id=customer.id,
        file_object_key=f"test/{customer_email}.pdf",
        status="approved",
    )
    db.add(prescription)
    db.flush()
    db.add_all(
        [
            PrescriptionItem(
                prescription_id=prescription.id,
                medicine_id=medicine.id,
                extracted_name=medicine.name,
                dosage="500mg",
                quantity=2,
                pharmacist_approved=True,
            ),
            Inventory(
                store_id=store.id,
                medicine_id=medicine.id,
                available_quantity=20,
                reserved_quantity=0,
            ),
        ]
    )
    db.commit()
    return customer, pharmacist, prescription


def create_api_plan(db, customer_id, prescription_id, pharmacist_id, decision="approved"):
    plan = create_refill_plan(
        db=db,
        customer_id=customer_id,
        prescription_id=prescription_id,
        interval_days=30,
    )
    if decision:
        plan = review_refill_plan(
            db=db,
            plan_id=plan.id,
            pharmacist_id=pharmacist_id,
            decision=decision,
            review_note=f"{decision} during API setup",
        )
    return plan


def create_api_pending_request(db, customer_id, prescription_id, pharmacist_id):
    plan = create_api_plan(
        db,
        customer_id,
        prescription_id,
        pharmacist_id,
    )
    make_plan_due(db, plan)
    return plan, create_refill_request(
        db=db,
        customer_id=customer_id,
        plan_id=plan.id,
    )


def test_customer_can_create_refill_plan(client):
    db, db_generator = get_test_db()

    try:
        customer, pharmacist, prescription, inventory = create_test_data(db)

        plan = create_refill_plan(
            db=db,
            customer_id=customer.id,
            prescription_id=prescription.id,
            interval_days=30,
        )

        assert plan.id is not None
        assert plan.customer_id == customer.id
        assert plan.prescription_id == prescription.id
        assert plan.interval_days == 30
        assert plan.status == "pending_review"

    finally:
        db_generator.close()


def test_customer_can_create_refill_plan_through_api(client):
    headers = role_headers(
        client, "create-plan-api@example.com", "9876500014", "customer"
    )
    db, db_generator = get_test_db()
    try:
        customer, _, prescription = create_api_refill_data(
            db, "create-plan-api@example.com"
        )
        prescription_id = prescription.id
        customer_id = customer.id
    finally:
        db_generator.close()

    response = client.post(
        "/api/v1/refills/plans",
        headers=headers,
        json={"prescription_id": prescription_id, "interval_days": 30},
    )
    assert response.status_code == 201
    assert response.json()["customer_id"] == customer_id
    assert response.json()["status"] == "pending_review"


def test_refill_plan_status_and_request_creation_are_available_through_api(client):
    headers = role_headers(
        client, "status-api@example.com", "9876500015", "customer"
    )
    db, db_generator = get_test_db()
    try:
        customer, pharmacist, prescription = create_api_refill_data(
            db, "status-api@example.com"
        )
        plan = create_api_plan(
            db, customer.id, prescription.id, pharmacist.id, "approved"
        )
        plan_id = plan.id
    finally:
        db_generator.close()

    paused = client.patch(
        f"/api/v1/refills/plans/{plan_id}/status?new_status=paused",
        headers=headers,
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    resumed = client.patch(
        f"/api/v1/refills/plans/{plan_id}/status?new_status=active",
        headers=headers,
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "active"

    db, db_generator = get_test_db()
    try:
        plan = db.get(RefillPlan, plan_id)
        make_plan_due(db, plan)
    finally:
        db_generator.close()

    request = client.post(
        f"/api/v1/refills/plans/{plan_id}/requests",
        headers=headers,
    )
    assert request.status_code == 201
    assert request.json()["plan_id"] == plan_id
    assert request.json()["status"] == "pending_review"


def test_refill_api_maps_service_errors_to_conflict_and_bad_request(client):
    headers = role_headers(
        client, "refill-error-api@example.com", "9876500016", "customer"
    )
    invalid_plan = client.post(
        "/api/v1/refills/plans",
        headers=headers,
        json={"prescription_id": 999999, "interval_days": 30},
    )
    assert invalid_plan.status_code == 404

    invalid_status = client.patch(
        "/api/v1/refills/plans/999999/status?new_status=paused",
        headers=headers,
    )
    assert invalid_status.status_code == 404

    invalid_request = client.post(
        "/api/v1/refills/plans/999999/requests",
        headers=headers,
    )
    assert invalid_request.status_code == 404

    invalid_payload = client.post(
        "/api/v1/refills/plans",
        headers=headers,
        json={"prescription_id": 0, "interval_days": 0},
    )
    assert invalid_payload.status_code == 422


def test_customer_cannot_create_duplicate_refill_plan(client):
    db, db_generator = get_test_db()

    try:
        customer, pharmacist, prescription, inventory = create_test_data(db)

        create_refill_plan(
            db=db,
            customer_id=customer.id,
            prescription_id=prescription.id,
            interval_days=30,
        )

        with pytest.raises(ValueError):
            create_refill_plan(
                db=db,
                customer_id=customer.id,
                prescription_id=prescription.id,
                interval_days=30,
            )

    finally:
        db_generator.close()


def test_pharmacist_can_approve_refill_plan(client):
    db, db_generator = get_test_db()

    try:
        customer, pharmacist, prescription, inventory = create_test_data(db)

        plan = create_refill_plan(
            db=db,
            customer_id=customer.id,
            prescription_id=prescription.id,
            interval_days=30,
        )

        reviewed_plan = review_refill_plan(
            db=db,
            plan_id=plan.id,
            pharmacist_id=pharmacist.id,
            decision="approved",
            review_note="Approved after pharmacist review.",
        )

        assert reviewed_plan.status == "active"
        assert reviewed_plan.reviewed_by == pharmacist.id
        assert reviewed_plan.review_note == "Approved after pharmacist review."
        assert reviewed_plan.reviewed_at is not None
        assert reviewed_plan.next_refill_at is not None

    finally:
        db_generator.close()


def test_pharmacist_can_reject_refill_plan(client):
    db, db_generator = get_test_db()

    try:
        customer, pharmacist, prescription, inventory = create_test_data(db)

        plan = create_refill_plan(
            db=db,
            customer_id=customer.id,
            prescription_id=prescription.id,
            interval_days=30,
        )

        reviewed_plan = review_refill_plan(
            db=db,
            plan_id=plan.id,
            pharmacist_id=pharmacist.id,
            decision="rejected",
            review_note="Rejected for testing.",
        )

        assert reviewed_plan.status == "rejected"
        assert reviewed_plan.reviewed_by == pharmacist.id
        assert reviewed_plan.review_note == "Rejected for testing."
        assert reviewed_plan.reviewed_at is not None

    finally:
        db_generator.close()


def test_customer_cannot_request_refill_before_due_date(client):
    db, db_generator = get_test_db()

    try:
        customer, pharmacist, prescription, inventory = create_test_data(db)

        plan = create_active_refill_plan(
            db,
            customer,
            pharmacist,
            prescription,
        )

        with pytest.raises(ValueError):
            create_refill_request(
                db=db,
                customer_id=customer.id,
                plan_id=plan.id,
            )

    finally:
        db_generator.close()


def test_customer_can_create_refill_request_when_due(client):
    db, db_generator = get_test_db()

    try:
        customer, pharmacist, prescription, inventory = create_test_data(db)

        plan = create_active_refill_plan(
            db,
            customer,
            pharmacist,
            prescription,
        )

        make_plan_due(db, plan)

        refill_request = create_refill_request(
            db=db,
            customer_id=customer.id,
            plan_id=plan.id,
        )

        assert refill_request.id is not None
        assert refill_request.plan_id == plan.id
        assert refill_request.status == "pending_review"

    finally:
        db_generator.close()


def test_pharmacist_can_approve_refill_request_and_create_order(client):
    db, db_generator = get_test_db()

    try:
        customer, pharmacist, prescription, inventory = create_test_data(db)

        plan = create_active_refill_plan(
            db,
            customer,
            pharmacist,
            prescription,
        )

        make_plan_due(db, plan)

        refill_request = create_refill_request(
            db=db,
            customer_id=customer.id,
            plan_id=plan.id,
        )

        result = approve_refill_request(
            db=db,
            request_id=refill_request.id,
            pharmacist_id=pharmacist.id,
            review_note="Refill approved after review.",
        )

        db.refresh(refill_request)
        db.refresh(plan)
        db.refresh(inventory)

        assert refill_request.status == "approved"
        assert refill_request.reviewed_by == pharmacist.id
        assert refill_request.review_note == "Refill approved after review."
        assert refill_request.order_id is not None

        order = db.get(Order, refill_request.order_id)

        assert order is not None
        assert order.customer_id == customer.id
        assert order.prescription_id == prescription.id
        assert inventory.reserved_quantity == 2
        assert plan.next_refill_at is not None
        assert plan.next_refill_at > datetime.now(timezone.utc).replace(
            tzinfo=None
        ) if plan.next_refill_at.tzinfo is None else plan.next_refill_at > datetime.now(timezone.utc)

    finally:
        db_generator.close()


@pytest.mark.parametrize("new_status", ["paused", "cancelled"])
def test_pausing_or_cancelling_plan_cancels_pending_requests(
    client,
    new_status,
):
    db, db_generator = get_test_db()

    try:
        customer, pharmacist, prescription, inventory = create_test_data(
            db,
            email=f"refill_{new_status}@example.com",
        )

        plan = create_active_refill_plan(
            db,
            customer,
            pharmacist,
            prescription,
        )

        make_plan_due(db, plan)

        refill_request = create_refill_request(
            db=db,
            customer_id=customer.id,
            plan_id=plan.id,
        )

        updated_plan = update_refill_plan_status(
            db=db,
            customer_id=customer.id,
            plan_id=plan.id,
            new_status=new_status,
        )

        db.refresh(refill_request)

        assert updated_plan.status == new_status
        assert refill_request.status == "cancelled"

    finally:
        db_generator.close()


def test_customer_can_list_only_own_refill_plans(client):
    customer_headers = role_headers(
        client, "plans-owner@example.com", "9876500001", "customer"
    )
    other_headers = role_headers(
        client, "plans-other@example.com", "9876500002", "customer"
    )

    db, db_generator = get_test_db()
    try:
        customer, pharmacist, prescription = create_api_refill_data(
            db, "plans-owner@example.com"
        )
        other_customer, _, other_prescription = create_api_refill_data(
            db, "plans-other@example.com"
        )
        create_refill_plan(db, customer.id, prescription.id, 30)
        create_refill_plan(db, other_customer.id, other_prescription.id, 30)
        other_customer_id = other_customer.id
    finally:
        db_generator.close()

    response = client.get(
        "/api/v1/refills/plans/my", headers=customer_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["customer_id"] != other_customer_id

    response = client.get(
        "/api/v1/refills/plans/my", headers=other_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["customer_id"] == other_customer.id


def test_pharmacist_and_admin_can_list_pending_refill_plan_queue(client):
    pharmacist_headers = role_headers(
        client, "queue-pharmacist@example.com", "9876500003", "pharmacist"
    )
    admin_headers = role_headers(
        client, "queue-admin@example.com", "9876500004", "admin"
    )

    db, db_generator = get_test_db()
    try:
        customer, pharmacist, prescription = create_api_refill_data(
            db, "queue-customer@example.com"
        )
        plan = create_refill_plan(
            db, customer.id, prescription.id, 30
        )
        pending_id = plan.id
    finally:
        db_generator.close()

    for headers in (pharmacist_headers, admin_headers):
        response = client.get(
            "/api/v1/refills/plans/queue", headers=headers
        )
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [pending_id]


def test_customer_cannot_access_refill_queues(client):
    headers = role_headers(
        client, "queue-customer@example.com", "9876500005", "customer"
    )

    assert client.get(
        "/api/v1/refills/plans/queue", headers=headers
    ).status_code == 403
    assert client.get(
        "/api/v1/refills/requests/queue", headers=headers
    ).status_code == 403


def test_customer_can_list_only_own_refill_requests(client):
    owner_headers = role_headers(
        client, "requests-owner@example.com", "9876500006", "customer"
    )
    other_headers = role_headers(
        client, "requests-other@example.com", "9876500007", "customer"
    )

    db, db_generator = get_test_db()
    try:
        owner, pharmacist, prescription = create_api_refill_data(
            db, "requests-owner@example.com"
        )
        other, other_pharmacist, other_prescription = create_api_refill_data(
            db, "requests-other@example.com"
        )
        _, owner_request = create_api_pending_request(
            db, owner.id, prescription.id, pharmacist.id
        )
        _, other_request = create_api_pending_request(
            db, other.id, other_prescription.id, other_pharmacist.id
        )
        owner_request_id = owner_request.id
        other_request_id = other_request.id
    finally:
        db_generator.close()

    response = client.get(
        "/api/v1/refills/requests/my", headers=owner_headers
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [owner_request_id]

    response = client.get(
        "/api/v1/refills/requests/my", headers=other_headers
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [other_request_id]


def test_pharmacist_and_admin_can_list_pending_refill_request_queue(client):
    pharmacist_headers = role_headers(
        client, "request-queue-pharmacist@example.com", "9876500008", "pharmacist"
    )
    admin_headers = role_headers(
        client, "request-queue-admin@example.com", "9876500009", "admin"
    )

    db, db_generator = get_test_db()
    try:
        customer, pharmacist, prescription = create_api_refill_data(
            db, "request-queue-customer@example.com"
        )
        _, refill_request = create_api_pending_request(
            db, customer.id, prescription.id, pharmacist.id
        )
        request_id = refill_request.id
    finally:
        db_generator.close()

    for headers in (pharmacist_headers, admin_headers):
        response = client.get(
            "/api/v1/refills/requests/queue", headers=headers
        )
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [request_id]


@pytest.mark.parametrize("decision, expected_status", [("approved", "active"), ("rejected", "rejected")])
def test_pharmacist_can_review_refill_plan_through_api(
    client, decision, expected_status
):
    headers = role_headers(
        client, f"plan-review-{decision}@example.com", "9876500010", "pharmacist"
    )
    db, db_generator = get_test_db()
    try:
        customer, pharmacist, prescription = create_api_refill_data(
            db, f"plan-review-customer-{decision}@example.com"
        )
        plan = create_refill_plan(db, customer.id, prescription.id, 30)
        plan_id = plan.id
    finally:
        db_generator.close()

    response = client.patch(
        f"/api/v1/refills/plans/{plan_id}/review",
        headers=headers,
        json={"decision": decision, "review_note": "API review note"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == expected_status
    assert response.json()["reviewed_by"] is not None

    db, db_generator = get_test_db()
    try:
        refreshed = db.get(RefillPlan, plan_id)
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "refill_plan",
                AuditLog.entity_id == plan_id,
                AuditLog.action == f"refill.plan_{decision}",
            )
        )
        assert refreshed.status == expected_status
        assert refreshed.review_note == "API review note"
        assert audit is not None
        assert refreshed.reviewed_by == audit.actor_id
        assert audit.details["review_note"] == "API review note"
    finally:
        db_generator.close()


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_pharmacist_can_review_refill_request_through_api(client, decision):
    headers = role_headers(
        client, f"request-review-{decision}@example.com", "9876500011", "pharmacist"
    )
    db, db_generator = get_test_db()
    try:
        customer, pharmacist, prescription = create_api_refill_data(
            db, f"request-review-customer-{decision}@example.com"
        )
        _, refill_request = create_api_pending_request(
            db, customer.id, prescription.id, pharmacist.id
        )
        request_id = refill_request.id
    finally:
        db_generator.close()

    response = client.patch(
        f"/api/v1/refills/requests/{request_id}/review",
        headers=headers,
        json={"decision": decision, "review_note": "Request API note"},
    )
    assert response.status_code == 200
    assert response.json()["refill_request"]["status"] == decision
    assert response.json()["refill_request"]["review_note"] == "Request API note"

    db, db_generator = get_test_db()
    try:
        refreshed = db.get(RefillRequest, request_id)
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "refill_request",
                AuditLog.entity_id == request_id,
                AuditLog.action == f"refill.request_{decision}",
            )
        )
        assert refreshed.status == decision
        assert refreshed.review_note == "Request API note"
        assert audit is not None
    finally:
        db_generator.close()


def test_refill_review_missing_ids_and_already_reviewed_records(client):
    headers = role_headers(
        client, "review-errors@example.com", "9876500012", "pharmacist"
    )
    missing_plan = client.patch(
        "/api/v1/refills/plans/999999/review",
        headers=headers,
        json={"decision": "approved"},
    )
    assert missing_plan.status_code == 404

    missing_request = client.patch(
        "/api/v1/refills/requests/999999/review",
        headers=headers,
        json={"decision": "rejected"},
    )
    assert missing_request.status_code == 404

    db, db_generator = get_test_db()
    try:
        customer, pharmacist, prescription = create_api_refill_data(
            db, "review-errors-customer@example.com"
        )
        plan = create_api_plan(
            db, customer.id, prescription.id, pharmacist.id, "approved"
        )
        make_plan_due(db, plan)
        refill_request = create_refill_request(
            db, customer.id, plan.id
        )
        plan_id = plan.id
        request_id = refill_request.id
    finally:
        db_generator.close()

    already_reviewed_plan = client.patch(
        f"/api/v1/refills/plans/{plan_id}/review",
        headers=headers,
        json={"decision": "rejected"},
    )
    assert already_reviewed_plan.status_code == 409

    approved_request = client.patch(
        f"/api/v1/refills/requests/{request_id}/review",
        headers=headers,
        json={"decision": "rejected"},
    )
    assert approved_request.status_code == 200

    already_reviewed_request = client.patch(
        f"/api/v1/refills/requests/{request_id}/review",
        headers=headers,
        json={"decision": "rejected"},
    )
    assert already_reviewed_request.status_code == 409


@pytest.mark.parametrize(
    "path, payload",
    [
        ("/api/v1/refills/plans/1/review", {"decision": "invalid"}),
        ("/api/v1/refills/requests/1/review", {"decision": "invalid"}),
        ("/api/v1/refills/plans/1/review", {"decision": "approved", "review_note": "x" * 501}),
        ("/api/v1/refills/requests/1/review", {"decision": "rejected", "review_note": "x" * 501}),
    ],
)
def test_refill_review_rejects_invalid_payloads(client, path, payload):
    headers = role_headers(
        client, "invalid-payload@example.com", "9876500013", "pharmacist"
    )
    response = client.patch(path, headers=headers, json=payload)
    assert response.status_code == 422
