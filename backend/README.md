# CampusVoice — Backend Service

FastAPI REST backend and PostgreSQL database foundation for the **CampusVoice** AI-Powered Student Feedback Intelligence platform.

---

## 1. Backend Overview
The backend provides the API service, database connectivity, and NLP preprocessing pipeline for ingesting, managing, and standardizing student feedback across campus departments and academic semesters.

* **Framework**: FastAPI (Python 3.10+)
* **Database**: PostgreSQL 18+
* **ORM**: SQLAlchemy 2.x
* **Driver**: psycopg (psycopg3)
* **Migrations**: Alembic
* **Data Validation**: Pydantic v2 & `pydantic-settings`
* **NLP & Text Processing**: NLTK, spaCy (`en_core_web_sm`)
* **Testing**: pytest, HTTPX

---

## 2. Prerequisites
* **Python**: 3.10+ installed (tested on Python 3.13)
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

## 4. NLP Resources & Model Setup

The NLP pipeline requires specific NLTK corpora and the spaCy English language model. These are downloaded via controlled, explicit setup commands rather than network downloads during server startup:

### Step A: Download NLTK Resources (Development)
```powershell
python -m app.nlp.resources --download
```
Downloads:
* `punkt` & `punkt_tab` (tokenization)
* `stopwords` (stopword lists)
* `wordnet` & `omw-1.4` (lexical database)

### Step B: Production Build-Time Resource Installation (Render)
For production environments (such as Render), both NLTK `stopwords` and the spaCy `en_core_web_sm` language model are deterministically installed during the build phase. Runtime resource downloads are intentionally not performed by the application:
```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Install required NLTK resources
python backend/scripts/install_nltk_resources.py

# 3. Install and verify spaCy model
python backend/scripts/install_spacy_model.py
```
Or simply use the repository root build script:
```bash
./render-build.sh
```

**Render Web Service Settings:**
* **Root Directory**: `.`
* **Build Command**: `./render-build.sh` *(or `pip install -r backend/requirements.txt && python backend/scripts/install_nltk_resources.py && python backend/scripts/install_spacy_model.py`)*
* **Start Command**: `PYTHONPATH=. uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`

### Step C: Download spaCy English Model (Local Development)
```powershell
python -m spacy download en_core_web_sm
```

---

## 5. Environment Configuration (`.env`)

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

## 6. Database Migrations (Alembic)

Alembic manages all database schema changes. To apply the initial migration that creates the `feedback` table:

```powershell
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

---

## 7. Running Unit Tests

Execute the automated test suite covering text normalization, tokenization, stopword filtering (with negation preservation), lemmatization, and API endpoints:

```powershell
pytest tests/ -v
```

---

## 8. Running FastAPI Server

Start the development server with auto-reload:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 9. Interactive Documentation (Swagger / OpenAPI)

Once the server is running, visit:
* **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Alternative ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 10. API Endpoints

### Health Check
* `GET /health` or `GET /api/v1/health`
  * Returns service operational status.

### NLP Preprocessing Test Endpoint
* `POST /api/v1/nlp/preprocess`
  * **Request Body**:
    ```json
    {
      "text": "The practical sessions are very useful! The faculty explains concepts clearly, but the lab computers are sometimes slow."
    }
    ```
  * **Response Body**:
    ```json
    {
      "original_text": "The practical sessions are very useful! The faculty explains concepts clearly, but the lab computers are sometimes slow.",
      "normalized_text": "the practical sessions are very useful! the faculty explains concepts clearly, but the lab computers are sometimes slow.",
      "tokens": ["the", "practical", "sessions", "are", "very", "useful", "the", "faculty", "explains", "concepts", "clearly", "but", "the", "lab", "computers", "are", "sometimes", "slow"],
      "filtered_tokens": ["practical", "sessions", "useful", "faculty", "explains", "concepts", "clearly", "lab", "computers", "sometimes", "slow"],
      "lemmatized_tokens": ["practical", "session", "useful", "faculty", "explain", "concept", "clearly", "lab", "computer", "sometimes", "slow"],
      "clean_text": "practical session useful faculty explain concept clearly lab computer sometimes slow"
    }
    ```
  * **Sentiment Negation Preservation**: Negation words (`not`, `no`, `never`, `n't`) are strictly preserved to ensure downstream sentiment analysis models receive accurate contextual polarity:
    * Input: `"The faculty is not helpful."`
    * Clean Text: `"faculty not helpful"` (NOT `"faculty helpful"`).

### Feedback Ingestion & Retrieval
* `POST /api/v1/feedback`: Ingests and stores student feedback in PostgreSQL.
* `GET /api/v1/feedback`: Retrieves stored feedback records ordered by newest first.

### Step 9.1 — Feedback Analysis API
* `POST /api/v1/feedback/analyze`
  * **Purpose**: Expose the existing unified ML feedback intelligence pipeline through FastAPI.
  * **Flow**:
    ```text
    Client
      ↓
    POST /api/v1/feedback/analyze
      ↓
    Pydantic Validation
      ↓
    FeedbackIntelligencePipeline (cached singleton)
      ↓
    NLP + TF-IDF + Sentiment + Category + Priority
      ↓
    JSON Response
    ```
  * **Request Body**:
    ```json
    {
      "feedback": "The faculty is not helpful and the explanations are not clear."
    }
    ```
  * **Response Body**:
    ```json
    {
      "feedback": "The faculty is not helpful and the explanations are not clear.",
      "clean_text": "faculty not helpful explanation not clear",
      "sentiment": {
        "label": -1,
        "name": "negative",
        "confidence": 0.5216,
        "probabilities": {
          "negative": 0.5216,
          "neutral": 0.3629,
          "positive": 0.1155
        }
      },
      "category": {
        "name": "Teaching",
        "confidence": 0.2507,
        "probabilities": {
          "Teaching": 0.2507,
          "Course Content": 0.2476,
          "Library Facilities": 0.1436,
          "Examination": 0.1366,
          "Lab Work": 0.1319,
          "Extracurricular": 0.0895
        }
      },
      "models": {
        "sentiment": "logistic_regression",
        "category": "logistic_regression"
      },
      "priority": {
        "score": 65,
        "level": "Medium",
        "reason": "Negative sentiment detected with moderate confidence."
      }
    }
    ```
  * **Characteristics**:
    * **Reusable Inference**: Delegates directly to the cached `FeedbackIntelligencePipeline` without reloading artifacts.
    * **Deterministic & Explainable**: Priority scores and reasoning are computed deterministically from model confidence scores.
    * **Pydantic v2 Validation**: Rejects non-string, empty, and whitespace-only requests with HTTP 422 while preserving exact raw feedback text.

---

## 11. Step 9.3 — Persist Analyzed Feedback to PostgreSQL

In **Step 9.3**, the backend adds transactional database persistence for feedback intelligence results, storing the machine learning outputs directly alongside the feedback record in PostgreSQL.

### Architecture Overview

* **In-Memory vs. Persisted Endpoints**:
  * `POST /api/v1/feedback/analyze`: Purely in-memory and analysis-only (used for interactive exploration and the real-time React analysis view). Does NOT persist records to the database.
  * `POST /api/v1/feedback/analyze-and-save`: Analyzes student feedback via the unified ML pipeline and immediately commits the intelligence result to PostgreSQL in a single transactional operation.
* **Database Model Extension**:
  * The `Feedback` SQLAlchemy model (`feedback` table) is extended with nullable columns for the primary analysis attributes:
    * `clean_text` (`Text`): Lemmatized, normalized text with negation preservation.
    * `sentiment_label` (`Integer`): `-1` (Negative), `0` (Neutral), `1` (Positive).
    * `sentiment_name` (`String(50)`): `"negative"`, `"neutral"`, `"positive"`.
    * `sentiment_confidence` (`Float`): Calibrated model confidence score.
    * `category_name` (`String(100)`): Predicted feedback topic (e.g., `"Teaching"`, `"Lab Work"`).
    * `category_confidence` (`Float`): Confidence score for the predicted topic.
    * `priority_score` (`Integer`): Bounded $[0, 100]$ priority score.
    * `priority_level` (`String(20)`): Priority tier (`"High"`, `"Medium"`, `"Low"`).
    * `priority_reason` (`Text`): Deterministic administrative reasoning.
  * `department` and `semester` are made `nullable=True` so that feedback submitted without department metadata stores `NULL` without injecting fake or misleading placeholder strings.
* **Service Layer**:
  * `app.services.feedback_service.save_analyzed_feedback`: Encapsulates database mapping and transactional commit/rollback logic, cleanly isolating database operations from ML inference.
* **Migration `002_add_analysis_fields_to_feedback`**:
  * Adds all 9 analysis columns and alters `department` / `semester` to nullable.
  * **Downgrade Safety**: Drops the 9 analysis columns. If reverting `department`/`semester` to `NOT NULL`, it checks for rows with `NULL` values and raises an informative error to prevent data loss or unauthorized placeholder fabrication.

### Example: Analyze & Save Endpoint

* **Endpoint**: `POST /api/v1/feedback/analyze-and-save`
* **Status**: `201 Created`
* **Request**:
  ```json
  {
    "feedback": "The faculty is not helpful and the explanations are not clear."
  }
  ```
* **Response (HTTP 201 Created)**:
  ```json
  {
    "id": 5,
    "department": null,
    "semester": null,
    "feedback_text": "The faculty is not helpful and the explanations are not clear.",
    "clean_text": "faculty not helpful explanation not clear",
    "sentiment_label": -1,
    "sentiment_name": "negative",
    "sentiment_confidence": 0.5216,
    "category_name": "Teaching",
    "category_confidence": 0.2507,
    "priority_score": 65,
    "priority_level": "Medium",
    "priority_reason": "Negative sentiment detected with moderate confidence.",
    "created_at": "2026-09-14T14:37:05.997888+05:30"
  }
  ```

---

## 12. Step 9.5 — Feedback Statistics API (Admin Dashboard Foundation)

In **Step 9.5**, the backend implements a database-backed aggregation API (`GET /api/v1/feedback/stats`) designed to serve as the statistical engine for the future Admin Dashboard.

### Architecture & Design Decisions

* **Direct Database Aggregation**:
  * Employs SQL-level aggregate functions (`func.count()`) and `group_by()` executed directly in PostgreSQL.
  * Avoids memory bloat by **never** loading large feedback text records or embeddings into Python memory.
* **Schema Contract (`FeedbackStatsResponse`)**:
  * `total_feedback` (`int`): Total count of records in the `feedback` table.
  * `analyzed_feedback` (`int`): Count of records where `sentiment_name IS NOT NULL`.
  * `unclassified_feedback` (`int`): Count of records where `sentiment_name IS NULL`.
    * *Invariant*: `total_feedback == analyzed_feedback + unclassified_feedback`.
  * `sentiment` (`SentimentStats`):
    * `positive`, `neutral`, `negative`, `unclassified`
  * `priority` (`PriorityStats`):
    * `high`, `medium`, `low`, `unclassified`
  * `categories` (`Dict[str, int]`):
    * Dynamically discovered dictionary mapping category names to frequency counts.
    * Categories are derived purely from existing database records (zero hardcoded category lists).
    * `NULL` category values are safely excluded from the dictionary.
* **Case Normalization & Robustness**:
  * Sentiment and priority groupings utilize `func.lower()` to prevent casing discrepancies (e.g., `"Negative"` vs `"negative"`).
  * Null handling routes legacy unclassified records cleanly into `.unclassified` fields.
* **Route Ordering**:
  * Registered as `GET /api/v1/feedback/stats` before generic collection routes (`GET /api/v1/feedback`) and any future dynamic path parameters (`GET /api/v1/feedback/{id}`) to eliminate routing collisions.

### Example: Feedback Statistics Endpoint

* **Endpoint**: `GET /api/v1/feedback/stats`
* **Status**: `200 OK`
* **Response (HTTP 200 OK)**:
  ```json
  {
    "total_feedback": 8,
    "analyzed_feedback": 4,
    "unclassified_feedback": 4,
    "sentiment": {
      "positive": 1,
      "neutral": 0,
      "negative": 3,
      "unclassified": 4
    },
    "priority": {
      "high": 0,
      "medium": 3,
      "low": 1,
      "unclassified": 4
    },
    "categories": {
      "Teaching": 3,
      "Library Facilities": 1
    }
  }
  ```

---

## 13. Step 9.8 — Database-Backed Feedback Records API (Admin Dashboard Table Engine)

In **Step 9.8**, the backend implements a database-backed, paginated, and filtered records retrieval endpoint (`GET /api/v1/feedback/records`) to power the future Admin Dashboard feedback-management table.

### Architecture & Capabilities

* **Database-Level Execution**:
  * Filtering, keyword search, counting, ordering, and pagination are executed entirely within PostgreSQL via SQLAlchemy queries.
  * No bulk records or text embeddings are loaded into Python memory for client-side slicing.
* **Pagination**:
  * `page` (integer, default: `1`, minimum: `1`): The 1-indexed page number.
  * `page_size` (integer, default: `10`, minimum: `1`, maximum: `100`): The number of records returned per page.
  * `offset = (page - 1) * page_size` and `limit = page_size`.
  * Out-of-range pages return `items: []` alongside the accurate `total` count and computed `total_pages`.
* **Keyword Search**:
  * `search` (string, optional): Case-insensitive substring matching against `feedback_text` using PostgreSQL-compatible `Feedback.feedback_text.ilike(f"%{search}%")`.
  * Leading and trailing whitespace is trimmed; empty or whitespace-only inputs are ignored.
* **Sentiment Filtering**:
  * `sentiment` (string, optional): Filters by `sentiment_name`.
  * Allowed values (case-insensitive): `positive`, `neutral`, `negative`.
  * Unclassified records with `sentiment_name = NULL` are excluded from sentiment-filtered results.
  * Invalid sentiment values return `HTTP 422 Unprocessable Entity` with a clear validation error.
* **Dynamic Category Filtering**:
  * `category` (string, optional): Dynamic case-insensitive matching against `category_name`.
  * Fully dynamic — does not hardcode ML category names.
  * Non-existent categories return an empty items list (`total: 0`, `items: []`) rather than an error.
* **Priority Tier Filtering**:
  * `priority` (string, optional): Filters by `priority_level`.
  * Allowed values (case-insensitive): `high`, `medium`, `low`.
  * Unclassified records with `priority_level = NULL` are excluded from priority-filtered results.
  * Invalid priority values return `HTTP 422 Unprocessable Entity`.
* **Combined Filters**:
  * Multiple active filters are combined using SQL `WHERE` conjunctions (`AND`), guaranteeing that returned records satisfy all specified criteria simultaneously.
* **Deterministic Ordering**:
  * Default ordering: `created_at DESC` (newest feedback first).
  * Stable secondary ordering: `id DESC` to ensure deterministic ordering when multiple records share identical timestamps.
* **NULL Handling for Legacy Records**:
  * Unclassified legacy records return `null` for uncomputed analysis attributes (`sentiment_name`, `category_name`, `priority_level`, `clean_text`, etc.) without fabricating placeholder data.

### Request & Response Examples

#### Example 1: Default Paginated Query
* **Request**:
  ```http
  GET /api/v1/feedback/records?page=1&page_size=10
  ```
* **Response (HTTP 200 OK)**:
  ```json
  {
    "items": [
      {
        "id": 9,
        "department": null,
        "semester": null,
        "feedback_text": "The chemistry lab equipment is outdated and malfunctioning during experiments.",
        "clean_text": "chemistry lab equipment outdated malfunction experiment",
        "sentiment_label": -1,
        "sentiment_name": "negative",
        "sentiment_confidence": 0.5388,
        "category_name": "Lab Work",
        "category_confidence": 0.6381,
        "priority_score": 70,
        "priority_level": "High",
        "priority_reason": "Negative sentiment detected with moderate confidence.",
        "created_at": "2026-09-14T15:26:50.451178+05:30"
      }
    ],
    "total": 9,
    "page": 1,
    "page_size": 10,
    "total_pages": 1
  }
  ```

#### Example 2: Combined Filter Query
* **Request**:
  ```http
  GET /api/v1/feedback/records?search=faculty&category=Teaching&sentiment=negative&priority=medium&page=1&page_size=5
  ```
* **Response (HTTP 200 OK)**:
  ```json
  {
    "items": [
      {
        "id": 8,
        "department": null,
        "semester": null,
        "feedback_text": "The faculty is not helpful and the explanations are not clear.",
        "clean_text": "faculty not helpful explanation not clear",
        "sentiment_label": -1,
        "sentiment_name": "negative",
        "sentiment_confidence": 0.5216,
        "category_name": "Teaching",
        "category_confidence": 0.2507,
        "priority_score": 65,
        "priority_level": "Medium",
        "priority_reason": "Negative sentiment detected with moderate confidence.",
        "created_at": "2026-09-14T15:14:07.505955+05:30"
      }
    ],
    "total": 3,
    "page": 1,
    "page_size": 5,
    "total_pages": 1
  }
  ```

---

## 14. Backend Project Structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py             # Auth dependencies: get_current_user, require_admin
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── auth.py             # Authentication endpoints: /login, /me
│   │           ├── users.py            # User management endpoints: list, get, create, update
│   │           ├── health.py
│   │           ├── feedback.py         # Stats, records, submit, list, and analyze-and-save endpoints
│   │           ├── analysis.py         # In-memory analysis & priority endpoint
│   │           └── nlp.py              # NLP test endpoint
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                   # App settings, JWT & Admin credentials
│   │   ├── roles.py                    # UserRole enum: admin, student
│   │   └── security.py                 # Bcrypt hashing & PyJWT token management
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── feedback.py                 # Feedback model with analysis fields
│   │   └── user.py                     # User model (id, username, password_hash, role, is_active)
│   ├── nlp/                            # NLP processing module
│   │   ├── __init__.py
│   │   ├── preprocessing.py            # Normalization, tokenization, lemmatization
│   │   └── resources.py                # NLTK & spaCy resource management
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                     # LoginRequest, TokenResponse, CurrentUserResponse
│   │   ├── users.py                    # UserListItem, UserListResponse, UserCreateRequest, UserUpdateRequest, UserDetailResponse
│   │   ├── feedback.py                 # FeedbackCreate, FeedbackResponse, Stats, and Records schemas
│   │   ├── analysis.py                 # Feedback analysis Pydantic schemas
│   │   └── nlp.py                      # Preprocessing request & result schemas
│   ├── services/                       # Service layer
│   │   ├── __init__.py
│   │   ├── feedback_service.py         # Database persistence service
│   │   ├── feedback_stats_service.py   # Database statistics aggregation service
│   │   ├── feedback_records_service.py # Database records retrieval, filtering & pagination service
│   │   └── user_service.py             # User listing, creation, updating, and deactivation service
│   ├── __init__.py
│   └── main.py
├── scripts/
│   └── seed_admin.py                   # Local development admin user provisioning
├── tests/
│   ├── __init__.py
│   ├── test_analysis_endpoint.py       # Analysis API endpoint test suite (18 tests)
│   ├── test_auth.py                    # Auth & RBAC test suite (28 tests)
│   ├── test_user_management.py         # User management API test suite (38 tests)
│   ├── test_feedback_persistence.py    # Feedback persistence test suite (14 tests)
│   ├── test_feedback_records.py        # Feedback records API test suite (32 tests)
│   ├── test_feedback_stats.py          # Feedback statistics test suite (9 tests)
│   └── test_nlp_preprocessing.py       # NLP preprocessing test suite (15 tests)
├── alembic/
│   ├── versions/
│   │   ├── 001_create_feedback_table.py
│   │   ├── 002_add_analysis_fields_to_feedback.py
│   │   └── 003_create_users_table.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── requirements.txt
├── .env.example
├── .env                                (local, gitignored)
└── README.md
```

---

## 15. Authentication & Role-Based Access Control (RBAC) (Step 9.12)

Step 9.12 establishes a secure, backend-enforced authentication system and role-based access control (RBAC) protecting sensitive administrative routes while ensuring uninterrupted student access.

### 15.1 Role Definitions
* **`admin`**: Full administrative access to student feedback statistics (`GET /api/v1/feedback/stats`), filtered and paginated records (`GET /api/v1/feedback/records`), and user profile verification (`GET /api/v1/auth/me`).
* **`student`**: Unauthenticated public feedback submission and intelligence analysis. Can authenticate if provisioned, but has no access to admin dashboard analytics or record lists (receives `HTTP 403 Forbidden`).

### 15.2 Security Architecture
* **Password Hashing**: Salted bcrypt (`bcrypt>=4.1.0`) with work factor 12. Plaintext passwords are never logged, transmitted in error messages, or stored in the database.
* **Token Standard**: Signed HMAC-SHA256 (HS256) JSON Web Tokens (`PyJWT>=2.8.0`) containing subject `sub` (user ID), `username`, `role`, and expiration (`exp`).
* **Protected Routes Dependency**: FastApi `Depends(require_admin)` extracts and validates the Bearer token from the `Authorization: Bearer <token>` header, checks user active status, and verifies that `user.role == UserRole.ADMIN.value`.
* **Zero Disruption to Student Ingestion**: Public student submission routes (`POST /api/v1/feedback`, `POST /api/v1/feedback/analyze-and-save`, `POST /api/v1/feedback/analyze`) remain completely unauthenticated.

### 15.3 Authentication Endpoints

#### POST /api/v1/auth/login
Authenticates credentials and returns a Bearer access token.

* **Request Body**:
  ```json
  {
    "username": "admin",
    "password": "YourSecurePassword123"
  }
  ```
* **Response (HTTP 200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "role": "admin",
    "username": "admin"
  }
  ```

#### GET /api/v1/auth/me
Returns current authenticated user profile without exposing password hashes.

* **Headers**: `Authorization: Bearer <token>`
* **Response (HTTP 200 OK)**:
  ```json
  {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-09-15T11:44:56.894443+05:30"
  }
  ```

### 15.4 Local Admin Seeding Script
To create an initial development administrator account:

```powershell
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="YourDevelopmentPassword123"
python scripts/seed_admin.py
```
The script is fully idempotent: if the user already exists, it prints an informational notice and exits safely without modifying the account.

---

## 16. User Management API (Step 9.14.1)

In **Step 9.14.1**, the backend introduces a dedicated, admin-only REST API (`/api/v1/users`) for managing user accounts, roles, active statuses, and credentials.

### 16.1 Architecture & Security Rules

* **Admin Authorization**: All endpoints enforce `Depends(require_admin)`. Students receive `HTTP 403 Forbidden`, and unauthenticated callers receive `HTTP 401 Unauthorized`.
* **No Physical Deletion**: User accounts are never physically removed via SQL `DELETE`. Deactivation is represented by `is_active = false`, preserving historical audit integrity.
* **Self-Protection**: Administrators cannot deactivate their own account (`HTTP 400 Bad Request`).
* **Last Active Admin Protection**: The system prevents deactivating or demoting the last active administrator (`HTTP 409 Conflict`), safeguarding against irreversible administrative lockout.
* **Stable Usernames**: Usernames cannot be modified after account creation.
* **Response Privacy**: Neither plaintext passwords nor one-way `password_hash` values are ever exposed in any response schema.
* **Database-Level Operations**: User listings, search, filtering, and counting are executed directly in PostgreSQL via SQLAlchemy 2.x expressions without loading the full table into memory.

### 16.2 Endpoints

#### 1. GET /api/v1/users
Retrieves a paginated list of users with optional filtering and search.

* **Query Parameters**:
  * `page` (integer, default: `1`, minimum: `1`): 1-indexed page number.
  * `page_size` (integer, default: `20`, minimum: `1`, maximum: `100`): Items per page.
  * `search` (string, optional): Case-insensitive keyword search on `username`.
  * `role` (string, optional): Filter by `admin` or `student`.
  * `is_active` (boolean, optional): Filter by `true` or `false`.
* **Ordering**: `created_at DESC`, `id DESC`.
* **Response (HTTP 200 OK)**:
  ```json
  {
    "items": [
      {
        "id": 2,
        "username": "student_jane",
        "role": "student",
        "is_active": true,
        "created_at": "2026-09-15T12:59:34.123456+05:30"
      },
      {
        "id": 1,
        "username": "admin",
        "role": "admin",
        "is_active": true,
        "created_at": "2026-09-15T11:44:56.894443+05:30"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 2,
    "total_pages": 1
  }
  ```

#### 2. GET /api/v1/users/{user_id}
Retrieves safe details for an individual user account.

* **Response (HTTP 200 OK)**:
  ```json
  {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-09-15T11:44:56.894443+05:30"
  }
  ```
* **Errors**: `HTTP 404 Not Found` if the user ID does not exist.

#### 3. POST /api/v1/users
Creates a new user account with salted bcrypt password hashing.

* **Request Body**:
  ```json
  {
    "username": "student_john",
    "password": "SecurePassword123!",
    "role": "student"
  }
  ```
* **Validation**:
  * `username`: 1-100 characters, whitespace-trimmed, case-insensitive uniqueness.
  * `password`: Minimum 8 characters, maximum 72 bytes.
  * `role`: `student` (default) or `admin`.
* **Response (HTTP 201 Created)**:
  ```json
  {
    "id": 3,
    "username": "student_john",
    "role": "student",
    "is_active": true,
    "created_at": "2026-09-15T19:30:00.000000+05:30"
  }
  ```
* **Errors**: `HTTP 409 Conflict` if the username already exists; `HTTP 422` if validation fails.

#### 4. PATCH /api/v1/users/{user_id}
Updates user attributes (role, active status, or password).

* **Request Body** (at least one field required):
  ```json
  {
    "role": "admin",
    "is_active": false,
    "password": "NewSecurePassword456!"
  }
  ```
* **Response (HTTP 200 OK)**:
  ```json
  {
    "id": 3,
    "username": "student_john",
    "role": "admin",
    "is_active": false,
    "created_at": "2026-09-15T19:30:00.000000+05:30"
  }
  ```
* **Safeguard Errors**:
  * `HTTP 400 Bad Request`: When an admin attempts to set `is_active: false` on their own ID.
  * `HTTP 409 Conflict`: When attempting to deactivate or demote the last active admin account in the database.

---

## 11. Security Architecture & Hardening (Step 9.17)

Step 9.17 introduced comprehensive security hardening across the CampusVoice authentication, authorization, and network communication layers.

### 1. JWT Authentication & Token Security
- **Algorithm Verification**: Tokens are signed and decoded using `HS256`. Decoding strictly enforces `algorithms=["HS256"]` with required claims `["sub", "iat", "exp"]`. Forged algorithms (`none`, `HS384`, `RS256`) are rejected with HTTP 401.
- **Payload Privacy & Sanitization**: `create_access_token` automatically strips sensitive keys (`password`, `password_hash`, `feedback_text`) from claims, keeping token payloads minimal (`sub`, `username`, `role`).
- **Real-Time Database Verification**: The `get_current_user` dependency resolves the subject (`sub`) against PostgreSQL on every request. If a user is deactivated or demoted in the database, subsequent requests are rejected immediately even if their access token has not yet expired.

### 2. Password Security & Bcrypt Hashing
- **Salted Bcrypt Hashes**: All passwords are encrypted with bcrypt (12 rounds of salting). Passwords and password hashes are strictly excluded from all API response schemas, error messages, debug logs, and token claims.
- **Uniform Length Constraints**: A strict minimum length of 8 characters and a maximum of 72 bytes (bcrypt input limit) are enforced identically across user creation, password updates, admin seeding (`scripts/seed_admin.py`), and low-level cryptographic utilities.
- **Safe Hash Verification**: `verify_password` wraps bcrypt operations in defensive exception boundaries, returning `False` on malformed hashes without crashing or revealing stack traces.

### 3. Login Endpoint Hardening & Timing Protection
- **Neutralizing Username Enumeration**: To prevent timing analysis attacks where response latency could reveal whether a username exists, the login handler runs `verify_password(candidate, DUMMY_BCRYPT_HASH)` when a user is not found.
- **Generic Authentication Responses**: Non-existent users, incorrect passwords, and inactive user accounts return the exact same generic error: `HTTP 401 Unauthorized` with detail `"Invalid username or password."`. Account status or existence is never leaked.

### 4. Authoritative Role-Based Access Control (RBAC)
- **Protected Administrator Endpoints**:
  - `GET /api/v1/feedback/stats`
  - `GET /api/v1/feedback/records`
  - `GET /api/v1/users`
  - `GET /api/v1/users/{user_id}`
  - `POST /api/v1/users`
  - `PATCH /api/v1/users/{user_id}`
- **Enforcement Rules**:
  - Unauthenticated requests: `HTTP 401 Unauthorized`
  - Authenticated student requests: `HTTP 403 Forbidden` (`"Administrative privileges required to access this resource."`)
  - Inactive accounts: `HTTP 401 Unauthorized` (`"User account is inactive."`)
- **Safeguards**: Self-deactivation prevention (`HTTP 400 Bad Request`) and last-active-admin demotion/deactivation protection (`HTTP 409 Conflict`) prevent administrator lockout.
- **Public Student Accessibility**: Feedback submission (`POST /feedback`), analysis (`POST /feedback/analyze`), and persisted analysis (`POST /feedback/analyze-and-save`) remain public without requiring student login.

### 5. Configurable CORS Hardening
- **Environment Modes**: Supported via `ENVIRONMENT=development|production|testing`.
- **Allowed Origins**: Configured via `CORS_ALLOWED_ORIGINS` (comma-separated origins).
- **Development Defaults**: In development, `localhost:5173` and `127.0.0.1:5173` are allowed alongside `FRONTEND_URL`.
- **Production Restrictions**: In production, explicit origins are required; wildcard `*` origins are strictly stripped when credentials are enabled (`allow_credentials=True`).
- **Restricted Methods & Headers**: Only necessary HTTP methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`) and headers (`Content-Type`, `Authorization`, `Accept`, `X-Requested-With`) are permitted.

### 6. Automated Security Regression Suite
Tested with 33 dedicated security unit & integration tests (`tests/test_security_hardening.py`):
- All 187 backend tests passing (`.\venv\Scripts\python -m pytest tests/ -v`).
