# CampusVoice — Frontend Service

React + Vite frontend for the **CampusVoice** Student Feedback Intelligence platform.

---

## 1. Overview
The frontend provides an interactive, responsive web interface for students to submit institutional feedback and receive immediate, transparent feedback intelligence powered by the FastAPI backend, unified NLP/ML pipeline, and PostgreSQL persistence.

---

## 2. Step 9.4 — Student Feedback Submission & PostgreSQL Persistence

In **Step 9.4**, the primary student feedback submission flow is connected to the backend persistence endpoint:
`POST /api/v1/feedback/analyze-and-save`

### End-to-End Information Flow

```text
       Student
          ↓
  React Feedback Form
  (App.jsx — client validation)
          ↓
  analyzeAndSaveFeedback()
  (analysisApi.js Service Layer)
          ↓
POST /api/v1/feedback/analyze-and-save
          ↓
       FastAPI
  (Validation & Error Handling)
          ↓
FeedbackIntelligencePipeline
  (NLP + TF-IDF + Sentiment + Category + Priority)
          ↓
PostgreSQL Database
  (Feedback table persistence & commit)
          ↓
   FeedbackResponse JSON
  (Database ID + Timestamps + Intelligence)
          ↓
  React UI Render
  (Saved Confirmation Banner + Intelligence Cards)
```

### Component & State Architecture

- **Feedback Submission Form (`App.jsx`)**:
  - Semantic `<label htmlFor="feedback-input">` and `<textarea>` with character counter.
  - Client-side validation preventing submission of empty or whitespace-only inputs.
  - Quick-fill sample buttons (`Needs Attention Sample`, `Positive Sample`, `Clear`).
  - Loading spinner indicator disabling the Analyze button during API calls to prevent duplicate submissions.
  - The previous analysis result is cleared immediately upon initiating a new submission so stale data cannot be mistaken for the current submission.
  - User feedback text is preserved in the input area across loading and error states for seamless retries.
- **Persistence Confirmation Banner (`App.jsx`)**:
  - Displays a dedicated, accessible confirmation badge at the top of the results section:
    - Status icon and `"Feedback Saved Successfully"`.
    - Real database record identifier (`Feedback ID: #{result.id}`).
    - Formatted creation timestamp (`Submitted: 14 Sep 2026, ...`).
    - Uses `role="status"` and `aria-live="polite"` for assistive technology.
- **Analysis Result Display (`App.jsx`)**:
  - **Priority Assessment**: Displays score (/100), visual meter, level (`HIGH`, `MEDIUM`, `LOW`) using accessible badge markers and text labels (not color alone), and deterministic administrative reasoning.
  - **Sentiment Analysis**: Displays polarity (`NEGATIVE`, `NEUTRAL`, `POSITIVE`), model confidence percentage, and probability breakdown.
  - **Category Classification**: Displays primary category name, model confidence score, and top category probabilities breakdown.
  - **NLP Preprocessing Card**: Displays cleaned normalized text (`clean_text`), showing how sentiment-critical negation terms (`not`, `no`, `never`) are preserved.
- **API Service Layer (`src/services/analysisApi.js`)**:
  - `analyzeAndSaveFeedback(feedbackText, metadata)`: Submits to `POST /api/v1/feedback/analyze-and-save` and returns the persisted record.
  - `analyzeFeedback(feedbackText)`: Retained as an analysis-only service targeting `POST /api/v1/feedback/analyze`.
  - Configurable backend target via `VITE_API_BASE_URL` (defaults to `http://127.0.0.1:8000`).
  - Safe error handling translating HTTP 422, 503, 500, and network failures into user-friendly messages without exposing internal stack traces.

---

## 3. Step 9.6 — React Admin Dashboard Foundation

In **Step 9.6**, the frontend introduces the first controlled version of the **Admin Dashboard**, providing high-level statistical intelligence without adding third-party charting or routing libraries.

### Architecture & Navigation

* **Portal View Navigation (`App.jsx`)**:
  * An accessible tab-switcher allowing seamless navigation between:
    * **Student Feedback**: Interactive feedback submission, ML analysis, and PostgreSQL persistence.
    * **Admin Dashboard**: Live, database-backed aggregate feedback statistics and intelligence overview.
  * No routing dependencies required; uses clean, lightweight state-driven tab switching.
* **Dedicated Statistics API Service (`src/services/statsApi.js`)**:
  * `getFeedbackStats()`: Communicates with `GET /api/v1/feedback/stats`.
  * Defensively validates response fields (`total_feedback`, `analyzed_feedback`, `unclassified_feedback`, `sentiment`, `priority`, `categories`).
  * Graceful error handling for network outages, HTTP 503, and HTTP 500 without leaking raw backend stack traces.
* **Admin Dashboard Component (`src/components/AdminDashboard.jsx`)**:
  * **Top-Level KPI Cards**:
    * Total Submissions (`stats.total_feedback`)
    * Analyzed Feedback (`stats.analyzed_feedback`)
    * Unclassified Feedback (`stats.unclassified_feedback`)
    * High Priority (`stats.priority.high`)
  * **Sentiment Breakdown**:
    * Positive, Neutral, Negative, and Unclassified counts with pure CSS progress meters.
  * **Priority Tiers**:
    * High, Medium, Low, and Unclassified urgency metrics with clear text labels and visual bars.
  * **Dynamic Departmental & Topic Categories**:
    * Dynamically iterates over `stats.categories` to display all active categories present in the database. Zero hardcoded category names.
  * **Interactive Refresh**:
    * Updates live statistics from PostgreSQL without reloading the browser page.
  * **Error Resilience & Retry**:
    * Displays friendly error alerts and a functional **Retry** button if the backend statistics service is unreachable.
* **Responsive Layout (`src/components/AdminDashboard.css`)**:
  * Desktop: 4-column KPI cards and side-by-side breakdown grids.
  * Mobile (<640px): Stacks gracefully into single-column cards with zero horizontal overflow.

---

## 4. Configuration & Environment Variables

Copy `.env.example` to `.env` to override configuration:

```env
# FastAPI Backend URL
VITE_API_BASE_URL=http://127.0.0.1:8000
```

> **Note**: Do not commit secrets or local credentials to Git.

---

## 5. Development & Build Commands

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

