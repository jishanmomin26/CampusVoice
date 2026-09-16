# CampusVoice — Backend Service

FastAPI REST backend, PostgreSQL relational persistence, and Machine Learning intelligence service for the **CampusVoice** AI-Powered Student Feedback Intelligence platform.

---

## 1. Backend Overview

The backend service provides the core API routing, database persistence, natural language processing, and machine learning inference for student feedback collection and institutional administrative analytics.

* **Framework**: FastAPI (Python 3.10+, tested on Python 3.13)
* **Server**: Uvicorn (ASGI)
* **Database**: PostgreSQL 18+ (Local) / Neon PostgreSQL (Production)
* **ORM**: SQLAlchemy 2.x
* **Driver**: psycopg3 (`psycopg[binary]`)
* **Migrations**: Alembic
* **Data Validation**: Pydantic v2 & `pydantic-settings`
* **NLP & Text Processing**: NLTK, spaCy (`en_core_web_sm`)
* **Machine Learning**: scikit-learn, joblib
* **Authentication**: PyJWT (`HS256`), bcrypt (12 rounds)
* **Testing**: pytest, HTTPX

---

## 2. Prerequisites

* **Python**: 3.10+ installed
* **PostgreSQL**: PostgreSQL 18+ running on `localhost:5432` with a database named `campusvoice` (or a cloud PostgreSQL instance like Neon).

---

## 3. Local Environment Setup & Installation

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

## 4. NLP Resources & Model Setup

The NLP pipeline requires the NLTK `stopwords` corpus and the spaCy English language model `en_core_web_sm`. These are installed explicitly via setup scripts rather than triggering network downloads during application startup or request processing.

### Local Development Setup
```powershell
# 1. Download required NLTK resources
python backend/scripts/install_nltk_resources.py

# 2. Download and verify spaCy English model
python backend/scripts/install_spacy_model.py
```

### Production Build Flow (Render)
During production deployment on Render, both resources are deterministically downloaded and verified at build time by [`render-build.sh`](file:///d:/Projects%20Of%20JISHAN/CampusVoice/render-build.sh):
```bash
#!/usr/bin/env bash
set -e

pip install -r backend/requirements.txt
python backend/scripts/install_nltk_resources.py
python backend/scripts/install_spacy_model.py
```
> [!NOTE]
> The application strictly avoids runtime network downloads inside `get_spacy_model()` and `get_stopwords()`. If resources are missing, an explicit `MissingNLPResourceError` is raised immediately.

---

## 5. Environment Configuration (`.env`)

Copy `backend/.env.example` to `backend/.env`:
```powershell
cp .env.example .env
```

### Configuration Variables (`backend/app/core/config.py`)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | string | `development` | Environment mode (`development`, `production`, `testing`). |
| `DATABASE_URL` | string | *Local fallback* | Connection string: `postgresql+psycopg://user:pass@host:port/db`. |
| `FRONTEND_URL` | string | `http://localhost:5173` | Allowed frontend URL for CORS. |
| `CORS_ALLOWED_ORIGINS` | string | `None` | Optional comma-separated list of additional allowed origins. |
| `JWT_SECRET_KEY` | string | *Dev placeholder* | Secret key for signing JWT tokens ($\ge 32$ characters). |
| `JWT_ALGORITHM` | string | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `60` | JWT access token expiration in minutes. |
| `ADMIN_USERNAME` | string | `admin` | Initial admin username for seeding. |
| `ADMIN_PASSWORD` | string | `None` | Initial admin password for seeding. |

### Production Configuration Hardening (Step 9.18.1)
When `ENVIRONMENT=production`, strict validation is enforced at application startup:
* `DATABASE_URL` must be explicitly configured and cannot point to `localhost`, `127.0.0.1`, `0.0.0.0`, or `::1`.
* `JWT_SECRET_KEY` must be explicitly configured, cannot match the development placeholder, and must be at least 32 characters long.
* `CORS_ALLOWED_ORIGINS` or a non-localhost `FRONTEND_URL` must be provided. Wildcard origins (`*`) are disallowed when credentials are enabled.
* Error messages sanitize and omit all connection strings, credentials, and secrets.

---

## 6. Database Migrations (Alembic)

Database schemas are managed version-by-version using Alembic migrations in `backend/alembic/versions/`:

### Migration History:
1. `001_create_feedback`: Creates the `feedback` table for raw submissions (`id`, `department`, `semester`, `feedback_text`, `created_at`, `updated_at`).
2. `002_add_analysis_fields`: Extends `feedback` table with ML analysis fields (`clean_text`, `sentiment_label`, `sentiment_score`, `sentiment_confidence`, `category_label`, `category_confidence`, `priority_score`, `priority_level`, `priority_reason`) and makes department/semester optional.
3. `003_create_users`: Creates the `users` table for JWT authentication and RBAC (`id`, `username`, `password_hash`, `role`, `is_active`, `created_at`, `updated_at`).

### Migration Commands:
```powershell
# Apply all pending migrations
alembic upgrade head

# Check current revision
alembic current

# View revision history
alembic history
```

---

## 7. Running the FastAPI Server

Start the local development server with auto-reload:
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive OpenAPI documentation is available at:
* **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 8. API Endpoints Reference

### Root & Health
* `GET /`: Welcome endpoint returning service metadata and API pointers.
* `GET /health` & `GET /api/v1/health`: Service health checks returning `{ "status": "healthy" }`.

### Student Feedback & Intelligence
* `POST /api/v1/feedback`: Submits raw student feedback into PostgreSQL.
  * *Request*: `{ "feedback_text": "...", "department": "...", "semester": "..." }`
  * *Response*: `HTTP 201 Created` with saved `FeedbackResponse`.
* `GET /api/v1/feedback`: Retrieves recent feedback records.
* `POST /api/v1/feedback/analyze`: Runs the unified feedback intelligence pipeline (NLP + TF-IDF + Sentiment + Category + Priority) without saving to the database.
  * *Request*: `{ "feedback": "The faculty explains concepts clearly." }`
  * *Response*: Returns predictions, confidence scores, probability distributions, and priority justification.
* `POST /api/v1/feedback/analyze-and-save`: Analyzes feedback and commits the record and intelligence output to PostgreSQL in a single atomic transaction.

### Administrative Analytics & Records
* `GET /api/v1/feedback/stats` *(Admin Only)*:
  * Returns aggregate metrics: total feedback volume, analyzed count, sentiment counts and percentages, priority distributions, and category breakdown.
* `GET /api/v1/feedback/records` *(Admin Only)*:
  * Returns paginated, searchable feedback records.
  * *Query parameters*: `page` (default 1), `page_size` (default 10, max 100), `search` (case-insensitive keyword), `sentiment`, `category`, `priority`.
  * *Ordering*: Strictly newest-first (`created_at DESC, id DESC`).

### Authentication & RBAC
* `POST /api/v1/auth/login`: Authenticates username and password; returns JWT bearer token.
  * *Request*: `{ "username": "admin", "password": "..." }`
  * *Response*: `{ "access_token": "...", "token_type": "bearer", "user": { "id": 1, "username": "admin", "role": "admin" } }`
* `GET /api/v1/auth/me` *(Authenticated)*:
  * Validates Bearer token and returns current authenticated user profile.

### User Management
* `GET /api/v1/users` *(Admin Only)*: Lists user accounts with pagination and optional `role` filtering.
* `GET /api/v1/users/{user_id}` *(Admin Only)*: Retrieves user account details.
* `POST /api/v1/users` *(Admin Only)*: Creates a new user with role `student` or `admin`.
* `PATCH /api/v1/users/{user_id}` *(Admin Only)*: Updates user role, active status, or password. Includes safeguards against admin self-deactivation and last-admin demotion.

---

## 9. Authentication & Security Architecture

* **Bcrypt Password Security**: Passwords are hashed with bcrypt (12 rounds of adaptive salting). Passwords and password hashes are never exposed in API schemas or error responses.
* **Timing-Safe Login**: When an invalid username is submitted, a dummy bcrypt hash verification is executed to prevent timing-based username enumeration.
* **Stateless JWT Tokens**: Signed using `HS256` with strict claim verification (`sub`, `exp`, `iat`).
* **Active User Invalidation**: The `get_current_user` dependency checks the database on every request. Deactivated accounts are blocked immediately regardless of token expiry.
* **CORS Restrictions**: Configurable via `CORS_ALLOWED_ORIGINS`. In production, wildcard origins (`*`) are disallowed with credentials.

---

## 10. Machine Learning Integration

The backend loads serialized model artifacts from `ml/models/`:
* `tfidf_vectorizer.joblib`: Pre-fitted TF-IDF vectorizer (2,720 features).
* `best_sentiment_model.joblib`: Production Logistic Regression sentiment classifier.
* `best_category_model.joblib`: Production Logistic Regression category classifier.
* `ml.priority.priority_scoring.PriorityScorer`: Deterministic priority engine.

Artifacts are cached in memory upon pipeline initialization, eliminating repeated disk deserialization latency.

---

## 11. Production Deployment on Render

CampusVoice backend is deployed as a Web Service on **Render**:
* **Public URL**: `https://campusvoice-api-2nkg.onrender.com`
* **Root Directory**: `.`
* **Build Command**: `./render-build.sh`
* **Start Command**: `PYTHONPATH=. uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`

### Render Environment Variables Configuration:
```env
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://<user>:<password>@<neon-host>/<database>?sslmode=require
CORS_ALLOWED_ORIGINS=https://campus-voice-01.vercel.app
JWT_SECRET_KEY=<production-random-secret-min-32-chars>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<secure-admin-password>
```

---

## 12. Running Tests

The backend test suite is executed using `pytest`:

```powershell
cd backend
python -m pytest tests/ -v
```

### Test Coverage Summary:
* Total Tests: **212 passed** (0 failed).
* Key test modules:
  * `tests/test_auth.py`: Authentication, JWT validation, and timing safety.
  * `tests/test_user_management.py`: User CRUD, self-protection, and last-admin safeguards.
  * `tests/test_security_hardening.py`: 33 dedicated security and authorization tests.
  * `tests/test_production_config.py`: 12 production configuration hardening tests.
  * `tests/test_nlp_resources.py`: NLTK resource installation and search path tests.
  * `tests/test_spacy_resources.py`: spaCy model installation and verification tests.
  * `tests/test_analysis_endpoint.py`: End-to-end feedback intelligence endpoint tests.
  * `tests/test_feedback_records.py`: Records table pagination and filtering tests.
  * `tests/test_feedback_persistence.py`: Database transactional persistence tests.

---

## 13. Troubleshooting

* **Missing NLTK or spaCy resources**:
  * Run `python backend/scripts/install_nltk_resources.py` and `python backend/scripts/install_spacy_model.py`.
* **Database connection failed**:
  * Verify PostgreSQL is running on port 5432 and `DATABASE_URL` credentials are correct.
* **CORS blocked**:
  * Verify `CORS_ALLOWED_ORIGINS` includes your frontend origin (`http://localhost:5173` in development, `https://campus-voice-01.vercel.app` in production).
