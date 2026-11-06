
from sqlalchemy import select

from app.db.database import get_db
from app.models import Medicine

MEDICINE_NAME = "MediFlow Demo Medicine"

db_generator = get_db()
db = next(db_generator)

try:
    medicine = db.scalar(
        select(Medicine).where(
            Medicine.name == MEDICINE_NAME
        )
    )

    if medicine is None:
        medicine = Medicine(
            name=MEDICINE_NAME,
            generic_name=None,
            brand_name=None,
            strength="250 mg",
            dosage_form="Tablet",
            schedule_category="H",
            requires_prescription=True,
            is_active=True,
        )

        db.add(medicine)
        db.commit()
        db.refresh(medicine)

        print("Demo medicine created successfully.")

    else:
        print("Demo medicine already exists.")

    print("Medicine ID:", medicine.id)
    print("Name:", medicine.name)
    print("Schedule:", medicine.schedule_category)
    print("Active:", medicine.is_active)

finally:
    db.close()
    db_generator.close()
