from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse
from app.schemas.user import UserResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    email = str(user_data.email).lower()

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    if user_data.phone:
        existing_phone = db.scalar(
            select(User).where(User.phone == user_data.phone)
        )

        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number is already registered",
            )

    new_user = User(
        full_name=user_data.full_name,
        email=email,
        phone=user_data.phone,
        password_hash=hash_password(user_data.password),
        role="customer",
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or phone number is already registered",
        )

    return new_user


@router.post("/login", response_model=TokenResponse)
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db),
):
    email = str(user_data.email).lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if (
        user is None
        or not user.is_active
        or not verify_password(user_data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,
    )


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user