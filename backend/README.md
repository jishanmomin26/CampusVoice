# CampusVoice — Backend Service

FastAPI REST backend and PostgreSQL database foundation for the **CampusVoice** AI-Powered Student Feedback Intelligence platform.

---

## 1. Backend Overview
The backend provides the API service and database connectivity for ingesting and managing student feedback across campus departments and academic semesters. It uses:
* **Framework**: FastAPI (Python 3.10+)
* **Database**: PostgreSQL 18+
* **ORM**: SQLAlchemy 2.x
* **Driver**: psycopg (psycopg3)
* **Migrations**: Alembic
* **Data Validation**: Pydantic v2 & `pydantic-settings`

---

## 2. Prerequisites
* **Python**: 3.10+ installed
* **PostgreSQL**: Version 18+ running on `localhost:5432` with a database named `campusvoice`.

---

## 3. Python Environment Setup & Dependencies

From the `backend/` directory:

### Windows (PowerShell):
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS / Linux:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 4. Environment Configuration (`.env`)

Copy `backend/.env.example` to `backend/.env` (or update `backend/.env`):
```powershell
cp .env.example .env
```

Edit `backend/.env` with your local PostgreSQL credentials:
```env
# PostgreSQL Database Connection (SQLAlchemy 2.x + psycopg3)
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/campusvoice

# Frontend Origin for CORS
FRONTEND_URL=http://localhost:5173
```

> **Security Note**: `backend/.env` is strictly excluded from version control via `.gitignore`. Never commit passwords or credentials to Git.

---

## 5. Database Migrations (Alembic)

Alembic manages all database schema changes. To apply the initial migration that creates the `feedback` table:

```powershell
# Ensure your virtual environment is active and you are in the backend/ directory:
alembic upgrade head
```

### Useful Alembic Commands:
* Check current revision:
  ```powershell
  alembic current
  ```
* View migration history:
  ```powershell
  alembic history
  ```
* Rollback last migration (if needed):
  ```powershell
  alembic downgrade -1
  ```

---

## 6. Running FastAPI Server

Start the FastAPI development server with auto-reload:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 7. Interactive Documentation (Swagger / OpenAPI)

Once the server is running, visit:
* **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Alternative ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 8. API Endpoints

### Health Check
* `GET /health` or `GET /api/v1/health`
  * Returns:
    ```json
    {
      "status": "healthy",
      "service": "CampusVoice API",
      "version": "0.1.0"
    }
    ```

### Feedback Ingestion
* `POST /api/v1/feedback`
  * Status: `201 Created`
  * Request Body:
    ```json
    {
      "department": "Computer Science",
      "semester": "Semester 6",
      "feedback_text": "The computer network laboratory routers require updated firmware."
    }
    ```
  * Response Body:
    ```json
    {
      "id": 1,
      "department": "Computer Science",
      "semester": "Semester 6",
      "feedback_text": "The computer network laboratory routers require updated firmware.",
      "created_at": "2026-09-12T21:30:00+00:00"
    }
    ```

### Feedback Retrieval
* `GET /api/v1/feedback`
  * Status: `200 OK`
  * Returns an array of stored feedback records ordered by newest first:
    ```json
    [
      {
        "id": 1,
        "department": "Computer Science",
        "semester": "Semester 6",
        "feedback_text": "The computer network laboratory routers require updated firmware.",
        "created_at": "2026-09-12T21:30:00+00:00"
      }
    ]
    ```

---

## 9. Backend Project Structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── health.py
│   │           └── feedback.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── feedback.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── feedback.py
│   ├── __init__.py
│   └── main.py
├── alembic/
│   ├── versions/
│   │   └── 001_create_feedback_table.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── requirements.txt
├── .env.example
├── .env                  (local, gitignored)
└── README.md
```
