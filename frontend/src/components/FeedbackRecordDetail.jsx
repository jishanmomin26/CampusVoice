import React, { useEffect } from 'react';
import './FeedbackRecordDetail.css';

/**
 * FeedbackRecordDetail Component (Step 9.10)
 * 
 * Presentation modal displaying complete analysis details for a selected feedback record:
 * - Original feedback text (untruncated)
 * - NLP preprocessed clean text
 * - Submission metadata (Department, Semester, Created Timestamp)
 * - Sentiment classification (name, numeric label, calibrated confidence %)
 * - Category classification (category name, confidence %)
 * - Priority scoring (level badge, score / 100, explainable reason)
 * - Safe NULL handling for unclassified legacy records
 * - Accessible modal dialog with keyboard navigation (Escape to close)
 */
export default function FeedbackRecordDetail({ record, onClose }) {
  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!record) return null;

  // Format confidence percentage
  const formatConfidence = (val) => {
    if (typeof val !== 'number' || isNaN(val)) return '—';
    return `${(val * 100).toFixed(1)}%`;
  };

  // Format ISO timestamp into local human-readable date/time
  const formatTimestamp = (isoString) => {
    if (!isoString) return '—';
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) return '—';
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return '—';
    }
  };

  // Render sentiment badge
  const renderSentimentBadge = (name) => {
    if (!name) {
      return <span className="record-badge badge-unclassified">Unclassified</span>;
    }
    const norm = name.toLowerCase();
    if (norm === 'positive') {
      return <span className="record-badge badge-sentiment-positive">Positive</span>;
    }
    if (norm === 'neutral') {
      return <span className="record-badge badge-sentiment-neutral">Neutral</span>;
    }
    if (norm === 'negative') {
      return <span className="record-badge badge-sentiment-negative">Negative</span>;
    }
    return <span className="record-badge badge-unclassified">{name}</span>;
  };

  // Render priority badge
  const renderPriorityBadge = (level) => {
    if (!level) {
      return <span className="record-badge badge-unclassified">Unclassified</span>;
    }
    const norm = level.toLowerCase();
    let badgeClass = 'badge-unclassified';
    if (norm === 'high') badgeClass = 'badge-priority-high';
    else if (norm === 'medium') badgeClass = 'badge-priority-medium';
    else if (norm === 'low') badgeClass = 'badge-priority-low';

    return <span className={`record-badge ${badgeClass}`}>{level}</span>;
  };

  return (
    <div
      className="detail-modal-backdrop"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="detail-modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="feedback-detail-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="detail-modal-header">
          <div className="detail-header-title-group">
            <h3 id="feedback-detail-title" className="detail-modal-title">Feedback Details</h3>
            <span className="detail-record-id-pill">Record #{record.id}</span>
          </div>
          <button
            type="button"
            className="detail-close-btn"
            onClick={onClose}
            aria-label="Close feedback details"
          >
            &times;
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="detail-modal-body">
          {/* 1. Original Feedback */}
          <section className="detail-section" aria-label="Original Feedback">
            <h4 className="detail-section-title">Original Feedback</h4>
            <div className="detail-feedback-box">
              <p className="detail-feedback-text">{record.feedback_text}</p>
            </div>
          </section>

          {/* 2. Processed Text */}
          <section className="detail-section" aria-label="Preprocessed Feedback">
            <h4 className="detail-section-title">Processed Text</h4>
            <div className="detail-preprocessed-box">
              {record.clean_text ? (
                <p className="detail-clean-text">{record.clean_text}</p>
              ) : (
                <p className="detail-placeholder-text">Not available</p>
              )}
            </div>
          </section>

          {/* 3. Metadata Grid */}
          <section className="detail-section" aria-label="Submission Metadata">
            <h4 className="detail-section-title">Submission Metadata</h4>
            <div className="detail-meta-grid">
              <div className="meta-card">
                <span className="meta-label">Department</span>
                <span className="meta-val">{record.department || 'Not provided'}</span>
              </div>
              <div className="meta-card">
                <span className="meta-label">Semester</span>
                <span className="meta-val">{record.semester || 'Not provided'}</span>
              </div>
              <div className="meta-card">
                <span className="meta-label">Submitted</span>
                <span className="meta-val">{formatTimestamp(record.created_at)}</span>
              </div>
            </div>
          </section>

          {/* 4. Intelligence Grid: Sentiment & Category & Priority */}
          <div className="detail-intelligence-grid">
            {/* Sentiment Analysis */}
            <section className="detail-card" aria-label="Sentiment Analysis">
              <div className="detail-card-header">
                <h4 className="detail-card-title">Sentiment Analysis</h4>
              </div>
              <div className="detail-card-content">
                <div className="intelligence-row">
                  <span className="intelligence-label">Sentiment</span>
                  {renderSentimentBadge(record.sentiment_name)}
                </div>
                <div className="intelligence-row">
                  <span className="intelligence-label">Label</span>
                  <span className="mono-value">
                    {record.sentiment_label != null ? record.sentiment_label : '—'}
                  </span>
                </div>
                <div className="intelligence-row">
                  <span className="intelligence-label">Confidence</span>
                  <span className="mono-value">
                    {formatConfidence(record.sentiment_confidence)}
                  </span>
                </div>
              </div>
            </section>

            {/* Category Analysis */}
            <section className="detail-card" aria-label="Category Analysis">
              <div className="detail-card-header">
                <h4 className="detail-card-title">Category Analysis</h4>
              </div>
              <div className="detail-card-content">
                <div className="intelligence-row">
                  <span className="intelligence-label">Category</span>
                  <span className="category-value">
                    {record.category_name || <span className="unclassified-text">Unclassified</span>}
                  </span>
                </div>
                <div className="intelligence-row">
                  <span className="intelligence-label">Confidence</span>
                  <span className="mono-value">
                    {formatConfidence(record.category_confidence)}
                  </span>
                </div>
              </div>
            </section>

            {/* Priority Analysis */}
            <section className="detail-card priority-detail-card" aria-label="Priority Analysis">
              <div className="detail-card-header">
                <h4 className="detail-card-title">Priority Analysis</h4>
              </div>
              <div className="detail-card-content">
                <div className="intelligence-row">
                  <span className="intelligence-label">Priority Tier</span>
                  {renderPriorityBadge(record.priority_level)}
                </div>
                <div className="intelligence-row">
                  <span className="intelligence-label">Priority Score</span>
                  <span className="mono-value">
                    {record.priority_score != null ? `${record.priority_score} / 100` : '—'}
                  </span>
                </div>
                <div className="priority-reason-block">
                  <span className="intelligence-label">Reason</span>
                  <p className="priority-reason-text">
                    {record.priority_reason || 'Not available'}
                  </p>
                </div>
              </div>
            </section>
          </div>
        </div>

        {/* Footer */}
        <div className="detail-modal-footer">
          <button
            type="button"
            className="detail-done-btn"
            onClick={onClose}
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
}
