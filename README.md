# MediFlow — Day 1 starter

Day 1 foundation: React + TypeScript, FastAPI, PostgreSQL 16 via Docker Compose, environment configuration, readiness endpoint and backend tests.

## Prerequisites
- Python 3.12
- Node.js 20 LTS or newer
- npm
- Docker Desktop with Docker Compose
- Git

## Start PostgreSQL
From the repository root:
```powershell
docker compose up -d db
docker compose ps
```
Wait for the database health status to become `healthy`.

## Start backend
```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```
API: http://127.0.0.1:8000  
Swagger: http://127.0.0.1:8000/docs  
Liveness: http://127.0.0.1:8000/api/v1/health  
Database readiness: http://127.0.0.1:8000/api/v1/ready

## Start frontend
Open another PowerShell terminal from the repository root:
```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```
Open http://localhost:5173.

## Run tests
In the backend terminal:
```powershell
pytest -q
```

## Local database credentials
The Docker Compose defaults are for local development only. Do not reuse them outside your machine. Use strong credentials and a managed secrets service in deployment.

## Day 1 limitations
OTP, real sign-in, pharmacist workflows, prescription OCR/LLM extraction, inventory routing, refill scheduling and payments are not implemented yet. Do not use this starter with real prescriptions or customer data.
