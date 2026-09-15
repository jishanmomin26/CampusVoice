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

## 8. Step 9.13.2 — Centralized Authenticated API & Session Handling

In **Step 9.13.2**, the React frontend transitions all authenticated HTTP communication to a robust, centralized API client layer (`src/services/apiClient.js`) that enforces consistent Bearer token injection, structured error classification, export safety, and concurrency-safe 401 session expiration handling.

### Architecture & Key Capabilities

* **Centralized API Client (`src/services/apiClient.js`)**:
  * Uniform wrapper around native `fetch` supporting `get`, `post`, `put`, and `delete`.
  * Automatically inspects `localStorage` via `getStoredToken()` and injects `Authorization: Bearer <token>` into outgoing requests when available.
  * Explicit token override support via `{ token }` option for pre-storage bootstrap verification (e.g., initial `/auth/me` check during login).
  * Automatically attaches `Content-Type: application/json` for request bodies.
  * Structured error classification via `ApiError` class with convenience boolean flags:
    * `isAuthError` (`status === 401`)
    * `isForbidden` (`status === 403`)
    * `isValidationError` (`status === 422`)
    * `isServerError` (`status >= 500`)
    * `isNetworkError` (`status === 0` / fetch network failure)
* **Automatic 401 Session Expiry & Non-Circular Decoupling**:
  * **Subscriber Pattern (`onUnauthorized`)**: `apiClient.js` maintains a set of unauthorized listeners without importing `AuthContext` or React hooks, completely avoiding circular dependency cycles.
  * When any protected endpoint responds with HTTP 401:
    1. Immediately purges the expired JWT from `localStorage` via `removeStoredToken()`.
    2. Notifies registered subscribers via `notifyUnauthorized()`.
    3. Throws an `ApiError(401)` preventing further consumer processing.
  * **AuthContext Subscription**: On mount, `AuthContext` registers a listener with `onUnauthorized(handleUnauthorized)`. Upon notification, it:
    * Resets user state to `null`.
    * Clears token state to `null`.
    * Sets `sessionExpired: true`.
  * **Auto-Navigation & Expiry Alert (`App.jsx`)**:
    * If `sessionExpired` is triggered while viewing the Admin Dashboard, the UI automatically transitions the active tab back to `"student"`.
    * An accessible, dismissible alert banner appears at the top of the Student Portal: `"Your session has expired. Please sign in again."`.
  * **Concurrency Protection**: An internal `isHandlingUnauthorized` mutex prevents multiple parallel 401 responses from triggering redundant storage clears, duplicate listener invocations, or navigation thrashing.
  * **No Blind 401 Retries**: Once a request encounters a 401, no automatic retries are executed; the request fails immediately and cleanly.
  * **Login Isolation (`skipAuthHandler: true`)**: The `login()` method passes `skipAuthHandler: true`, ensuring invalid credentials display an inline login error without triggering global session-expired handlers.
* **Service Layer Refactoring**:
  * **`statsApi.js`**: Refactored to use `apiClient.get('/api/v1/feedback/stats')`, preserving defensive validation and translating errors into friendly UI messages.
  * **`recordsApi.js`**: Refactored to use `apiClient.get('/api/v1/feedback/records?...')`.
  * **`authApi.js`**: Refactored `login()` and `getCurrentUser()` to use `apiClient`.
* **Export Safety During Session Invalidation**:
  * In `recordsApi.js` (`fetchAllMatchingFeedbackRecords`), sequential page fetches are executed with `apiClient.get`.
  * If a 401 occurs at any point during a multi-page fetch:
    * An `ApiError(401)` is thrown immediately.
    * Pagination is halted and zero further page requests are dispatched.
    * Generation of partial or corrupt CSV/Excel files is completely prevented.
* **Preservation of Public Student Feedback**:
  * Feedback submission functions (`analyzeAndSaveFeedback` and `analyzeFeedback` in `src/services/analysisApi.js`) remain public and unauthenticated, using standalone HTTP requests without Bearer token requirements or 401 side effects.

---

## 9. Step 9.14.2 — Admin User Management UI & Dashboard Integration

In **Step 9.14.2**, the frontend introduces the **User Management UI** integrated cleanly into the **Admin Dashboard**, providing full administrative control over institutional user accounts, roles, and activation states.

### Architecture & Components

* **API Service Layer (`src/services/usersApi.js`)**:
  * Fully integrated with centralized `apiClient.js` with Bearer token authentication and 401 session expiry handling.
  * `getUsers(params)`: Encodes query parameters safely via `URLSearchParams` for `page`, `page_size`, `search`, `role`, and `is_active`.
  * `getUser(userId)`: Fetches individual user record details by ID (`GET /api/v1/users/{user_id}`).
  * `createUser(payload)`: Provisions student or admin user (`POST /api/v1/users`). Handles HTTP 409 conflict errors cleanly.
  * `updateUser(userId, payload)`: Sends partial updates (`role`, `is_active`, optional `password`) via `PATCH /api/v1/users/{user_id}` using `apiClient.patch`.
* **User Management Component (`src/components/UserManagement.jsx` & `UserManagement.css`)**:
  * **Interactive Toolbar**:
    * Username search box with 350ms debounced input and single-click clear button.
    * Role filter dropdown (`All Roles`, `Admin`, `Student`).
    * Status filter dropdown (`All Status`, `Active`, `Inactive`).
    * "Clear Filters" action resetting query state back to page 1.
  * **User Accounts Data Table**:
    * Columns: `ID`, `Username`, `Role`, `Status`, `Created`, `Actions`.
    * Color-coded status badges with glowing status indicator dots (`Active` vs `Inactive`).
    * Role badges distinguishing `Admin` from `Student`.
    * Formatted timestamps (`formatTimestamp`).
  * **Self-Protection Safeguards**:
    * Detects the authenticated administrator by ID and username comparison against `useAuth()`.
    * Displays a prominent `(You)` badge next to the current admin's username in the table.
    * Disables the "Deactivate" button on the admin's own row with a descriptive assistive tooltip (`"You cannot deactivate your own account."`).
  * **Provision User Modal**:
    * Semantic modal dialog with focus management, backdrop blur, and escape key handling.
    * Fields: `Username` (required), `Password` (required, minimum 8 characters, password-masked), and `Role` (`student` or `admin`).
    * Conflict handling: Displays user-friendly error banners on 409 Conflict (`"That username is already in use."`) without crashing or modal dismissal.
  * **Edit User Modal**:
    * Displays permanent `Username` in a disabled, read-only input with informative hint.
    * Allows updating `Role` (`student` / `admin`) and `Account Status` (`Active` / `Inactive`).
    * Prevents admins from setting their own status to Inactive.
    * Optional password reset field (only sent when non-empty).
  * **Deactivation Confirmation Dialog**:
    * High-visibility danger dialog warning about immediate loss of account access while clarifying that historical student feedback remains safely preserved.
    * Direct "Activate" button for fast re-activation of previously deactivated accounts.
  * **Zero Sensitive Data Persistence**:
    * Passwords are never stored in component state after modal closure, never logged to the browser console, and never saved in `localStorage` or `sessionStorage`.
* **Dashboard Subnavigation (`src/components/AdminDashboard.jsx` & `AdminDashboard.css`)**:
  * Introduces responsive `.admin-subnav` button group with distinct tabs:
    * **Feedback Analytics**: KPI summary cards, interactive charts, and topic distributions.
    * **Feedback Records**: Full tabular view of student feedback, advanced filtering, record detail modals, and CSV/Excel export.
    * **User Management**: Administrative user provisioning, role assignments, and activation toggles.
  * Only rendered when `isAdmin === true`; student accounts are strictly prevented from viewing administrative navigation.
  * Seamless state switching without session loss or unnecessary page reloads.

---

## 10. Step 9.15.1 — Initial Bundle Optimization & Code Splitting

In **Step 9.15.1**, the React frontend architecture was optimized through component-level code splitting and on-demand dynamic imports, reducing the initial JavaScript payload by **81.1%** without altering any UI behavior, API contracts, or existing features.

### Architecture & Optimization Strategy

```text
                                Initial Page Load
                          (Student Feedback Submission)
                                        ↓
                       Initial Bundle: ~168 kB (53 kB gzip)
                     [App.jsx, Analysis Form, AuthContext]
                                        ↓
       ┌────────────────────────────────┼────────────────────────────────┐
       ↓                                ↓                                ↓
Admin Sign-In                Feedback Records View            Export to Excel
(Dynamic React.lazy)         (Dynamic React.lazy)             (Dynamic import('xlsx'))
       ↓                                ↓                                ↓
AdminDashboard.js (~14 kB)   FeedbackRecords.js (~16 kB)      xlsx.js (~429 kB)
DashboardCharts.js (~383 kB) FeedbackRecordDetail.js (~6 kB)  (Strictly on click)
UserManagement.js (~20 kB)
```

1. **On-Demand Dynamic Module Import (`src/utils/exportFeedback.js`)**:
   - Removed static `import * as XLSX from 'xlsx'` from the top-level bundle.
   - `exportFeedbackToExcel(records, customFilename)` is now an asynchronous function using runtime dynamic import (`const XLSX = await import('xlsx')`).
   - The heavy SheetJS library (~429 kB) is completely isolated and never downloaded during initial student or admin page loads.
   - Lightweight CSV export (`exportFeedbackToCSV`) remains synchronous and 100% dependency-free with zero XLSX overhead.

2. **Hierarchical Code Splitting with `React.lazy()` & `Suspense`**:
   - **`App.jsx`**: Lazy-loads `<AdminDashboard />`. Unauthenticated visitors and students never download administrative code.
   - **`AdminDashboard.jsx`**: Lazy-loads subviews and heavy modules:
     - `DashboardCharts` (`SentimentChart`, `PriorityChart`, `CategoryChart` powered by Recharts).
     - `FeedbackRecords` (Data table and filter toolbar).
     - `UserManagement` (User provisioning and administration).
   - **`FeedbackRecords.jsx`**: Lazy-loads the `<FeedbackRecordDetail />` modal dialog, fetched only when an administrator inspects an individual record.

3. **Resilient Error Boundaries & Accessible Fallbacks**:
   - **`ErrorBoundary` (`src/components/ErrorBoundary.jsx`)**:
     - Class component implementing `getDerivedStateFromError` and `componentDidCatch`.
     - Catches lazy chunk resolution failures (e.g. intermittent network drops) and renders a user-friendly error card with a "Retry Loading" button without exposing raw stack traces.
   - **`LazyFallback` (`src/components/LazyFallback.jsx`)**:
     - Accessible loading indicator utilizing `role="status"` and `aria-live="polite"`.
     - Pure CSS animated spinner matching the CampusVoice dark-glassmorphism design aesthetic.

### Measured Bundle Performance Metrics

Exact production build numbers measured via `npm run build` (Vite v5.4.21):

| Metric | Pre-Optimization (Baseline) | Post-Optimization (Step 9.15.1) | Reduction / Change |
| :--- | :--- | :--- | :--- |
| **Initial JS (`index.js`)** | `888.48 kB` | **`168.29 kB`** | **-720.19 kB (-81.06%)** |
| **Initial JS (gzip)** | `269.59 kB` | **`53.24 kB`** | **-216.35 kB (-80.25%)** |
| **Initial CSS (`index.css`)** | `61.54 kB` | **`22.31 kB`** | **-39.23 kB (-63.75%)** |
| **Initial CSS (gzip)** | `11.13 kB` | **`4.89 kB`** | **-6.24 kB (-56.06%)** |
| **Vite Chunk Warnings** | `(!) > 500 kB chunk warning` | **0 warnings (all chunks < 500 kB)** | **Fully Resolved** |

#### Production Chunk Breakdown (`dist/assets/`)

| Chunk File | Uncompressed Size | Gzip Payload | Loading Trigger |
| :--- | :--- | :--- | :--- |
| `index-v5G1hBlA.js` | 168.29 kB | 53.24 kB | **Initial Page Load** |
| `index-CmEM-P9v.css` | 22.31 kB | 4.89 kB | **Initial Page Load** |
| `AdminDashboard-CfvLDj9l.js` | 14.12 kB | 3.09 kB | On Admin Sign-In |
| `AdminDashboard-Dki5AkBm.css` | 9.99 kB | 2.42 kB | On Admin Sign-In |
| `DashboardCharts-Cm4vxQzA.js` | 383.06 kB | 111.18 kB | On Analytics Subview View (Recharts) |
| `DashboardCharts-BKgSF9dR.css` | 1.68 kB | 0.70 kB | On Analytics Subview View |
| `FeedbackRecords-CS6wmoTe.js` | 16.66 kB | 4.92 kB | On Feedback Records Tab Click |
| `FeedbackRecords-0DF2AcFS.css` | 12.43 kB | 3.08 kB | On Feedback Records Tab Click |
| `FeedbackRecordDetail-0IkvwSt8.js`| 6.24 kB | 1.41 kB | On Record "View Details" Click |
| `FeedbackRecordDetail-F5Z1wXlp.css`| 4.82 kB | 1.47 kB | On Record "View Details" Click |
| `UserManagement-B1CuvMbW.js` | 20.57 kB | 5.24 kB | On User Management Tab Click |
| `UserManagement-CfNsJlUW.css` | 12.43 kB | 2.93 kB | On User Management Tab Click |
| `xlsx-D_0l8YDs.js` | 429.03 kB | 143.08 kB | **Only on "Export Excel" button click** |

---

## 11. Configuration & Environment Variables

Copy `.env.example` to `.env` to override configuration:

```env
# FastAPI Backend URL
VITE_API_BASE_URL=http://127.0.0.1:8000
```

> **Security Note**: Never commit passwords, tokens, or local credentials to Git.

---

## 12. Development & Build Commands

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

### Run Automated Frontend Tests (Vitest)
```powershell
cd frontend
# Single CI test run
npm run test:run

# Interactive watch mode
npm test

# Test coverage analysis
npm run test:coverage
```

---

## 13. Step 9.16.1 — Frontend Automated Testing Foundation

In **Step 9.16.1**, an enterprise-grade automated testing foundation was introduced for the React frontend, utilizing **Vitest**, **React Testing Library**, **JSDOM**, and **V8 Coverage**. The testing setup is completely isolated from the production Vite pipeline (`vite.config.js`), ensuring zero bundle size overhead, zero production chunk changes, and total preservation of existing code-splitting performance.

### Testing Stack

- **Test Runner & Harness**: [Vitest v2.1.8](https://vitest.dev/) (fast, native ESM runner compatible with Vite 5)
- **DOM Environment**: [jsdom v29.1.1](https://github.com/jsdom/jsdom)
- **Component Testing**: [@testing-library/react v16.3.3](https://testing-library.com/docs/react-testing-library/intro/)
- **User Interaction Simulation**: [@testing-library/user-event v14.6.7](https://testing-library.com/docs/user-event/intro/)
- **Custom DOM Matchers**: [@testing-library/jest-dom v7.0.1](https://github.com/testing-library/jest-dom)
- **Coverage Engine**: [@vitest/coverage-v8 v2.1.8](https://vitest.dev/guide/coverage.html)

### Configuration Architecture

1. **`vitest.config.js`**:
   - Independent test configuration file defining `test.globals: true`, `test.environment: 'jsdom'`, and `test.setupFiles: ['./src/test/setup.js']`.
   - Production build (`vite.config.js`) remains untouched and unaware of testing infrastructure.
2. **`src/test/setup.js`**:
   - Imports `@testing-library/jest-dom/vitest` for rich assertions (`toBeInTheDocument`, `toHaveValue`, etc.).
   - Resets DOM body, clears `localStorage`, `sessionStorage`, and all mocks in `afterEach`.
   - Provides global browser environment shims: `ResizeObserver` (for Recharts responsive containers), `window.matchMedia`, `URL.createObjectURL`, and `URL.revokeObjectURL`.

### Test Suite Organization

The test suite contains **15 test files** across **99 passing tests**:

```text
frontend/src/
├── test/
│   └── setup.js                          # Global test environment & browser mocks
├── utils/__tests__/
│   ├── tokenStorage.test.js              # Token read, write, remove, expiry, validation (9 tests)
│   └── exportFeedback.test.js            # CSV escaping, sanitization, dynamic XLSX import (12 tests)
├── services/__tests__/
│   ├── apiClient.test.js                 # Headers, Bearer injection, timeout, 401 throttle (16 tests)
│   ├── authApi.test.js                   # Login API, /me profile fetching (3 tests)
│   ├── analysisApi.test.js               # Submission & analysis service methods (4 tests)
│   ├── statsApi.test.js                  # Analytics metrics endpoint handling (3 tests)
│   ├── recordsApi.test.js                # Query building, filters, pagination, details (5 tests)
│   └── usersApi.test.js                  # User CRUD operations & admin endpoints (9 tests)
├── context/__tests__/
│   └── AuthContext.test.jsx              # Auth provider, login, logout, session expiration (10 tests)
├── components/__tests__/
│   ├── LoginPage.test.jsx                # Form rendering, validation, submit, password toggle (6 tests)
│   ├── ErrorBoundary.test.jsx            # Error trapping, safe fallback card, retry handler (3 tests)
│   ├── LazyLoading.test.jsx              # Suspense fallbacks, accessible spinner (3 tests)
│   ├── FeedbackRecords.test.jsx          # Table render, search/filter, error state, detail modal (5 tests)
│   └── UserManagement.test.jsx           # User table, create/edit modals, conflict alerts (6 tests)
└── __tests__/
    └── App.test.jsx                      # Top-level portal, RBAC navigation tabs, session banner (5 tests)
```

### Covered Workflows & Scenarios

1. **Authentication & Token Storage**:
   - Storing, retrieving, clearing JWT tokens in `localStorage`.
   - Handling invalid tokens, non-string values, and storage quota exceptions gracefully.
   - Centralized 401 interception: token clearing and broadcast throttling to prevent notification spam.
2. **Context & State Management (`AuthContext`)**:
   - Initial hydration from stored token with `/me` profile validation.
   - Login mutation, error propagation, and role flag synchronization (`isAdmin`).
   - Clean logout wiping stored tokens and session state.
   - Session expiration event handling and alert banner toggling.
3. **Data Export (`exportFeedback`)**:
   - CSV header generation, date formatting, CSV formula injection neutralization (`=`, `+`, `-`, `@`).
   - Dynamic `import('xlsx')` execution verifying SheetJS is strictly loaded on demand.
4. **Interactive Component Workflows**:
   - `LoginPage`: Accessible inputs, required field alerts, submit payload trimming, credential error displays.
   - `UserManagement`: Self-protection rules (disabling deactivation and role demotion for current admin), create user modal with 409 conflict handling, edit user modal with password preservation.
   - `FeedbackRecords`: Table sorting, multi-attribute filtering, pagination bounds, detail modal launch.
   - `ErrorBoundary` & `LazyFallback`: Safe chunk failure trapping and accessible loading states.
5. **Portal RBAC & Navigation (`App.jsx`)**:
   - Public student feedback submission form and confirmation banner.
   - Unauthenticated visitors seeing only the "Admin Sign In" tab.
   - Authenticated student accounts restricted from administrative navigation.
   - Authenticated administrators granted access to the Admin Dashboard.

### Measured Coverage Results (`npm run test:coverage`)

```text
-------------------|---------|----------|---------|---------|-------------------
File               | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s 
-------------------|---------|----------|---------|---------|-------------------
All files          |   65.88 |    69.54 |   59.12 |   65.88 |                   
 src               |   42.46 |    27.27 |   14.28 |   42.46 |                   
  App.jsx          |   42.46 |    27.27 |   14.28 |   42.46 | ...52-463,468-522 
 src/components    |    58.3 |    63.32 |   53.65 |    58.3 |                   
  ...Dashboard.jsx |       0 |        0 |       0 |       0 | 1-510             
  ...ardCharts.jsx |       0 |        0 |       0 |       0 | 1-298             
  ...rBoundary.jsx |   95.65 |       90 |     100 |   95.65 | 24-25             
  ...ordDetail.jsx |   90.76 |       28 |   71.42 |   90.76 | ...1,77-78,83,134 
  ...ckRecords.jsx |    83.4 |     61.9 |      45 |    83.4 | ...04,465-471,500 
  LazyFallback.jsx |     100 |      100 |     100 |     100 |                   
  LoginPage.jsx    |     100 |     93.1 |     100 |     100 | 50,129            
  ...anagement.jsx |    85.6 |    62.96 |    43.9 |    85.6 | ...22-824,895-898 
 src/context       |     100 |      100 |     100 |     100 |                   
  AuthContext.jsx  |     100 |      100 |     100 |     100 |                   
 src/services      |   89.06 |    79.87 |     100 |   89.06 |                   
  analysisApi.js   |   69.23 |    72.41 |     100 |   69.23 | ...53-154,158-165 
  apiClient.js     |   95.34 |    81.63 |     100 |   95.34 | ...75,205-207,216 
  authApi.js       |   83.05 |    44.44 |     100 |   83.05 | ...43,57-58,66-67 
  recordsApi.js    |     100 |    85.29 |     100 |     100 | 60,105-107,110    
  statsApi.js      |     100 |      100 |     100 |     100 |                   
  usersApi.js      |   90.78 |    81.25 |     100 |   90.78 | ...39-140,154-155 
 src/utils         |   96.94 |    86.15 |     100 |   96.94 |                   
  ...rtFeedback.js |   96.98 |    84.61 |     100 |   96.98 | ...02,172,225-226 
  tokenStorage.js  |   96.82 |     92.3 |     100 |   96.82 | 51-52             
-------------------|---------|----------|---------|---------|-------------------
Test Files: 15 passed (15)
Tests:      99 passed (99)
```
