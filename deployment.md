# MediFlow Pharmacy Platform
## Deployment Guide

**Version:** 1.0  
**Date:** November 2026

## 1. Overview

This guide describes how to configure and run the MediFlow Pharmacy Platform in a local development or demonstration environment.

The application consists of:

- React and TypeScript frontend.
- FastAPI backend.
- PostgreSQL 16 database.
- Optional Google Gemini API integration for prescription information extraction.

This guide does not describe a production-ready deployment. Use synthetic data only.

## 2. Prerequisites

Install the following:

- Windows 10/11 or a compatible operating system.
- Python 3.14.
- Node.js 20 or newer.
- npm.
- Docker Desktop with Docker Compose.
- Git.

Verify installations:

```powershell
python --version
node --version
npm --version
docker --version
docker compose version
git --version
```

## 3. Obtain the Source Code

Clone the repository:

```powershell
git clone https://github.com/seshasai7d7-source/mediflow-pharmacy-platform.git
cd mediflow-pharmacy-platform
```

If the source code is already available locally, open PowerShell in the repository root.

## 4. Configure PostgreSQL

Start the database:

```powershell
docker compose up -d db
docker compose ps
```

Wait for the database health check to report healthy.

The supplied Docker Compose configuration uses:

| Setting | Value |
|---|---|
| Database | mediflow |
| Username | mediflow |
| Host port | 5433 |
| Container port | 5432 |
| Container | mediflow-postgres |

The default password is for local development only. Replace it before using the environment beyond a local demonstration.

## 5. Configure the Backend

Navigate to the backend:

```powershell
cd backend
```

Create and activate a virtual environment:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Edit `backend/.env` and configure:

| Variable | Description |
|---|---|
| APP_NAME | Application name |
| APP_ENV | Application environment |
| ENABLE_DEV_AUTH | Development authentication setting |
| API_V1_PREFIX | Versioned API prefix |
| DATABASE_URL | PostgreSQL connection string |
| FRONTEND_ORIGINS | Allowed frontend origins |
| JWT_SECRET_KEY | Secret used for signing JWTs |
| JWT_ALGORITHM | JWT signing algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | Access token lifetime |
| GEMINI_API_KEY | Optional Gemini API key |
| GEMINI_MODEL | Gemini model name |

For the supplied Docker Compose configuration, the database URL must use host port `5433`:

```text
postgresql+psycopg://mediflow:YOUR_PASSWORD@localhost:5433/mediflow
```

Replace the JWT placeholder with a strong, randomly generated secret. Never use a sample or default secret outside local development.

To enable Gemini extraction, configure a valid API key. Without it, the application should be tested using the pharmacist's manual-review workflow and the configured fallback behavior.

## 6. Apply Database Migrations

With the backend virtual environment active and the terminal in the `backend` directory:

```powershell
alembic upgrade head
```

This applies the database schema migrations.

## 7. Start the Backend

From the `backend` directory:

```powershell
uvicorn app.main:app --reload
```

The backend is available at:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- Health endpoint: http://127.0.0.1:8000/api/v1/health

Keep this terminal running.

## 8. Configure and Start the Frontend

Open another PowerShell terminal and navigate to the frontend directory:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

The frontend environment variable is:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the frontend:

```powershell
npm run dev
```

Open:

http://localhost:5173

## 9. Verification

Verify the following components:

### Database

```powershell
docker compose ps
```

Confirm that the PostgreSQL container is healthy.

### Backend

Open:

http://127.0.0.1:8000/api/v1/health

Confirm that the API responds successfully.

### API documentation

Open:

http://127.0.0.1:8000/docs

Confirm that Swagger UI loads.

### Frontend

Open:

http://localhost:5173

Verify that the application loads and reports backend connectivity.

### Authentication and workflows

Using demonstration accounts and synthetic data:

1. Register a customer account.
2. Sign in as a customer.
3. Submit a synthetic prescription document.
4. Sign in using a pharmacist demonstration account.
5. Open the pharmacist prescription queue.
6. Review the submitted prescription.
7. Verify rejection behavior using an invalid synthetic prescription.
8. Approve a suitable synthetic prescription.
9. Open Pharmacist Order Management.
10. Verify that the pharmacist can view customer orders.
11. Test the supported order status transitions:
    confirmed → preparing → ready → dispatched → delivered.
12. Refresh the page and verify that the final order status persists.
13. Verify that a customer cannot access the pharmacist Order Management page.
14. Test cancellation of an eligible order and verify that reserved inventory is released.

Do not approve invalid synthetic prescriptions.

## 10. Run Automated Tests

From the backend directory with the virtual environment active:

```powershell
python -m pytest -q
```

A successful test run should report all tests passing.

## 11. Build the Frontend

From the frontend directory:

```powershell
npm run build
```

Vite generates the production frontend assets in:

```text
frontend/dist/
```

## 12. Shutdown

Stop the frontend and backend using `Ctrl + C` in their respective terminals.

Stop the PostgreSQL container from the repository root:

```powershell
docker compose down
```

To remove the local database volume as well:

```powershell
docker compose down -v
```

**Warning:** Removing the volume permanently deletes the local PostgreSQL database and its stored data.

## 13. Security and Deployment Notes

- Do not commit `.env` files or API credentials.
- Use strong, unique secrets.
- Do not expose the local PostgreSQL port publicly.
- Use HTTPS in a real deployment.
- Restrict access to uploaded prescription documents.
- Use managed secrets and secure database credentials.
- Configure backups, monitoring, and access logging.
- Perform appropriate privacy, security, and regulatory reviews before any real pharmacy use.

## 14. Known Limitations

This deployment is intended for development and demonstration purposes.

- Payment gateway integration is not implemented.
- Medicine pricing is not configured as a complete business pricing catalogue.
- AI extraction requires pharmacist review.
- Production hosting, monitoring, backup automation, and regulatory validation are not included.

Do not process real prescriptions or customer data using this demonstration deployment.