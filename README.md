# CampusVoice: AI-Powered Student Feedback Intelligence System

CampusVoice is an AI-powered end-to-end feedback intelligence platform designed to analyze, categorize, and extract actionable insights from student feedback in academic institutions. Combining Modern React, FastAPI, traditional NLP (NLTK, spaCy), Machine Learning (scikit-learn), Word Embeddings (Gensim), and Deep Learning (TensorFlow/Keras), CampusVoice transforms unstructured student sentiments into structured institutional intelligence.

---

## Current Development Status
**Milestone:** `Step 1 — Project Initialization`
- Project directory structure established.
- Modern React frontend scaffolded with initial placeholder.
- Modular FastAPI backend initialized with `GET /health` endpoint.
- Machine Learning (ML) and Database pipeline directories organized.
- Version control configurations prepared.

---

## Planned Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React, Vite, Modern CSS |
| **Backend** | Python, FastAPI, Uvicorn, Pydantic |
| **Database & ORM** | PostgreSQL, SQLAlchemy |
| **NLP & Text Processing** | NLTK, spaCy |
| **Machine Learning** | scikit-learn |
| **Word Embeddings** | Gensim (Word2Vec / FastText) |
| **Deep Learning** | TensorFlow / Keras (LSTM / Neural Networks) |
| **API Architecture** | RESTful JSON API |

---

## Repository Structure

```
CampusVoice/
├── frontend/                 # React frontend application
│   ├── src/                  # React components and styling
│   ├── package.json          # Node dependencies and scripts
│   └── vite.config.js        # Vite configuration
├── backend/                  # FastAPI backend application
│   ├── app/                  # Application core, API routes, schemas
│   │   ├── api/              # API endpoints (versioned)
│   │   ├── core/             # Application configuration
│   │   └── main.py           # FastAPI application entrypoint
│   ├── requirements.txt      # Python dependencies
│   └── README.md             # Backend setup guide
├── ml/                       # Machine Learning and NLP pipeline
│   ├── datasets/             # Raw and processed datasets
│   ├── notebooks/            # Exploratory Data Analysis & experiments
│   ├── preprocessing/       # Text cleaning, tokenization, lemmatization
│   ├── training/             # Model training pipelines
│   ├── evaluation/           # Model validation & performance metrics
│   └── models/               # Serialized model artifacts & weights
├── database/                 # Database migrations and SQL schemas
├── .gitignore                # Global ignore rules for Node, Python, ML
└── README.md                 # Project documentation
```

---

## Quick Start Guide

### 1. Frontend Setup
Navigate to the `frontend/` directory, install dependencies, and launch the Vite development server:
```bash
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:5173` to view the application.

### 2. Backend Setup
Navigate to the `backend/` directory, create and activate a Python virtual environment, install dependencies, and start the FastAPI server:

**On Windows (PowerShell):**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**On macOS / Linux:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be running at `http://127.0.0.1:8000`.

### 3. Testing Health Endpoint
Verify the backend service status:
- Browser or curl: `http://127.0.0.1:8000/health`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
