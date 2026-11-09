# MediFlow Pharmacy Platform
## Deployment Guide

**GitHub Repository:** https://github.com/seshasai7d7-source/mediflow-pharmacy-platform

**Version:** 1.1  
**Date:** November 2026  
**Deployment Status:** Local development and demonstration only

---

## 1. Overview

This guide describes how to configure, run, and verify the MediFlow Pharmacy Platform in a local development or demonstration environment.

The application consists of:

- React 19 and TypeScript frontend.
- FastAPI backend.
- PostgreSQL 16 database.
- Google Gemini API integration for AI-assisted prescription information extraction.

The application includes customer authentication, prescription submission, pharmacist review, order management, inventory reservation, refill plan and request workflows, and administrative functionality.

This is not a production deployment. Use synthetic demonstration data only.

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

Clone the public repository:

```powershell
git clone https://github.com/seshasai7d7-source/mediflow-pharmacy-platform.git
cd mediflow-pharmacy-platform
```

If the repository is already available locally, open PowerShell in its root directory.

## 4. Start PostgreSQL

From the repository root:

```powershell
docker compose up -d db
docker compose ps
```

Wait for the PostgreSQL health check to report healthy.

The supplied Docker Compose configuration uses:

| Setting | Value |
|---|---|
| Database | mediflow |
| Username | mediflow |
| Host port | 5433 |
| Container port | 5432 |
| Container | mediflow-postgres |

The Compose configuration contains a development-only default database password. It must be replaced with a strong local value before using the environment beyond a local demonstration.

If you change the database credentials, keep the Compose configuration and backend `DATABASE_URL` consistent.

## 5. Configure the Backend

Navigate to the backend directory:

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

Edit `backend/.env` and configure the following variables:

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

Replace `YOUR_PASSWORD` with the password configured for your local database.

Generate a strong, unique JWT secret. Do not use a sample or default secret outside local development.

To enable Gemini extraction, configure a valid API key. If Gemini is unavailable or extraction is incomplete, the prescription workflow must be handled through pharmacist review and the application's manual-review fallback.

## 6. Apply Database Migrations

With the backend virtual environment active and the terminal in the `backend` directory:

```powershell
alembic upgrade head
```

This applies the database schema migrations, including the refill-related tables.

## 7. Configure Demonstration Accounts

Privileged demonstration accounts are provisioned separately from public customer registration.

Create or update the administrator account:

```powershell
$env:DEMO_ADMIN_EMAIL = "admin.demo@gmail.com"
$env:DEMO_ADMIN_PASSWORD = Read-Host "Enter the demo admin password" -AsSecureString | ForEach-Object {
    [System.Net.NetworkCredential]::new("", $_).Password
}

python .\create_admin.py
```

Create or update the pharmacist account:

```powershell
$env:DEMO_PHARMACIST_EMAIL = "pharmacist.demo@mediflow.local"
$env:DEMO_PHARMACIST_PASSWORD = Read-Host "Enter the demo pharmacist password" -AsSecureString | ForEach-Object {
    [System.Net.NetworkCredential]::new("", $_).Password
}

python .\create_pharmacist.py
```

Use a different strong password of at least 12 characters for each account.

The scripts:

- Read account credentials from environment variables.
- Create the account if it does not exist.
- Update the password hash if the account already exists with the expected role.
- Reject an existing account if its role does not match.
- Do not print passwords or access tokens.

The environment variables are local to the current PowerShell session. Do not commit credentials or place real passwords in this guide.

### Demonstration login identifiers

| Role | Email |
|---|---|
| Administrator | admin.demo@gmail.com |
| Pharmacist | pharmacist.demo@mediflow.local |
| Customer | Register through the application |

The administrator and pharmacist passwords are the values configured locally during account setup. No shared password is included in this document.

## 8. Start the Backend

From the `backend` directory:

```powershell
uvicorn app.main:app --reload
```

The backend is available at:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- Health endpoint: http://127.0.0.1:8000/api/v1/health

Keep this terminal running.

## 9. Configure and Start the Frontend

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

Configure the frontend environment variable:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the frontend:

```powershell
npm run dev
```

Open the application:

http://localhost:5173

## 10. Verification

### Database

From the repository root:

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

### Customer workflow

Using synthetic data:

1. Register a customer account.
2. Sign in as the customer.
3. Browse the medicine inventory.
4. Submit a synthetic prescription document.
5. View the prescription status.
6. View available order information.
7. Create and manage a refill plan using an eligible approved prescription.

### Pharmacist workflow

1. Sign in using the pharmacist demonstration account.
2. Open the prescription review queue.
3. Inspect a submitted synthetic prescription.
4. Review the extracted medicine information.
5. Test the manual-review fallback where applicable.
6. Reject an invalid synthetic prescription.
7. Approve a suitable synthetic prescription.
8. Open Pharmacist Order Management.
9. Verify supported order status transitions:

   `confirmed → preparing → ready → dispatched → delivered`

10. Refresh the page and verify that the order status persists.
11. Review pending refill plans and refill requests.

Do not approve invalid synthetic prescriptions.

### Administrator workflow

1. Sign in using the administrator demonstration account.
2. Open the administrative overview.
3. Review user and store information.
4. Verify available operational counts and status information.
5. Test supported user and store management operations.

### Authorization

Verify that:

- Customers cannot access pharmacist-only operations.
- Customers cannot access administrator-only operations.
- Pharmacist accounts cannot access administrator-only operations.
- Public registration creates customer accounts only.

## 11. Run Automated Tests

From the `backend` directory with the virtual environment active:

```powershell
python -m pytest -q
```

Latest development verification:

```text
170 passed
```

The test suite uses isolated test database configuration and mocked external AI behavior where appropriate.

## 12. Build the Frontend

From the `frontend` directory:

```powershell
npm run build
```

Vite generates the production frontend assets in:

```text
frontend/dist/
```

Latest development verification completed successfully.

## 13. Shutdown

Stop the frontend and backend using `Ctrl + C` in their respective terminals.

Stop PostgreSQL from the repository root:

```powershell
docker compose down
```

To remove the local database volume as well:

```powershell
docker compose down -v
```

**Warning:** Removing the volume permanently deletes the local PostgreSQL database and its stored data.

## 14. Security and Deployment Notes

- Do not commit `.env` files or API credentials.
- Use strong, unique secrets.
- Do not expose the local PostgreSQL port publicly.
- Use HTTPS in a real deployment.
- Restrict access to uploaded prescription documents.
- Use managed secrets and secure database credentials.
- Configure backups, monitoring, and access logging.
- Perform appropriate privacy, security, and regulatory reviews before real pharmacy use.
- Rotate demonstration credentials before any deployment beyond local evaluation.

## 15. Known Limitations

This deployment is intended for development and demonstration purposes.

- Payment gateway integration is not implemented.
- Medicine pricing is not configured as a complete business pricing catalogue.
- AI extraction requires pharmacist review.
- Refill requests require explicit customer and pharmacist/admin actions; automated reminders and recurring orders are not implemented.
- OTP authentication, family profiles, and multilingual interfaces are not implemented.
- Production hosting, monitoring, backup automation, and regulatory validation are not included.

**Do not process real prescriptions or customer data using this demonstration deployment.**

---

**End of Deployment Guide**