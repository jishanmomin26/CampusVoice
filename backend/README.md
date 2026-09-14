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

### Step A: Download NLTK Resources
```powershell
python -m app.nlp.resources --download
```
Downloads:
* `punkt` & `punkt_tab` (tokenization)
* `stopwords` (stopword lists)
* `wordnet` & `omw-1.4` (lexical database)

### Step B: Download spaCy English Model
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

## 11. Backend Project Structure

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
│   │           ├── feedback.py
│   │           ├── analysis.py     # Feedback analysis & priority endpoint
│   │           └── nlp.py          # NLP test endpoint
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
│   ├── nlp/                        # NLP processing module
│   │   ├── __init__.py
│   │   ├── preprocessing.py        # Normalization, tokenization, lemmatization
│   │   └── resources.py            # NLTK & spaCy resource management
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── feedback.py
│   │   ├── analysis.py             # Feedback analysis Pydantic schemas
│   │   └── nlp.py                  # Preprocessing request & result schemas
│   ├── __init__.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   ├── test_analysis_endpoint.py   # Analysis API endpoint test suite
│   └── test_nlp_preprocessing.py   # NLP preprocessing test suite
├── alembic/
│   ├── versions/
│   │   └── 001_create_feedback_table.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── requirements.txt
├── .env.example
├── .env                            (local, gitignored)
└── README.md
```
