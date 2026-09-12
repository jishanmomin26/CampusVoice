# CampusVoice — Backend Service

FastAPI backend service powering the **CampusVoice** AI Feedback Intelligence platform.

---

## Requirements
* Python 3.10+ (tested on Python 3.13)
* `pip` package manager

---

## Setup & Execution Guide

### 1. Create Virtual Environment
From the `backend/` directory:

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Development Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Verify Endpoints
* **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
* **Interactive API Documentation (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Alternative API Documentation (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## API Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           └── health.py    # Health check endpoint
│   ├── core/
│   │   └── config.py            # Pydantic Settings
│   └── main.py                  # App initialization & middleware
├── requirements.txt             # Project dependencies
└── README.md
```
