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

## 4. Step 9.9 — Admin Dashboard Feedback Records Table

In **Step 9.9**, the Admin Dashboard is enhanced with a dedicated **Feedback Records Management** section positioned beneath the KPI cards and analytics charts.

### Architecture & Key Capabilities

* **API Service Layer (`src/services/recordsApi.js`)**:
  * `getFeedbackRecords({ page, pageSize, search, sentiment, category, priority })`: Communicates directly with backend endpoint `GET /api/v1/feedback/records`.
  * Constructs query parameters dynamically, safely omitting empty or default filter values.
  * Robust error handling translating HTTP 422, 503, 500, and connection timeouts into user-friendly messages.
* **Server-Side Keyword Search**:
  * Searches `feedback_text` through PostgreSQL case-insensitive substring matching.
  * 350ms debounced user input prevents unnecessary network requests during active typing.
  * Automatic reset to page 1 upon search term alteration.
  * Dedicated clear (`×`) button to quickly reset search.
* **Multi-Criteria Dynamic Filtering**:
  * **Sentiment**: Filter by `positive`, `neutral`, `negative` or view all.
  * **Priority**: Filter by `high`, `medium`, `low` urgency tiers.
  * **Dynamic Categories**: Populates category dropdown options dynamically from `stats.categories` (zero hardcoded ML labels).
  * **Clear Filters Action**: One-click reset restoring default unfiltered records and returning to page 1.
* **Server-Side Pagination**:
  * Leverages backend metadata (`total`, `page`, `page_size`, `total_pages`).
  * Displays informative status: `"Showing page X of Y · Z matching records"`.
  * Configurable rows per page selector (`10`, `20`, `50`).
  * Accessible Previous and Next navigation buttons with proper boundary disabling.
  * Gracefully handles out-of-range or empty page results.
* **Responsive Records Table (`src/components/FeedbackRecords.jsx` & `FeedbackRecords.css`)**:
  * **Columns**: ID (`#id`), Feedback Message, Sentiment (color-coded badge), Sentiment Confidence (`%`), Category, Category Confidence (`%`), Priority (tier badge + score pill), Submitted (human-readable localized timestamp).
  * **Legacy Record Safety**: Seamlessly displays `Unclassified` badges and `—` placeholders for records with `NULL` analysis fields without fabricating data or crashing.
  * **Overflow & Mobile Support**: Contained within an accessible horizontally scrollable container (`table-responsive-container`) with touch scrolling enabled for tablet and mobile viewports (<768px and ~390px).
* **Dedicated Component States**:
  * Clean inline loading indicator with CSS spinner.
  * Error alert banner with functional **Retry** button.
  * Distinct empty state differentiating between an empty database and filter criteria that returned no matching records.

---

## 5. Step 9.10 — Feedback Record Detail / Full Analysis View

In **Step 9.10**, the Admin Dashboard introduces a focused, in-depth **Feedback Record Detail Modal** (`FeedbackRecordDetail.jsx`), allowing administrators to inspect complete ML intelligence for any individual feedback record without navigating away, reloading the page, or executing redundant network requests.

### Architecture & Key Capabilities

* **Zero-Extra-Endpoint Architecture**:
  * Leverages the rich dataset already loaded by `GET /api/v1/feedback/records`.
  * The backend records endpoint provides all 14 necessary fields (`id`, `department`, `semester`, `feedback_text`, `clean_text`, `created_at`, `sentiment_name`, `sentiment_label`, `sentiment_confidence`, `category_name`, `category_confidence`, `priority_score`, `priority_level`, `priority_reason`).
  * Modal opens instantaneously upon user interaction without network latency or additional server overhead.
* **Component Architecture (`src/components/FeedbackRecordDetail.jsx` & `FeedbackRecordDetail.css`)**:
  * **Dialog Accessibility**: Formatted with `role="dialog"`, `aria-modal="true"`, semantic header, and accessible dismiss triggers.
  * **Dismissal Modes**:
    * Dedicated close button (`×`).
    * Clicking outside the modal container on the glassmorphic backdrop.
    * Keyboard shortcut: Pressing <kbd>Escape</kbd> automatically dismisses the modal and restores focus.
  * **State Preservation**:
    * Opening and closing the detail view does not re-fetch the records table, preserving the administrator's active page number, search query, and filter selections.
* **Comprehensive Multi-Dimensional Intelligence Display**:
  * **Header & Metadata**: Record ID (`#id`), localized creation timestamp, department, and semester.
  * **Original Feedback Text**: Full student submission rendered inside a styled quote callout block.
  * **NLP Preprocessed / Normalized Text**: Displays the cleaned, tokenized, and negation-preserved text (`clean_text`) produced by the NLP pipeline.
  * **Sentiment Analysis Card**:
    * Sentiment badge (`Positive`, `Neutral`, `Negative`, or `Unclassified`).
    * Calibrated model confidence score with progress bar (`XX.X%`).
    * Raw model label code (`LABEL_2`, `LABEL_1`, `LABEL_0`, or `Unclassified`).
  * **Feedback Category Card**:
    * Classified institutional category name (`Faculty & Teaching`, `Course Content`, `Infrastructure & Facilities`, etc.).
    * Calibrated category confidence score with progress meter (`XX.X%`).
  * **Priority Assessment Card**:
    * Urgency tier badge (`HIGH`, `MEDIUM`, `LOW`, or `Unclassified`).
    * Exact deterministic priority score out of 100 with visual meter.
    * Explainable administrative reasoning text (`priority_reason`).
* **Safe Handling of Legacy & Unclassified Records**:
  * Records with `NULL` analysis fields (such as legacy records inserted before Step 7 intelligence pipeline integration) display graceful placeholders (`"Not available"`, `"Not provided"`, `"Unclassified"`, and `"—"`).
  * Absolutely zero synthetic or fabricated values are displayed, and no runtime exceptions are triggered.
* **Fully Responsive Design**:
  * Seamlessly adapts across Desktop (>1024px), Tablet (768px), and Mobile (390px) viewports with constrained max-height, backdrop-filter blur, and smooth vertical scrolling.

---

## 6. Step 9.11 — Feedback Export & Reporting

In **Step 9.11**, the Admin Dashboard adds comprehensive, client-side **CSV** and **Excel (.xlsx)** export capabilities (`exportFeedback.js`), empowering institutional leaders to download feedback intelligence matching their active filter selections.

### Architecture & Key Capabilities

* **Local Browser-Side Generation**:
  * All export transformations, formatting, and file generation happen strictly within the user's browser.
  * No feedback data is transmitted to external third-party services or APIs.
  * Object URLs used for download triggers are revoked immediately after delivery.
* **All-Matching-Records Architecture**:
  * The export represents **all records** matching the current search and filter criteria, rather than only the records displayed on the current pagination page.
  * Respects the backend maximum `page_size` constraint (`100` items per request) via `fetchAllMatchingFeedbackRecords`.
  * If matching records span multiple pages, the client fetches pages sequentially using the backend's `total_pages` metadata, preventing uncontrolled parallel requests or memory spikes.
* **Preservation of Active View & State**:
  * Exporting data never resets or modifies the administrator's active page number, search input, debounced query, or dropdown filter selections.
* **CSV Export (`exportFeedbackToCSV`)**:
  * Formatted strictly according to RFC 4180 standards.
  * Correctly escapes fields containing commas, double quotes (`""`), carriage returns, and newlines.
  * Prepends a UTF-8 Byte Order Mark (`\uFEFF`) ensuring that special characters and multi-line feedback open seamlessly in Microsoft Excel.
* **Excel Export (`exportFeedbackToExcel`)**:
  * Generates native binary `.xlsx` workbooks powered by **SheetJS (`xlsx` v0.18.5)**.
  * Standard sheet name: `"Feedback Records"`.
  * Applies practical spreadsheet optimizations, including frozen header rows and auto-adjusted readable column widths (`!cols`).
* **Standardized 14 Export Columns**:
  1. `ID`
  2. `Department`
  3. `Semester`
  4. `Original Feedback`
  5. `Processed Text`
  6. `Sentiment`
  7. `Sentiment Label`
  8. `Sentiment Confidence`
  9. `Category`
  10. `Category Confidence`
  11. `Priority Level`
  12. `Priority Score`
  13. `Priority Reason`
  14. `Submitted`
* **Safe NULL Handling for Legacy & Incomplete Records**:
  * Missing classifications default to `"Unclassified"`.
  * Missing numerical values (confidence percentages, priority scores) remain clean empty cells rather than zero, `NaN`, or fabricated estimates.
  * Missing text metadata (department, semester, clean text, administrative reason) remain clean empty cells.
* **Deterministic, Sanitized Filenames**:
  * Generated with daily timestamps: `campusvoice_feedback_YYYY-MM-DD.csv` and `campusvoice_feedback_YYYY-MM-DD.xlsx`.
  * Avoids embedding raw user queries or arbitrary inputs into filenames.
* **Empty State & Disabled Controls**:
  * When active filters yield zero matching records (`total === 0`), the export buttons are automatically disabled with accessible tooltip indications (`"No records to export"`).

---

## 7. Step 9.13.1 — Frontend Authentication Foundation & Role-Based Access Control

In **Step 9.13.1**, the React frontend is enhanced with an accessible, production-grade authentication foundation and role-based access control (RBAC):

### Architecture & Components

* **Authentication API Service (`src/services/authApi.js`)**:
  * `login(username, password)`: Submits credentials to `POST /api/v1/auth/login`. Handles 401 with a sanitized `"Invalid username or password."` error and returns signed JWT access token.
  * `getCurrentUser(token)`: Queries `GET /api/v1/auth/me` using `Authorization: Bearer <token>` to retrieve the authenticated user profile (`id`, `username`, `role`, `is_active`, `created_at`).
  * Reuses `VITE_API_BASE_URL` pattern with graceful network and server error handling.
* **Centralized Token Storage (`src/utils/tokenStorage.js`)**:
  * JWT access token is persisted in browser `localStorage` under the dedicated key:
    `campusvoice_access_token`
  * **Strict Credential Security**: User passwords are **never** stored in `localStorage`, `sessionStorage`, cookies, URL parameters, console logs, or persistent state.
* **Authentication Context & Provider (`src/context/AuthContext.jsx`)**:
  * Provides global `useAuth()` hook exposing:
    * `user`: Current profile object or `null`.
    * `token`: Stored JWT access token or `null`.
    * `isAuthenticated`: Boolean (`Boolean(user && token)`).
    * `isAdmin`: Boolean (`Boolean(user && user.role === 'admin')`).
    * `isLoading`: Boolean (`true` during initial `/auth/me` verification).
    * `login(username, password)`: Validates credentials, fetches profile, persists token.
    * `logout()`: Clears token, resets auth state, and returns to Student view.
  * **Session Restoration**: On application mount, `AuthContext` automatically checks `localStorage` for an existing token and calls `GET /api/v1/auth/me`. If valid, the user session is restored seamlessly; if expired or invalid, the token is cleanly purged.
* **Login Page (`src/components/LoginPage.jsx` & `LoginPage.css`)**:
  * Glassmorphic CampusVoice design language matching the main dashboard.
  * Accessible `<form>` with associated labels, `autoComplete="username"` and `autoComplete="current-password"`, show/hide password toggle, and accessible error banners (`role="alert"`, `aria-live="polite"`).
  * Safe, sanitized error messages preventing exposure of backend exceptions or stack traces.
* **Role-Based Navigation & Access Control (`App.jsx`)**:
  * **Unauthenticated Users**:
    * Full access to Student Feedback submission, NLP preprocessing, and persistence.
    * Navigation displays `"Student Feedback"` and `"Admin Sign In"` tabs.
    * Accessing the Admin tab prompts the login interface.
  * **Authenticated Admins (`role: "admin"`)**:
    * Access to both `"Student Feedback"` and `"Admin Dashboard"` tabs.
    * Header displays user badge (`admin (admin)`) and `"Sign Out"` action.
    * API services (`statsApi.js` and `recordsApi.js`) automatically attach the Bearer token to backend requests.
  * **Authenticated Students (`role: "student"`)**:
    * Access to `"Student Feedback"`.
    * `"Admin Dashboard"` tab is hidden from the navigation bar.
    * If an administrative route is reached, a safe `"Admin Access Required"` warning is displayed with a button to return to the student portal.
* **Logout Flow**:
  * Invokes `logout()`, removing `campusvoice_access_token` from `localStorage`.
  * Resets auth state and immediately returns to the Student Feedback view without requiring a full browser page refresh.

---

## 8. Configuration & Environment Variables

Copy `.env.example` to `.env` to override configuration:

```env
# FastAPI Backend URL
VITE_API_BASE_URL=http://127.0.0.1:8000
```

> **Security Note**: Never commit passwords, tokens, or local credentials to Git.

---

## 9. Development & Build Commands

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



