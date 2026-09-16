# CampusVoice
## AI-Powered Student Feedback Intelligence System

CampusVoice is a production-ready, full-stack Natural Language Processing (NLP) and Machine Learning (ML) platform designed to collect, analyze, categorize, and prioritize student feedback in academic institutions. Combining a modern React frontend, high-performance FastAPI backend, traditional NLP (spaCy, NLTK), scikit-learn classification models, explainable priority scoring, and PostgreSQL persistence, CampusVoice transforms unstructured, noisy student commentary into structured, actionable institutional intelligence.

---

## End-to-End Intelligence Pipeline

```text
       Student Feedback (Natural Language)
                       ↓
               NLP Preprocessing
      (Normalize • Lemmatize • Negation)
                       ↓
           TF-IDF Feature Extraction
        (2,720 N-gram Features: 1–2)
                       ↓
        ┌──────────────┴──────────────┐
        ↓                             ↓
 Sentiment Classification     Category Classification
  (Logistic Regression)        (Logistic Regression)
        ↓                             ↓
  Negative / Neutral /        Teaching • Course Content •
        Positive              Exam • Lab • Library • Extra
        └──────────────┬──────────────┘
                       ↓
            Explainable Priority Scoring
             (Deterministic Rule Engine)
                       ↓
             PostgreSQL Persistence
          (Feedback & User Entities)
                       ↓
             Administrative Portal
       (Dashboard • Charts • Records • RBAC)
```

---

## Key Features

* **Natural-Language Feedback Submission**: Public student portal supporting open-ended feedback submission with client-side validation and quick-fill samples.
* **Rigorous NLP Preprocessing**:
  * Unicode normalization, case folding, and whitespace collapsing.
  * Linguistic tokenization and lemmatization via spaCy (`en_core_web_sm`).
  * Sentiment-critical **negation preservation** (`not`, `no`, `never`, `n't`, `without`).
  * Non-destructive stopword filtering via NLTK (`stopwords`).
* **TF-IDF Feature Extraction**: Sublinear-scaled bi-gram vocabulary ($1 \le n \le 2$) fitted strictly on training data to prevent data leakage.
* **Dual Machine Learning Classification**:
  * **Sentiment Classifier**: Logistic Regression with balanced class weights classifying feedback into Positive, Neutral, or Negative.
  * **Category Classifier**: Multi-class Logistic Regression categorizing feedback into one of six academic domains (*Teaching*, *Course Content*, *Examination*, *Lab Work*, *Library Facilities*, *Extracurricular*).
* **Explainable Priority Scoring**: Deterministic, transparent rule-based algorithm mapping sentiment confidence and category signals into a standardized 0–100 score and tier (`High` $\ge 70$, `Medium` $\ge 40$, `Low` $< 40$).
* **PostgreSQL Persistence**: Robust relational persistence of feedback records, intelligence predictions, and administrative users with SQLAlchemy 2.x and Alembic migrations.
* **Real-Time Feedback Statistics**: Instant aggregation of submission volume, sentiment ratios, priority distributions, and department breakdowns.
* **Searchable & Filterable Records Table**: Dynamic filtering by sentiment, category, priority, and case-insensitive keyword search with server-side pagination.
* **Feedback Detail View**: Modal view providing complete insight into raw comments, cleaned tokens, probability distributions, and priority rationale.
* **Data Export**: Immediate client-side export of filtered or full records to CSV and Excel (`.xlsx`) formats.
* **Role-Based Access Control (RBAC)**:
  * Strict JWT Bearer authentication (`HS256`, bcrypt salted hashing).
  * Separate `student` and `admin` roles.
  * Protected administrative endpoints and dashboard views.
  * Safeguards against admin self-deactivation and last-admin lockout.
* **Frontend Performance & Optimization**:
  * Code-splitting and lazy-loading (`React.lazy`, `Suspense`).
  * Resilient error boundary protection (`ErrorBoundary`).
  * Centralized 401 session expiration handling with alert throttling.
* **Production Deployment Architecture**:
  * Frontend deployed on **Vercel**.
  * Backend deployed on **Render** with deterministic build-time resource installation.
  * Database hosted on **Neon PostgreSQL**.

---

## Technology Stack

| Domain | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | React 18 | Modern component architecture |
| | Vite 5 | High-speed frontend build tooling |
| | JavaScript (ES6+) | Core client programming language |
| | Recharts 3 | Responsive interactive SVG data visualizations |
| | Vanilla CSS | Custom, responsive UI styling without utility bloat |
| | XLSX (SheetJS) | Client-side spreadsheet export generation |
| **Backend** | Python 3.10+ | Primary server language (tested on Python 3.13) |
| | FastAPI | Asynchronous high-performance REST framework |
| | Pydantic v2 | Strict request/response schema validation |
| | `pydantic-settings` | Type-safe environment configuration management |
| | SQLAlchemy 2.x | Modern Python ORM and query builder |
| | psycopg3 (`psycopg[binary]`) | Fast PostgreSQL database driver |
| | Alembic | Version-controlled relational database schema migrations |
| **NLP** | NLTK 3.8+ | Lexical resources and stopword management |
| | spaCy 3.7+ | Industrial-strength tokenization and lemmatization |
| | `en_core_web_sm` | spaCy English small language model package |
| **Machine Learning** | scikit-learn 1.4+ | Vectorization, classification algorithms, and evaluation |
| | TF-IDF | Sublinear frequency-scaled n-gram feature extraction |
| | Logistic Regression | Regularized linear classification for sentiment and category |
| | Multinomial Naive Bayes | Probabilistic text baseline |
| | joblib | High-efficiency model serialization and persistence |
| **Authentication** | PyJWT | RFC 7519 JSON Web Token encoding and strict decoding |
| | bcrypt | Password hashing with adaptive salting (12 rounds) |
| **Database** | PostgreSQL 18+ | Local relational persistence engine |
| | Neon PostgreSQL | Cloud serverless PostgreSQL in production |
| **Deployment** | Vercel | Global CDN frontend hosting platform |
| | Render | Managed cloud application container for FastAPI |
| **Testing** | pytest | Backend unit, integration, and ML testing |
| | Vitest | Fast Vite-native unit and component test runner |
| | React Testing Library | Accessible, user-centric DOM component testing |

---

## System Architecture

```text
+-----------------------------------------------------------------------+
|                            CLIENT BROWSER                             |
|                                                                       |
|   +--------------------------+          +-------------------------+   |
|   |   Student Feedback UI    |          |     Admin Portal        |   |
|   | (Submission & Real-time  |          | (Analytics, Records,    |   |
|   |   Analysis Confirmation) |          |  Detail, Export, Users) |   |
|   +-------------+------------+          +------------+------------+   |
+-----------------|------------------------------------|----------------+
                  |                                    |
                  | HTTPS REST Requests                | Bearer JWT HTTPS
                  v                                    v
+-----------------------------------------------------------------------+
|                    FASTAPI BACKEND SERVICE (RENDER)                   |
|                                                                       |
|   +---------------------------------------------------------------+   |
|   |                        API Routers                            |   |
|   |   /health   •   /api/v1/feedback   •   /api/v1/auth   •   /users  |   |
|   +-------------------------------+-------------------------------+   |
|                                   |                                   |
|   +-------------------------------v-------------------------------+   |
|   |                 FeedbackIntelligencePipeline                  |   |
|   |                                                               |   |
|   |  [1] NLP Preprocessing (spaCy lemmatization + NLTK negations) |   |
|   |  [2] TF-IDF Feature Extraction (Fitted 2,720 features)        |   |
|   |  [3] Sentiment Classifier (Logistic Regression - Balanced)    |   |
|   |  [4] Category Classifier (Logistic Regression)                |   |
|   |  [5] PriorityScorer (Deterministic Rule Engine)               |   |
|   +-------------------------------+-------------------------------+   |
|                                   |                                   |
|   +-------------------------------v-------------------------------+   |
|   |                 SQLAlchemy 2.x Session & ORM                  |   |
|   +-------------------------------+-------------------------------+   |
+-----------------------------------|-----------------------------------+
                                    |
                                    | psycopg3 Connection Pool (TLS)
                                    v
+-----------------------------------------------------------------------+
|                      POSTGRESQL DATABASE (NEON)                       |
|                                                                       |
|   +-------------------------------+   +---------------------------+   |
|   |        feedback table         |   |        users table        |   |
|   |  (text, clean_text, sentiment,|   |  (username, password_hash,|   |
|   |   category, priority, dates)  |   |   role, is_active, dates) |   |
|   +-------------------------------+   +---------------------------+   |
+-----------------------------------------------------------------------+
```

---

## NLP Preprocessing Pipeline

Every feedback comment processed by CampusVoice passes through an 8-stage preprocessing pipeline implemented in [`backend/app/nlp/preprocessing.py`](file:///d:/Projects%20Of%20JISHAN/CampusVoice/backend/app/nlp/preprocessing.py):

1. **Input Validation**: Rejects empty strings, whitespace-only inputs, and non-string types with explicit HTTP 422 errors.
2. **Unicode Normalization**: Applies NFKD Unicode decomposition and strips unprintable control characters.
3. **Case Folding**: Standardizes text to lowercase.
4. **Whitespace Normalization**: Collapses repeated spaces, tabs, and newlines into single spaces.
5. **Tokenization**: Uses spaCy (`en_core_web_sm`) to produce linguistic tokens while discarding standalone punctuation.
6. **Sentiment Negation Preservation**: Critical sentiment words (`not`, `no`, `never`, `n't`, `neither`, `nor`, `none`, `cannot`, `without`, `hardly`, `barely`, `scarcely`) are exempt from stopword removal. Contractions like `"n't"` are standardized to `"not"`.
7. **Stopword Filtering**: Strips common English stopwords using NLTK's corpus (excluding preserved negations).
8. **Lemmatization**: Uses spaCy's lemmatizer to reduce inflected words to their dictionary root form (e.g., `"sessions"` $\rightarrow$ `"session"`, `"explains"` $\rightarrow$ `"explain"`).

### Deterministic Build-Time Installation (No Runtime Downloads)
In production (Render), NLTK `stopwords` and spaCy `en_core_web_sm` are installed during the build phase via [`render-build.sh`](file:///d:/Projects%20Of%20JISHAN/CampusVoice/render-build.sh). The application strictly avoids downloading resources during startup or request handling, guaranteeing offline stability and fast startup times.

---

## Machine Learning Pipeline

### Dataset & Transformation
The model pipeline was trained on an institutional feedback dataset (`ml/datasets/finalDataset0.2.xlsx`). The original wide survey format (185 responses across 6 category columns) was transformed into 723 validated, independent long-format feedback records, categorized across:
* **Teaching**
* **Course Content**
* **Examination**
* **Lab Work**
* **Library Facilities**
* **Extracurricular**

### Train / Test Partitioning
* **80% Training Set**: 578 samples (`ml/datasets/train_feedback.csv`).
* **20% Held-Out Test Set**: 145 samples (`ml/datasets/test_feedback.csv`).
* **Stratification**: Partitioned with fixed `random_state=42` stratified on sentiment labels.

### Feature Engineering
* **Vectorizer**: `sklearn.feature_extraction.text.TfidfVectorizer` (2,720 features).
* **Configuration**: `ngram_range=(1, 2)`, `min_df=1`, `max_df=0.95`, `sublinear_tf=True`.
* **Strict Anti-Leakage Rule**: The vectorizer was fit exclusively on the training split. The held-out test set was transformed strictly using the training vocabulary.

### Model Selection & Performance (Held-Out Test Set)

#### Sentiment Classification
Evaluated on 145 test samples across classes `-1` (Negative), `0` (Neutral), and `1` (Positive):

| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 | Selection |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression (Balanced)** | **72.41%** | **0.6201** | **0.6238** | **0.6217** | **Selected Best** |
| Multinomial Naive Bayes | 65.52% | 0.8158 | 0.3933 | 0.3666 | Baseline |

*Reason for Selection*: Multinomial Naive Bayes suffered from majority-class collapse towards positive comments (39.3% recall). Logistic Regression with balanced class weights correctly identified negative and neutral comments, achieving a superior Macro F1 of **0.6217**.

#### Category Classification
Evaluated on 145 test samples across the 6 academic categories:

| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 | Selection |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | **66.21%** | **0.6801** | **0.6620** | **0.6628** | **Selected Best** |
| Multinomial Naive Bayes | 63.45% | 0.6715 | 0.6343 | 0.6364 | Baseline |

*Reason for Selection*: Logistic Regression achieved superior Macro F1 (**0.6628**, +4.1% over Naive Bayes) with balanced precision and recall across all six categories.

---

## Explainable Priority Scoring

Priority calculation is performed by a **deterministic, rule-based scoring engine** ([`ml/priority/priority_scoring.py`](file:///d:/Projects%20Of%20JISHAN/CampusVoice/ml/priority/priority_scoring.py)). It is intentionally rule-based (not another black-box ML model) to ensure institutional accountability and complete transparency:

1. **Base Score (Sentiment Signal)**:
   * **Negative Sentiment**:
     * Confidence $\ge 0.70 \implies \text{Base Score} = 80$
     * Confidence $\ge 0.50 \implies \text{Base Score} = 65$
     * Confidence $< 0.50 \implies \text{Base Score} = 50$
   * **Neutral Sentiment**:
     * Confidence $\ge 0.70 \implies \text{Base Score} = 30$
     * Confidence $\ge 0.50 \implies \text{Base Score} = 25$
     * Confidence $< 0.50 \implies \text{Base Score} = 20$
   * **Positive Sentiment**:
     * Confidence $\ge 0.70 \implies \text{Base Score} = 10$
     * Confidence $\ge 0.50 \implies \text{Base Score} = 5$
     * Confidence $< 0.50 \implies \text{Base Score} = 0$

2. **Category Confidence Adjustment**:
   * Category Confidence $\ge 0.70 \implies +10$ points
   * Category Confidence $\ge 0.50 \implies +5$ points
   * Category Confidence $< 0.50 \implies +0$ points

3. **Clamping & Tier Mapping**:
   $$\text{Final Score} = \max(0, \min(100, \text{Base Score} + \text{Category Adjustment}))$$

| Priority Tier | Score Range | Administrative Meaning |
| :---: | :---: | :--- |
| **High** | $70 - 100$ | Critical feedback requiring urgent administrative review |
| **Medium** | $40 - 69$ | Moderate-priority feedback for standard departmental evaluation |
| **Low** | $0 - 39$ | Routine feedback or positive remarks with standard processing |

---

## Authentication & Security

* **Cryptographic Password Hashing**: Passwords stored as salted bcrypt hashes (12 rounds). Passwords and hashes are strictly excluded from API outputs, logs, and token payloads.
* **JWT Access Tokens**: Stateless bearer tokens signed with `HS256`, containing only safe identity claims (`sub`, `username`, `role`). Strict token expiry (`exp`) is enforced.
* **Role-Based Authorization (RBAC)**:
  * Public access: Student feedback submission and analysis endpoints.
  * Administrator-only access: Analytics statistics, records table, detail inspect, and user management.
* **Timing-Attack Protection**: Login verifies candidate passwords against a dummy bcrypt hash when a username does not exist, eliminating timing-based username enumeration.
* **Administrative Account Safeguards**:
  * Self-deactivation prevention: Admins cannot deactivate their own active accounts.
  * Last-admin protection: Prevents deleting, deactivating, or demoting the final active administrator.
* **Session Lifecycle Protection**: Centralized 401 response interceptor with a 400ms broadcast cooldown to prevent notification flooding upon session expiration.
* **CORS Hardening**: Strict origin whitelisting in production; wildcards (`*`) are disallowed when credentials are enabled.

---

## API Documentation

All versioned endpoints are prefixed with `/api/v1`. Interactive Swagger documentation is available at `/docs`.

### Health Endpoints
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Public | Root health check |
| `GET` | `/api/v1/health` | Public | Versioned health check |

### Feedback Endpoints
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/feedback` | Public | Submits student feedback into PostgreSQL |
| `GET` | `/api/v1/feedback` | Public | Retrieves recent feedback records |
| `POST` | `/api/v1/feedback/analyze` | Public | Executes ML intelligence pipeline without database persistence |
| `POST` | `/api/v1/feedback/analyze-and-save` | Public | Analyzes feedback and persists record + predictions in one atomic transaction |
| `GET` | `/api/v1/feedback/stats` | **Admin Only** | Aggregates dynamic feedback metrics for dashboard |
| `GET` | `/api/v1/feedback/records` | **Admin Only** | Retrieves paginated, filtered, and searchable feedback records |

### NLP Endpoints
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/nlp/preprocess` | Public | Low-level test endpoint for raw tokenization and lemmatization |

### Authentication Endpoints
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Public | Authenticates credentials and issues JWT access token |
| `GET` | `/api/v1/auth/me` | **Authenticated** | Returns current user profile and role |

### User Management Endpoints
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/users` | **Admin Only** | Lists registered users with pagination and role filter |
| `GET` | `/api/v1/users/{user_id}` | **Admin Only** | Retrieves user details by ID |
| `POST` | `/api/v1/users` | **Admin Only** | Creates a new user account |
| `PATCH` | `/api/v1/users/{user_id}` | **Admin Only** | Updates user role, active status, or password |

---

## Database Architecture & Migrations

CampusVoice utilizes PostgreSQL with SQLAlchemy 2.x and Alembic.

### Migration History
1. `001_create_feedback` ([`001_create_feedback_table.py`](file:///d:/Projects%20Of%20JISHAN/CampusVoice/backend/alembic/versions/001_create_feedback_table.py)): Creates initial `feedback` table with `id`, `department`, `semester`, `feedback_text`, and timestamps.
2. `002_add_analysis_fields` ([`002_add_analysis_fields_to_feedback.py`](file:///d:/Projects%20Of%20JISHAN/CampusVoice/backend/alembic/versions/002_add_analysis_fields_to_feedback.py)): Adds ML analysis columns (`clean_text`, `sentiment_label`, `sentiment_score`, `sentiment_confidence`, `category_label`, `category_confidence`, `priority_score`, `priority_level`, `priority_reason`) and makes departmental fields optional for direct text submissions.
3. `003_create_users` ([`003_create_users_table.py`](file:///d:/Projects%20Of%20JISHAN/CampusVoice/backend/alembic/versions/003_create_users_table.py)): Creates the `users` table for JWT authentication and RBAC (`id`, `username`, `password_hash`, `role`, `is_active`, timestamps).

### Migration Commands
```bash
cd backend
alembic upgrade head
alembic current
alembic history
```

---

## Frontend Architecture

The frontend is built with React 18 and Vite, organized around clean modular services and component encapsulation:

* **Student Feedback Portal (`App.jsx`)**: Responsive submission interface with instant feedback intelligence cards and saved persistence status.
* **Admin Dashboard (`AdminDashboard.jsx`)**: Analytical summary cards displaying total feedback, sentiment split, category frequencies, and priority levels.
* **Visual Analytics (`DashboardCharts.jsx`)**: Interactive Recharts components (Sentiment Distribution Donut, Priority Breakdown Bar Chart, Category Frequency Chart).
* **Feedback Records Table (`FeedbackRecords.jsx`)**: Searchable, multi-attribute filterable, paginated record management table.
* **Record Detail Modal (`FeedbackRecordDetail.jsx`)**: Full modal dialog displaying raw comments, cleaned tokens, probability distributions, and priority justification.
* **Data Export Utility (`exportFeedback.js`)**: Pure client-side CSV and Excel (`.xlsx`) export generation.
* **User Management (`UserManagement.jsx`)**: Administrative user creation, editing, role promotion, and activation toggling.
* **Code Splitting & Lazy Loading**: Heavy components (`FeedbackRecords`, `FeedbackRecordDetail`, `DashboardCharts`, `UserManagement`) are loaded asynchronously via `React.lazy` to keep the initial bundle lightweight (168 kB).

---

## Testing & Quality Assurance

CampusVoice includes comprehensive automated test coverage across all layers:

### 1. Backend Test Suite (212 Tests)
Covers authentication, RBAC, input validation, endpoints, database persistence, security hardening, and resource loading:
```bash
cd backend
python -m pytest tests/ -v
```

### 2. Machine Learning Test Suite (96 Tests)
Covers dataset preparation, TF-IDF vectorizer integrity, sentiment classification, category classification, pipeline integration, and deterministic priority scoring:
```bash
python -m pytest ml/tests/ -v
```

### 3. Frontend Test Suite (108 Tests across 16 Files)
Covers component rendering, form validation, authentication context, session expiration, export utilities, and error boundaries:
```bash
cd frontend
npm test
npm run test:run
npm run test:coverage
```

### 4. Frontend Production Build Validation
```bash
cd frontend
npm run build
```

---

## Production Deployment

CampusVoice is deployed across specialized cloud platforms:

* **Frontend**: Hosted on **Vercel**
  * **Production URL**: `https://campus-voice-01.vercel.app`
* **Backend**: Hosted on **Render** (Native Python Web Service)
  * **Production URL**: `https://campusvoice-api-2nkg.onrender.com`
* **Database**: Hosted on **Neon PostgreSQL** (Serverless PostgreSQL)

### Deployment Architecture & Data Flow

```text
Browser Client ──> Vercel (React Frontend)
                         │
                         │ HTTPS API (VITE_API_BASE_URL)
                         v
                   Render (FastAPI Backend)
                         │
                         │ TLS Database Connection (DATABASE_URL)
                         v
                   Neon (PostgreSQL Serverless)
```

### Render Build Configuration
Render executes [`render-build.sh`](file:///d:/Projects%20Of%20JISHAN/CampusVoice/render-build.sh) from the repository root:
* **Root Directory**: `.`
* **Build Command**: `./render-build.sh`
  ```bash
  pip install -r backend/requirements.txt
  python backend/scripts/install_nltk_resources.py
  python backend/scripts/install_spacy_model.py
  ```
* **Start Command**:
  ```bash
  PYTHONPATH=. uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT
  ```

---

## Environment Variables

> [!IMPORTANT]
> Never commit `.env` files to version control. Set environment variables securely in your hosting provider's dashboard (Render, Vercel).

### Frontend Environment Variables (`frontend/.env.example`)
| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Base URL of the FastAPI backend service | `http://127.0.0.1:8000` (Local) / `https://campusvoice-api-2nkg.onrender.com` (Prod) |

### Backend Environment Variables (`backend/.env.example`)
| Variable | Description | Safe Example Format |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Deployment environment mode (`development`, `production`, `testing`) | `development` |
| `DATABASE_URL` | PostgreSQL connection URL with psycopg driver | `postgresql+psycopg://<user>:<password>@<host>:5432/<dbname>` |
| `FRONTEND_URL` | Allowed origin for frontend requests | `http://localhost:5173` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins | `https://campus-voice-01.vercel.app` |
| `JWT_SECRET_KEY` | Cryptographic secret for signing JWTs ($\ge 32$ characters) | `<your-cryptographically-secure-random-secret>` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes | `60` |
| `ADMIN_USERNAME` | Username for administrator seed account | `admin` |
| `ADMIN_PASSWORD` | Password for administrator seed account | `<secure-admin-password>` |

---

## Repository Directory Structure

```text
CampusVoice/
├── .gitignore                      # Git exclusion rules for Python, Node, ML artifacts
├── README.md                       # Master project documentation
├── render-build.sh                 # Production build script for Render deployment
├── backend/                        # FastAPI REST service & database layer
│   ├── .env.example                # Backend environment variable template
│   ├── README.md                   # Detailed backend documentation
│   ├── alembic.ini                 # Alembic configuration
│   ├── requirements.txt            # Python production dependencies
│   ├── alembic/                    # Database migrations
│   │   └── versions/               # Revisions 001, 002, 003
│   ├── app/                        # Application source code
│   │   ├── api/                    # Versioned REST routers & dependencies
│   │   ├── core/                   # Settings, security, database session
│   │   ├── db/                     # Base model declarations
│   │   ├── models/                 # SQLAlchemy models (Feedback, User)
│   │   ├── nlp/                    # Preprocessing & resource loaders
│   │   ├── schemas/                # Pydantic schemas
│   │   ├── services/               # Records, stats, and feedback logic
│   │   └── main.py                 # FastAPI application entrypoint
│   ├── scripts/                    # Deployment & seed utilities
│   │   ├── install_nltk_resources.py # Build-time NLTK resource installer
│   │   ├── install_spacy_model.py    # Build-time spaCy model installer
│   │   └── seed_admin.py             # Admin user seed script
│   └── tests/                      # Backend automated test suite (212 tests)
├── frontend/                       # React 18 + Vite client application
│   ├── .env.example                # Frontend environment variable template
│   ├── README.md                   # Detailed frontend documentation
│   ├── package.json                # Frontend dependencies and npm scripts
│   ├── vite.config.js              # Vite build and test configuration
│   └── src/                        # React source code
│       ├── components/             # UI components, modals, charts, error boundary
│       ├── context/                # AuthContext & session management
│       ├── services/               # API client and service functions
│       └── utils/                  # Token storage, formatters, export utilities
├── database/                       # Database documentation and architectural specifications
│   └── README.md                   # Relational database & migration documentation
└── ml/                             # Machine Learning and NLP intelligence pipeline
    ├── README.md                   # ML architecture, benchmarks, and priority engine docs
    ├── datasets/                   # Survey datasets & long-format splits
    ├── evaluation/                 # Metrics, comparisons, confusion matrices
    ├── models/                     # Production model binaries & inference modules
    ├── notebooks/                  # Experimental notebooks documentation
    ├── pipeline/                   # Unified FeedbackIntelligencePipeline
    ├── preprocessing/              # Transformation & TF-IDF extraction
    ├── priority/                   # Deterministic PriorityScorer engine
    ├── training/                   # Model training pipelines
    └── tests/                      # ML automated test suite (96 tests)
```

---

## Project Status

CampusVoice is fully implemented, thoroughly tested across 416 total automated tests (212 backend + 96 ML + 108 frontend), and successfully deployed in production across Vercel, Render, and Neon PostgreSQL.
