from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.database import get_db

router = APIRouter(tags=["health"])

@router.get("/health")
def health_check() -> dict[str, str]:
    # Liveness: confirms the API process is responding.
    return {"status": "ok", "service": "mediflow-api"}

@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)) -> dict[str, str]:
    # Readiness: confirms that PostgreSQL is reachable.
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc
    return {"status": "ready", "database": "connected"}
