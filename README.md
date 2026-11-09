# MediFlow Pharmacy Platform

MediFlow is a pharmacy ordering and prescription-review platform built with FastAPI, PostgreSQL, React, and TypeScript.

The application demonstrates customer registration and authentication, medicine inventory, prescription submission, pharmacist review, and order management.

## Features

### Customer
- Register and sign in securely.
- Browse available medicine inventory.
- Submit prescription documents.
- View prescription review status.
- View orders and their current status.

### Pharmacist
- View the prescription review queue.
- Inspect prescription details and AI-extracted information.
- Review and edit medicine details before making a decision.
- Approve or reject prescriptions with a review decision.
- Manage order status through supported workflow transitions.
- View all pharmacy orders in the Order Management page.
- Update orders through confirmed, preparing, ready, dispatched, and delivered statuses.
- Cancel eligible orders according to backend workflow rules.

### Backend and business rules
- Role-based access for customers, pharmacists, and administrators.
- Password hashing and JWT-based authentication.
- PostgreSQL persistence using SQLAlchemy.
- Database schema migrations using Alembic.
- Inventory reservation and release during order workflows.
- Audit logging for important review and order actions.
- Gemini-powered prescription information extraction, treated as a draft for pharmacist review.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Authentication | JWT, password hashing |
| AI | Google Gemini API |
| Testing | Pytest, HTTPX |
| Infrastructure | Docker Compose |

## Prerequisites

- Python 3.14
- Node.js 20 or newer
- npm
- Docker Desktop with Docker Compose
- Git

## Project Structure

```text
mediflow-pharmacy-platform/
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── .env.example
├── docker-compose.yml
├── README.md
├── TDD.md
└── deployment.md
```

## Local Setup

### Prerequisites
- Python 3.14
- Node.js 20 or newer
- npm
- Docker Desktop with Docker Compose
- Git

### 1. Start PostgreSQL

From the repository root:

```powershell
docker compose up -d db
docker compose ps
```

Wait until the database reports healthy.

PostgreSQL is exposed on host port `5433`.

### 2. Configure and start the backend

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and configure:
- `DATABASE_URL` using host port `5433`.
- `JWT_SECRET_KEY` with a long random secret.
- `FRONTEND_ORIGINS=http://localhost:5173`.
- `GEMINI_API_KEY` with your Google Gemini API key, if AI extraction is required.

Run migrations and start the API:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

Backend: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/api/v1/health

### 3. Start the frontend

Open another PowerShell terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173.

The frontend API URL is configured through `VITE_API_BASE_URL`.

## Running Tests

From the backend directory with its virtual environment activated:

```powershell
python -m pytest -q
```
Latest verified backend test result: **140 passed, 1 warning**.

The frontend production build was also verified successfully using `npm run build`.

## Production Frontend Build

From the frontend directory:

```powershell
npm run build
```

Build output is generated in `frontend/dist`.

## Prescription Safety

AI-extracted prescription information is a draft for pharmacist review. It does not approve prescriptions or authorize dispensing.

A pharmacist must review prescription details before approval. The application includes restrictions for prohibited medicine schedule categories and requires customer consent for generic substitution.

Use only synthetic documents and test data for demonstrations. Do not use this development setup to process real prescriptions or customer information.

## Known Demo Limitations

- This project is a demonstration and has not been validated for production pharmacy operations.
- Payment processing and a live payment gateway are not implemented.
- Medicine pricing is not configured as a complete business pricing catalogue; demonstration order totals may be zero.
- AI extraction can be incomplete or unavailable and requires manual pharmacist review.
- Production deployment requires secure secrets management, HTTPS, monitoring, backups, and appropriate privacy and regulatory review.

## Security Notes

- Never commit `.env` files, API keys, JWT secrets, database passwords, uploaded prescriptions, or customer data.
- Replace local development credentials before deployment.
- Use HTTPS and managed secrets in a real deployment.
- Restrict database and administrative access.
- Use synthetic data for evaluation and demonstrations.