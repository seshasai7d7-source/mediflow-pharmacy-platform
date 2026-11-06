
from sqlalchemy import select

from app.core.security import hash_password, create_access_token
from app.db.database import get_db
from app.models import User

PHARMACIST_EMAIL = "pharmacist.demo@mediflow.local"
PHARMACIST_PASSWORD = "PharmacistDemo#2026"

db_generator = get_db()
db = next(db_generator)

try:
    pharmacist = db.scalar(
        select(User).where(User.email == PHARMACIST_EMAIL)
    )

    if pharmacist is None:
        pharmacist = User(
            full_name="Demo Pharmacist",
            email=PHARMACIST_EMAIL,
            password_hash=hash_password(PHARMACIST_PASSWORD),
            role="pharmacist",
            is_active=True,
        )

        db.add(pharmacist)
        db.commit()
        db.refresh(pharmacist)

        print("Pharmacist account created successfully.")

    elif pharmacist.role != "pharmacist":
        raise ValueError(
            "This email already belongs to a non-pharmacist account."
        )
    else:
        print("Pharmacist account already exists.")

    token = create_access_token(pharmacist.id)

    print("Email:", pharmacist.email)
    print("Role:", pharmacist.role)
    print("Password:", PHARMACIST_PASSWORD)
    print("Access token:", token)

finally:
    db.close()
    db_generator.close()
