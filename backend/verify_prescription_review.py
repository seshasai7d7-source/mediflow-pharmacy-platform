
from sqlalchemy import select

from app.db.database import get_db
from app.models import AuditLog, Prescription, PrescriptionItem

db_generator = get_db()
db = next(db_generator)

try:
    prescription = db.get(Prescription, 2)

    print("\n--- Prescription ---")
    print("ID:", prescription.id)
    print("Status:", prescription.status)
    print("Pharmacist ID:", prescription.pharmacist_id)
    print("Reviewed at:", prescription.reviewed_at)

    items = db.scalars(
        select(PrescriptionItem).where(
            PrescriptionItem.prescription_id == 2
        )
    ).all()

    print("\n--- Verified Medicine Items ---")
    for item in items:
        print("Medicine ID:", item.medicine_id)
        print("Medicine:", item.extracted_name)
        print("Quantity:", item.quantity)
        print("Pharmacist approved:", item.pharmacist_approved)

    logs = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.entity_type == "prescription",
            AuditLog.entity_id == 2,
        )
        .order_by(AuditLog.created_at.desc())
    ).all()

    print("\n--- Audit Logs ---")
    for log in logs:
        print("Action:", log.action)
        print("Actor ID:", log.actor_id)
        print("Details:", log.details)

finally:
    db.close()
    db_generator.close()
