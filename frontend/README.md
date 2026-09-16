# CampusVoice — Frontend Service

Interactive, responsive React + Vite web client for the **CampusVoice** Student Feedback Intelligence platform.

---

## 1. Overview

The frontend service provides a modern web interface for students to submit course and campus feedback, receive instant intelligence analysis, and for administrators to review institutional analytics, inspect feedback records, manage users, and export reports.

* **Framework**: React 18.3+
* **Build Tool**: Vite 5.4+
* **Language**: JavaScript (ES6+)
* **Styling**: Vanilla CSS (Custom tokens, responsive grid, glassmorphic accents)
* **Visualizations**: Recharts 3.10+
* **Spreadsheet Generation**: XLSX (SheetJS)
* **Testing**: Vitest 2.1+, React Testing Library, JSDOM
* **Production Hosting**: Vercel

---

## 2. Getting Started

### Prerequisites
* **Node.js**: Version 18.0 or higher
* **npm**: Version 9.0 or higher

### Installation
From the `frontend/` directory:
```bash
npm install
```

### Development Server
Launch the local development server with Hot Module Replacement (HMR):
```bash
npm run dev
```
The application will be accessible at: `http://localhost:5173`.

### Production Build & Preview
Create an optimized production bundle:
```bash
npm run build
```
Preview the production build locally:
```bash
npm run preview
```

---

## 3. Environment Configuration (`.env`)

Frontend configuration is handled via Vite environment variables prefixed with `VITE_`:

### Environment File Template (`frontend/.env.example`)
```env
# CampusVoice Frontend Environment Configuration Example
# FastAPI Backend Base URL
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Production Configuration (Vercel)
In production on Vercel, set:
```env
VITE_API_BASE_URL=https://campusvoice-api-2nkg.onrender.com
```

---

## 4. Application Workflows

### A. Student Feedback Submission Portal
* **Submission Interface (`App.jsx`)**:
  * Multiline feedback input with real-time character counter and validation.
  * Quick-fill demonstration buttons (`Needs Attention Sample`, `Positive Sample`, `Clear`).
  * Instant feedback intelligence preview upon submission.
* **Persistence Confirmation Banner**:
  * Displays real database ID (`Feedback ID: #{result.id}`) and formatted timestamp upon successful PostgreSQL persistence.
  * Accessible via `role="status"` and `aria-live="polite"`.

### B. Administrator Dashboard & Analytics
* **Authentication (`LoginPage.jsx`)**:
  * Secure credential authentication issuing JWT access tokens.
  * Timing-attack hardened backend endpoint with user-friendly error banners.
* **Analytical Summary Cards (`AdminDashboard.jsx`)**:
  * High-level metrics: total submissions, analyzed count, sentiment split, and priority breakdowns.
* **Interactive Data Visualizations (`DashboardCharts.jsx`)**:
  * Sentiment distribution donut chart.
  * Priority breakdown vertical bar chart.
  * Category frequency horizontal bar chart.
* **Feedback Records Table (`FeedbackRecords.jsx`)**:
  * Multi-attribute filtering by sentiment, academic category, and priority tier.
  * Debounced keyword search across feedback text.
  * Server-side pagination with customizable page sizes.
* **Record Detail Modal (`FeedbackRecordDetail.jsx`)**:
  * In-depth modal dialog showing raw text, normalized tokens, lemmatized tokens, sentiment confidence, category probabilities, and priority reason.
* **Data Export Utility (`exportFeedback.js`)**:
  * Client-side export of filtered or full records to CSV or Excel (`.xlsx`).
* **Admin User Management (`UserManagement.jsx`)**:
  * Create, edit, and toggle activation status for system users.
  * Safeguards preventing admins from deactivating themselves or locking out the last active admin.

---

## 5. Performance Optimization: Code Splitting & Lazy Loading

To ensure minimal initial bundle sizes and fast First Contentful Paint (FCP), all heavy administrative views are split into separate asynchronous chunks using `React.lazy` and `Suspense`:

* `LazyDashboardCharts`: Recharts charting library is loaded on-demand only when the admin dashboard is active.
* `LazyFeedbackRecords`: Records table loaded only when viewing records.
* `LazyFeedbackDetail`: Modal chunk loaded only upon inspecting a record.
* `LazyUserManagement`: User management view loaded only when accessed.
* `ErrorBoundary`: Graceful error trapping with user-friendly retry states if network drops occur during dynamic chunk loading.

### Measured Bundle Performance
* Initial JS bundle size: **168.29 kB** (gzipped: ~51 kB)
* Initial CSS bundle size: **22.31 kB**

---

## 6. Security Architecture & Session Protection

* **Token Storage**: JWT access tokens are stored in `localStorage` under `campusvoice_access_token`.
* **Zero Credential Exposure**: Plaintext passwords, bcrypt hashes, and internal database keys are never stored in browser storage or logged to the console.
* **Automatic Session Expiration**: An `HTTP 401 Unauthorized` interceptor in `apiClient.js` purges expired tokens and clears React authentication states.
* **Notification Flood Throttling**: A 400ms broadcast cooldown ensures concurrent failing requests generate a single session expiration alert rather than stacked alert storms.
* **Clean Logout**: Purges local storage tokens and immediately restores public student view states.

---

## 7. Testing & Quality Assurance

The frontend test suite is executed using **Vitest** and **React Testing Library**:

```bash
# Run tests interactively in watch mode
npm test

# Run tests once (CI mode)
npm run test:run

# Run tests with code coverage analysis
npm run test:coverage
```

### Test Coverage Summary:
* **Total Test Files**: 16 passed
* **Total Tests**: **108 passed** (0 failed)
* Test suites include:
  * `App.test.jsx`: Portal navigation and public feedback workflow.
  * `LoginPage.test.jsx`: Form rendering, validation, and login actions.
  * `FeedbackRecords.test.jsx`: Records table, search, filters, and pagination.
  * `FeedbackRecordDetail.test.jsx`: Detail modal dialog and probability meters.
  * `UserManagement.test.jsx`: User administration, conflict errors, and role safeguards.
  * `AuthContext.test.jsx`: State initialization, session persistence, and logout.
  * `securitySession.test.jsx`: 401 interceptors, broadcast throttling, and storage errors.
  * `exportFeedback.test.js`: CSV and XLSX generation integrity.
  * `ErrorBoundary.test.jsx`: Lazy chunk recovery and retry handlers.

---

## 8. Production Deployment on Vercel

The frontend is deployed to **Vercel**:
* **Production URL**: `https://campus-voice-01.vercel.app`
* **Connected Backend**: `https://campusvoice-api-2nkg.onrender.com`

### Vercel Deployment Configuration:
* **Framework Preset**: Vite
* **Build Command**: `npm run build`
* **Output Directory**: `dist`
* **Environment Variable**: `VITE_API_BASE_URL=https://campusvoice-api-2nkg.onrender.com`
