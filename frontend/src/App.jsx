import React, { useState } from 'react';
import './App.css';
import { analyzeFeedback } from './services/analysisApi';

function App() {
  const [feedbackText, setFeedbackText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const sampleNegative = "The faculty is not helpful and the explanations are not clear at all.";
  const samplePositive = "The library has an excellent collection of reference books and quiet study areas.";

  const handleAnalyze = async (e) => {
    e.preventDefault();

    // Client-side validation: reject empty or whitespace-only input
    if (!feedbackText || !feedbackText.trim()) {
      setError('Please enter meaningful feedback before analyzing.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await analyzeFeedback(feedbackText);
      setResult(data);
    } catch (err) {
      setError(err.message || 'An unexpected error occurred while analyzing your feedback.');
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

  return (
    <div className="container">
      {/* Header */}
      <header className="header">
        <div className="status-badge">
          <span className="pulse-dot"></span>
          Step 9.2 &bull; Intelligence Pipeline Connected
        </div>
        <h1 className="title">CampusVoice</h1>
        <p className="subtitle">AI-Powered Student Feedback Intelligence & Prioritization System</p>
      </header>

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
                  <span>Analyzing feedback with ML pipeline...</span>
                </>
              ) : (
                <span>Analyze Feedback</span>
              )}
            </button>
          </div>
        </form>
      </section>

      {/* Analysis Results Section */}
      {result && (
        <section className="results-wrapper" aria-live="polite" aria-label="Feedback Intelligence Results">
          <div className="results-header">
            <h2 className="results-title">Feedback Intelligence Breakdown</h2>
            <div className="models-tag">
              Models: <span>{result.models?.sentiment} (Sentiment)</span> &bull; <span>{result.models?.category} (Category)</span>
            </div>
          </div>

          <div className="results-grid">
            {/* 1. Priority Assessment Card */}
            <div className={`result-card priority-card ${getPriorityClass(result.priority?.level)}`}>
              <div className="card-header">
                <span className="card-tag">Administrative Signal</span>
                <span className={`priority-badge ${getPriorityClass(result.priority?.level)}`}>
                  Level: {result.priority?.level?.toUpperCase()}
                </span>
              </div>
              <h3 className="card-metric-title">Priority Assessment</h3>
              <div className="score-display">
                <span className="score-number">{result.priority?.score}</span>
                <span className="score-total">/ 100</span>
              </div>
              <div className="score-bar-container" aria-hidden="true">
                <div
                  className={`score-bar-fill ${getPriorityClass(result.priority?.level)}`}
                  style={{ width: `${result.priority?.score}%` }}
                ></div>
              </div>
              <p className="card-explanation">
                <strong>Reason:</strong> {result.priority?.reason}
              </p>
            </div>

            {/* 2. Sentiment Classification Card */}
            <div className={`result-card sentiment-card ${getSentimentClass(result.sentiment?.name)}`}>
              <div className="card-header">
                <span className="card-tag">Sentiment Analysis</span>
                <span className={`sentiment-badge ${getSentimentClass(result.sentiment?.name)}`}>
                  {result.sentiment?.name?.toUpperCase()}
                </span>
              </div>
              <h3 className="card-metric-title">Detected Polarity</h3>
              <div className="confidence-row">
                <span className="confidence-label">Model Confidence:</span>
                <span className="confidence-value">{formatPercent(result.sentiment?.confidence)}</span>
              </div>

              {result.sentiment?.probabilities && (
                <div className="probabilities-block">
                  <div className="prob-item">
                    <span>Negative</span>
                    <span>{formatPercent(result.sentiment.probabilities.negative)}</span>
                  </div>
                  <div className="prob-item">
                    <span>Neutral</span>
                    <span>{formatPercent(result.sentiment.probabilities.neutral)}</span>
                  </div>
                  <div className="prob-item">
                    <span>Positive</span>
                    <span>{formatPercent(result.sentiment.probabilities.positive)}</span>
                  </div>
                </div>
              )}
            </div>

            {/* 3. Category Classification Card */}
            <div className="result-card category-card">
              <div className="card-header">
                <span className="card-tag">Topic Modeling</span>
                <span className="category-badge">{result.category?.name}</span>
              </div>
              <h3 className="card-metric-title">Identified Category</h3>
              <div className="confidence-row">
                <span className="confidence-label">Model Confidence:</span>
                <span className="confidence-value">{formatPercent(result.category?.confidence)}</span>
              </div>

              {result.category?.probabilities && (
                <div className="probabilities-block">
                  {Object.entries(result.category.probabilities)
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
              <code>{result.clean_text || '(no tokens remaining)'}</code>
            </p>
            <p className="nlp-note">
              Sentiment-critical negation terms (such as <em>not</em>, <em>no</em>, <em>never</em>) are strictly retained during stopword filtering to ensure accurate polarity inference.
            </p>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="footer">
        <div className="meta-footer">
          <span className="meta-item">React 18 + Vite</span>
          <span>&bull;</span>
          <span className="meta-item">FastAPI REST Endpoint</span>
          <span>&bull;</span>
          <span className="meta-item">Priority Scoring Engine</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
