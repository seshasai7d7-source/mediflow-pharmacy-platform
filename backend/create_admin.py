import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models import User


EMAIL = os.getenv("DEMO_ADMIN_EMAIL", "").strip().lower()
PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD", "")

if not EMAIL or not PASSWORD:
    raise SystemExit(
        "Set DEMO_ADMIN_EMAIL and DEMO_ADMIN_PASSWORD before running this script."
    )

if len(PASSWORD) < 12:
    raise SystemExit("The demo admin password must be at least 12 characters.")

db = SessionLocal()

try:
    existing_user = db.scalar(
        select(User).where(User.email == EMAIL)
    )

    if existing_user:
        if existing_user.role != "admin":
            raise ValueError("The configured email belongs to a non-admin account.")
        existing_user.password_hash = hash_password(PASSWORD)
        db.commit()

        print("Admin account password updated sucessfully.")
        print("Email:", EMAIL)
    else:
        admin = User(
            full_name="MediFlow Admin",
            email=EMAIL,
            password_hash=hash_password(PASSWORD),
            role="admin",
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print("Admin account created successfully.")
        print("Email:", EMAIL)

except Exception:
    db.rollback()
    raise

finally:
    db.close()
