import React, { useState } from 'react';
import './App.css';
import { analyzeAndSaveFeedback } from './services/analysisApi';
import AdminDashboard from './components/AdminDashboard';
import LoginPage from './components/LoginPage';
import { AuthProvider, useAuth } from './context/AuthContext';

function AppContent() {
  const { user, isAuthenticated, isAdmin, isLoading, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('student'); // 'student' | 'admin' | 'login'
  const [feedbackText, setFeedbackText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const sampleNegative = "The faculty is not helpful and the explanations are not clear at all.";
  const samplePositive = "The library has an excellent collection of reference books and quiet study areas.";

  const handleLogout = () => {
    logout();
    setActiveTab('student');
  };

  const handleAnalyze = async (e) => {
    e.preventDefault();

    // Client-side validation: reject empty or whitespace-only input
    if (!feedbackText || !feedbackText.trim()) {
      setError('Please enter meaningful feedback before analyzing.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null); // Clear previous result immediately so stale data is not mistaken for a new submission

    try {
      const data = await analyzeAndSaveFeedback(feedbackText);
      setResult(data);
    } catch (err) {
      setError(err.message || 'An unexpected error occurred while saving and analyzing your feedback.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setFeedbackText('');
    setError(null);
    setResult(null);
  };

  const handleUseSample = (sample) => {
    setFeedbackText(sample);
    setError(null);
  };

  // Helper to format probabilities to percentage
  const formatPercent = (val) => {
    if (typeof val !== 'number') return '0.0%';
    return `${(val * 100).toFixed(1)}%`;
  };

  // Helper to format created_at ISO timestamp into human-readable string
  const formatTimestamp = (isoString) => {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return isoString;
      return d.toLocaleString('en-US', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return isoString;
    }
  };

  // Priority level styling helper
  const getPriorityClass = (level) => {
    const l = (level || '').toLowerCase();
    if (l === 'high') return 'priority-high';
    if (l === 'medium') return 'priority-medium';
    return 'priority-low';
  };

  // Sentiment class helper
  const getSentimentClass = (name) => {
    const s = (name || '').toLowerCase();
    if (s === 'negative') return 'sentiment-negative';
    if (s === 'positive') return 'sentiment-positive';
    return 'sentiment-neutral';
  };

  // Extracted metrics supporting both flat FeedbackResponse and nested objects
  const priorityLevel = result?.priority_level || result?.priority?.level;
  const priorityScore = result?.priority_score ?? result?.priority?.score ?? 0;
  const priorityReason = result?.priority_reason || result?.priority?.reason;
  const sentimentName = result?.sentiment_name || result?.sentiment?.name;
  const sentimentConfidence = result?.sentiment_confidence ?? result?.sentiment?.confidence;
  const categoryName = result?.category_name || result?.category?.name;
  const categoryConfidence = result?.category_confidence ?? result?.category?.confidence;
  const cleanText = result?.clean_text;
  const sentimentProbabilities = result?.sentiment?.probabilities;
  const categoryProbabilities = result?.category?.probabilities;
  const sentimentModel = result?.models?.sentiment || 'logistic_regression';
  const categoryModel = result?.models?.category || 'logistic_regression';

  return (
    <div className="container">
      {/* Header */}
      <header className="header">
        <div className="status-badge">
          <span className="pulse-dot"></span>
          {activeTab === 'student'
            ? 'CampusVoice \u2022 Student Feedback Portal'
            : activeTab === 'login'
            ? 'CampusVoice \u2022 Administrator Sign In'
            : isAuthenticated && isAdmin
            ? 'CampusVoice \u2022 Admin Analytics Dashboard'
            : 'CampusVoice \u2022 Administrator Portal'}
        </div>
        <h1 className="title">CampusVoice</h1>
        <p className="subtitle">AI-Powered Student Feedback Intelligence & Prioritization System</p>

        {/* View Navigation Tab Switcher */}
        <nav className="view-nav" aria-label="Portal Navigation">
          <div className="nav-container">
            <div className="nav-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                id="tab-student"
                aria-selected={activeTab === 'student'}
                aria-controls="panel-student"
                className={`nav-tab ${activeTab === 'student' ? 'active' : ''}`}
                onClick={() => setActiveTab('student')}
              >
                Student Feedback
              </button>

              {/* If Authenticated Admin: show Admin Dashboard tab */}
              {isAuthenticated && isAdmin && (
                <button
                  type="button"
                  role="tab"
                  id="tab-admin"
                  aria-selected={activeTab === 'admin'}
                  aria-controls="panel-admin"
                  className={`nav-tab ${activeTab === 'admin' ? 'active' : ''}`}
                  onClick={() => setActiveTab('admin')}
                >
                  Admin Dashboard
                </button>
              )}

              {/* If Unauthenticated: show Admin Sign In tab */}
              {!isAuthenticated && (
                <button
                  type="button"
                  role="tab"
                  id="tab-login"
                  aria-selected={activeTab === 'login' || activeTab === 'admin'}
                  aria-controls="panel-login"
                  className={`nav-tab ${activeTab === 'login' || activeTab === 'admin' ? 'active' : ''}`}
                  onClick={() => setActiveTab('login')}
                >
                  Admin Sign In
                </button>
              )}
            </div>

            {/* Authenticated user pill badge and Sign Out button */}
            {isAuthenticated && (
              <div className="auth-user-bar">
                <span className={`user-badge ${isAdmin ? 'badge-admin' : 'badge-student'}`}>
                  <span className="user-dot"></span>
                  <span className="user-name">{user?.username}</span>
                  <span className="user-role-label">({user?.role})</span>
                </span>
                <button
                  type="button"
                  id="nav-logout-btn"
                  className="nav-logout-btn"
                  onClick={handleLogout}
                  title="Sign out of your account"
                >
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </nav>
      </header>

      {/* Tab Panel: Student Feedback Portal */}
      {activeTab === 'student' && (
        <main id="panel-student" role="tabpanel" aria-labelledby="tab-student" className="tab-panel">
          {/* Main Feedback Analysis Form */}
          <section className="form-card" aria-label="Feedback Submission">
            <form onSubmit={handleAnalyze}>
              <div className="form-group">
                <div className="label-row">
                  <label htmlFor="feedback-input" className="form-label">
                    Student Feedback Input
                  </label>
                  <span className="char-counter">{feedbackText.length} characters</span>
                </div>

                <textarea
                  id="feedback-input"
                  className="feedback-textarea"
                  rows={4}
                  placeholder="Enter student course, faculty, exam, or facility feedback here (e.g. 'The laboratory computers are outdated and the software is not working...')"
                  value={feedbackText}
                  onChange={(e) => {
                    setFeedbackText(e.target.value);
                    if (error) setError(null);
                  }}
                  disabled={loading}
                  aria-describedby={error ? "feedback-error" : undefined}
                />
              </div>

              {/* Quick-fill Sample Suggestions */}
              <div className="samples-bar">
                <span className="samples-label">Quick test samples:</span>
                <button
                  type="button"
                  className="sample-btn"
                  onClick={() => handleUseSample(sampleNegative)}
                  disabled={loading}
                >
                  Needs Attention Sample
                </button>
                <button
                  type="button"
                  className="sample-btn"
                  onClick={() => handleUseSample(samplePositive)}
                  disabled={loading}
                >
                  Positive Sample
                </button>
                {feedbackText && (
                  <button
                    type="button"
                    className="clear-btn"
                    onClick={handleClear}
                    disabled={loading}
                  >
                    Clear
                  </button>
                )}
              </div>

              {/* Error Banner */}
              {error && (
                <div id="feedback-error" className="error-banner" role="alert">
                  <span className="error-icon" aria-hidden="true">&times;</span>
                  <span className="error-text">{error}</span>
                </div>
              )}

              {/* Submit Action */}
              <div className="form-actions">
                <button
                  type="submit"
                  className="analyze-btn"
                  disabled={loading || !feedbackText.trim()}
                  aria-busy={loading}
                >
                  {loading ? (
                    <>
                      <span className="btn-spinner" aria-hidden="true"></span>
                      <span>Saving &amp; analyzing feedback with ML pipeline...</span>
                    </>
                  ) : (
                    <span>Analyze Feedback</span>
                  )}
                </button>
              </div>
            </form>
          </section>

          {/* Analysis Results & Persistence Section */}
          {result && (
            <section className="results-wrapper" aria-live="polite" aria-label="Feedback Intelligence Results">
              {/* Step 9.4: Persistence Confirmation Section */}
              {typeof result.id === 'number' && (
                <div className="saved-confirmation" role="status" aria-live="polite">
                  <div className="saved-badge">
                    <span className="saved-icon" aria-hidden="true">&#10003;</span>
                    <span className="saved-title">Feedback Saved Successfully</span>
                  </div>
                  <div className="saved-meta">
                    <span className="saved-id">
                      <strong>Feedback ID:</strong> #{result.id}
                    </span>
                    {result.created_at && (
                      <span className="saved-time">
                        <strong>Submitted:</strong> {formatTimestamp(result.created_at)}
                      </span>
                    )}
                  </div>
                </div>
              )}

              <div className="results-header">
                <h2 className="results-title">Feedback Intelligence Breakdown</h2>
                <div className="models-tag">
                  Models: <span>{sentimentModel} (Sentiment)</span> &bull; <span>{categoryModel} (Category)</span>
                </div>
              </div>

              <div className="results-grid">
                {/* 1. Priority Assessment Card */}
                <div className={`result-card priority-card ${getPriorityClass(priorityLevel)}`}>
                  <div className="card-header">
                    <span className="card-tag">Administrative Signal</span>
                    <span className={`priority-badge ${getPriorityClass(priorityLevel)}`}>
                      Level: {priorityLevel ? priorityLevel.toUpperCase() : 'UNKNOWN'}
                    </span>
                  </div>
                  <h3 className="card-metric-title">Priority Assessment</h3>
                  <div className="score-display">
                    <span className="score-number">{priorityScore}</span>
                    <span className="score-total">/ 100</span>
                  </div>
                  <div className="score-bar-container" aria-hidden="true">
                    <div
                      className={`score-bar-fill ${getPriorityClass(priorityLevel)}`}
                      style={{ width: `${priorityScore}%` }}
                    ></div>
                  </div>
                  <p className="card-explanation">
                    <strong>Reason:</strong> {priorityReason || 'Deterministic assessment from confidence heuristics.'}
                  </p>
                </div>

                {/* 2. Sentiment Classification Card */}
                <div className={`result-card sentiment-card ${getSentimentClass(sentimentName)}`}>
                  <div className="card-header">
                    <span className="card-tag">Sentiment Analysis</span>
                    <span className={`sentiment-badge ${getSentimentClass(sentimentName)}`}>
                      {sentimentName ? sentimentName.toUpperCase() : 'UNKNOWN'}
                    </span>
                  </div>
                  <h3 className="card-metric-title">Detected Polarity</h3>
                  <div className="confidence-row">
                    <span className="confidence-label">Model Confidence:</span>
                    <span className="confidence-value">{formatPercent(sentimentConfidence)}</span>
                  </div>

                  {sentimentProbabilities && (
                    <div className="probabilities-block">
                      <div className="prob-item">
                        <span>Negative</span>
                        <span>{formatPercent(sentimentProbabilities.negative)}</span>
                      </div>
                      <div className="prob-item">
                        <span>Neutral</span>
                        <span>{formatPercent(sentimentProbabilities.neutral)}</span>
                      </div>
                      <div className="prob-item">
                        <span>Positive</span>
                        <span>{formatPercent(sentimentProbabilities.positive)}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* 3. Category Classification Card */}
                <div className="result-card category-card">
                  <div className="card-header">
                    <span className="card-tag">Topic Modeling</span>
                    <span className="category-badge">{categoryName || 'Unknown'}</span>
                  </div>
                  <h3 className="card-metric-title">Identified Category</h3>
                  <div className="confidence-row">
                    <span className="confidence-label">Model Confidence:</span>
                    <span className="confidence-value">{formatPercent(categoryConfidence)}</span>
                  </div>

                  {categoryProbabilities && (
                    <div className="probabilities-block">
                      {Object.entries(categoryProbabilities)
                        .sort(([, a], [, b]) => b - a)
                        .slice(0, 3)
                        .map(([cat, prob]) => (
                          <div key={cat} className="prob-item">
                            <span className="prob-cat-name">{cat}</span>
                            <span>{formatPercent(prob)}</span>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </div>

              {/* NLP Preprocessing & Negation Preservation Card */}
              <div className="result-card preprocessing-card">
                <div className="card-header">
                  <span className="card-tag">NLP Preprocessing & Negation</span>
                  <span className="nlp-badge">Step 3 &bull; spaCy + NLTK</span>
                </div>
                <h3 className="card-metric-title">Cleaned Normalized Text</h3>
                <p className="cleaned-text-display">
                  <code>{cleanText || '(no tokens remaining)'}</code>
                </p>
                <p className="nlp-note">
                  Sentiment-critical negation terms (such as <em>not</em>, <em>no</em>, <em>never</em>) are strictly retained during stopword filtering to ensure accurate polarity inference.
                </p>
              </div>
            </section>
          )}
        </main>
      )}

      {/* Tab Panel: Login Page */}
      {activeTab === 'login' && !isAuthenticated && (
        <main id="panel-login" role="tabpanel" aria-labelledby="tab-login" className="tab-panel">
          <LoginPage
            onSuccess={(userProfile) => {
              if (userProfile?.role === 'admin') {
                setActiveTab('admin');
              } else {
                setActiveTab('student');
              }
            }}
            onCancel={() => setActiveTab('student')}
          />
        </main>
      )}

      {/* Tab Panel: Admin Dashboard */}
      {activeTab === 'admin' && (
        <main id="panel-admin" role="tabpanel" aria-labelledby="tab-admin" className="tab-panel">
          {isLoading ? (
            <div className="auth-checking-state">
              <span className="auth-checking-spinner" aria-hidden="true"></span>
              <p>Verifying administrator session...</p>
            </div>
          ) : !isAuthenticated ? (
            <LoginPage
              onSuccess={(userProfile) => {
                if (userProfile?.role === 'admin') {
                  setActiveTab('admin');
                } else {
                  setActiveTab('student');
                }
              }}
              onCancel={() => setActiveTab('student')}
            />
          ) : !isAdmin ? (
            <div className="admin-denied-container">
              <div className="admin-denied-card">
                <div className="denied-icon" aria-hidden="true">&#128274;</div>
                <h2 className="denied-title">Admin Access Required</h2>
                <p className="denied-message">
                  Your account (<strong>{user?.username}</strong>) has the <strong>{user?.role}</strong> role.
                  Administrative privileges are strictly required to view student feedback intelligence analytics and records.
                </p>
                <div className="denied-actions">
                  <button
                    type="button"
                    className="denied-return-btn"
                    onClick={() => setActiveTab('student')}
                  >
                    Return to Student Portal
                  </button>
                  <button
                    type="button"
                    className="denied-logout-btn"
                    onClick={handleLogout}
                  >
                    Sign Out
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <AdminDashboard />
          )}
        </main>
      )}

      {/* Footer */}
      <footer className="footer">
        <div className="meta-footer">
          <span className="meta-item">React 18 + Vite</span>
          <span>&bull;</span>
          <span className="meta-item">FastAPI REST Endpoints</span>
          <span>&bull;</span>
          <span className="meta-item">PostgreSQL Persisted</span>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
