from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.pharmacist import router as pharmacist_router
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.prescriptions import router as prescriptions_router
from app.core.config import get_settings
from app.api.v1.stores import router as stores_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.orders import router as orders_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="MediFlow pharmacy reordering and prescription verification API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# API routes
app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(prescriptions_router, prefix=settings.api_v1_prefix)
app.include_router(pharmacist_router,prefix=settings.api_v1_prefix,)
app.include_router(stores_router, prefix=settings.api_v1_prefix)
app.include_router(inventory_router, prefix=settings.api_v1_prefix)
app.include_router(orders_router, prefix=settings.api_v1_prefix)
@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {
        "message": "Welcome to MediFlow API",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
    }