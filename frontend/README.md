# CampusVoice — Frontend Service

React + Vite frontend for the **CampusVoice** Student Feedback Intelligence platform.

---

## 1. Overview
The frontend provides an interactive, responsive web interface for students to submit institutional feedback and receive immediate, transparent feedback intelligence powered by the FastAPI backend and unified NLP/ML pipeline.

---

## 2. Step 9.2 — React Feedback Analysis Integration

### Architecture & Information Flow

```text
       Student
          ↓
  React Feedback Form
  (App.jsx — client validation)
          ↓
    analysisApi.js
  (Service Layer)
          ↓
  POST /api/v1/feedback/analyze
          ↓
       FastAPI
  (Backend Endpoint)
          ↓
FeedbackIntelligencePipeline
  (NLP + TF-IDF + Sentiment + Category + Priority)
          ↓
     JSON Result
          ↓
  React Analysis Result Display
  (Priority, Sentiment, Category, Cleaned Text)
```

### Component Structure
- **Feedback Form (`App.jsx`)**:
  - Semantic `<label htmlFor="feedback-input">` and `<textarea>` with character counter.
  - Client-side validation preventing submission of empty or whitespace-only inputs.
  - Quick-fill sample buttons (`Needs Attention Sample`, `Positive Sample`, `Clear`).
  - Loading spinner indicator disabling the Analyze button during API calls to prevent duplicate submissions.
  - User feedback text preserved in the input area across loading and error states.
- **Analysis Result Display (`App.jsx`)**:
  - **Priority Assessment**: Displays score (/100), visual meter, level (`HIGH`, `MEDIUM`, `LOW`) using accessible badge markers and text labels (not color alone), and deterministic administrative reasoning.
  - **Sentiment Analysis**: Displays polarity (`NEGATIVE`, `NEUTRAL`, `POSITIVE`), model confidence percentage, and probability distribution across classes.
  - **Category Classification**: Displays primary category name, model confidence score, and top category probabilities breakdown.
  - **NLP Preprocessing Card**: Displays cleaned normalized text (`clean_text`), showing how sentiment-critical negation terms (`not`, `no`, `never`) are preserved.
- **API Service Layer (`src/services/analysisApi.js`)**:
  - Decoupled service function `analyzeFeedback(feedbackText)`.
  - Configurable backend target via `VITE_API_BASE_URL` (defaults to `http://127.0.0.1:8000`).
  - Safe error handling translating HTTP 422, 503, 500, and network failures into user-friendly messages without exposing internal stack traces.

---

## 3. Configuration & Environment Variables

Copy `.env.example` to `.env` to override configuration:

```env
# FastAPI Backend URL
VITE_API_BASE_URL=http://127.0.0.1:8000
```

> **Note**: Do not commit secrets or local credentials to Git.

---

## 4. Development & Build Commands

### Start Vite Development Server
```powershell
cd frontend
npm run dev
```

### Production Build
```powershell
cd frontend
npm run build
```

### Preview Production Build Locally
```powershell
cd frontend
npm run preview
```
