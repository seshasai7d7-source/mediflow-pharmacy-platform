
from datetime import datetime, timedelta, timezone

import pytest

from app.db.database import get_db
from app.main import app
from app.models import (
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
