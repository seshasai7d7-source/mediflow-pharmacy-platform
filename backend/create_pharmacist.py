import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models import User


EMAIL = os.getenv("DEMO_PHARMACIST_EMAIL", "").strip().lower()
PASSWORD = os.getenv("DEMO_PHARMACIST_PASSWORD", "")

if not EMAIL or not PASSWORD:
    raise SystemExit(
        "Set DEMO_PHARMACIST_EMAIL and DEMO_PHARMACIST_PASSWORD before running this script."
    )

if len(PASSWORD) < 12:
    raise SystemExit("The demo pharmacist password must be at least 12 characters.")

db = SessionLocal()

try:
    pharmacist = db.scalar(
        select(User).where(User.email == EMAIL)
    )

    if pharmacist:
        if pharmacist.role != "pharmacist":
            raise ValueError(
                "The configured email belongs to a non-pharmacist account."
            )

        pharmacist.password_hash = hash_password(PASSWORD)
        db.commit()

        print("Pharmacist account password updated successfully.")
        print("Email:", EMAIL)

    else:
        pharmacist = User(
            full_name="Demo Pharmacist",
            email=EMAIL,
            password_hash=hash_password(PASSWORD),
            role="pharmacist",
            is_active=True,
        )

        db.add(pharmacist)
        db.commit()

        print("Pharmacist account created successfully.")
        print("Email:", EMAIL)

except Exception:
    db.rollback()
    raise

finally:
    db.close()