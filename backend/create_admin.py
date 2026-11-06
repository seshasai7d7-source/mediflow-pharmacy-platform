
from sqlalchemy import select

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models import User


EMAIL = "admin.demo@gmail.com"
PASSWORD = "AdminDemo#2026"

db = SessionLocal()

try:
    existing_user = db.scalar(
        select(User).where(User.email == EMAIL)
    )

    if existing_user:
        print("Demo admin already exists.")
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

        print("Demo admin created successfully.")
        print("Email:", EMAIL)
        print("Role: admin")

finally:
    db.close()
