import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { getFeedbackRecords } from '../services/recordsApi';
import FeedbackRecordDetail from './FeedbackRecordDetail';
import './FeedbackRecords.css';

/**
 * FeedbackRecords Component (Step 9.9)
 * 
 * Renders the Feedback Records Management section for the Admin Dashboard:
 * - Server-side search by keyword in feedback text (debounced)
 * - Dynamic filtering by sentiment, category, and priority
 * - Server-side pagination with page size control
 * - Responsive table with badges, confidence scores, and local timestamps
 * - Safe NULL handling for legacy records
 * - Dedicated loading, error, retry, and empty states
 */
export default function FeedbackRecords({ categories }) {
  // Data and pagination state
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(0);

  // Selected record for full detail view (Step 9.10)
  const [selectedRecord, setSelectedRecord] = useState(null);

  // Status state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter state
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sentiment, setSentiment] = useState('all');
  const [category, setCategory] = useState('all');
  const [priority, setPriority] = useState('all');

  // Debounce search input by 350ms
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
    }, 350);
    return () => clearTimeout(handler);
  }, [search]);

  // Extract dynamic category names from prop (derived from stats API)
  const categoryOptions = useMemo(() => {
    if (!categories) return [];
    if (Array.isArray(categories)) return categories;
    if (typeof categories === 'object') {
      return Object.keys(categories).sort();
    }
    return [];
  }, [categories]);

  // Check if any filter is active
  const hasActiveFilters = Boolean(
    debouncedSearch.trim() ||
    sentiment !== 'all' ||
    category !== 'all' ||
    priority !== 'all'
  );

  // Fetch records from server-side API
  const fetchRecords = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getFeedbackRecords({
        page,
        pageSize,
        search: debouncedSearch.trim() || undefined,
        sentiment: sentiment !== 'all' ? sentiment : undefined,
        category: category !== 'all' ? category : undefined,
        priority: priority !== 'all' ? priority : undefined,
      });

      setRecords(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 0);
    } catch (err) {
      setError(err.message || 'Unable to load feedback records. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedSearch, sentiment, category, priority]);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  // Filter change handlers (always reset page to 1)
  const handleSearchChange = (e) => {
    setSearch(e.target.value);
    setPage(1);
  };

  const handleSentimentChange = (e) => {
    setSentiment(e.target.value);
    setPage(1);
  };

  const handleCategoryChange = (e) => {
    setCategory(e.target.value);
    setPage(1);
  };

  const handlePriorityChange = (e) => {
    setPriority(e.target.value);
    setPage(1);
  };

  const handlePageSizeChange = (e) => {
    setPageSize(Number(e.target.value));
    setPage(1);
  };

  const handleClearFilters = () => {
    setSearch('');
    setDebouncedSearch('');
    setSentiment('all');
    setCategory('all');
    setPriority('all');
    setPage(1);
  };

  // Helper formatting functions
  const formatConfidence = (val) => {
    if (typeof val !== 'number' || isNaN(val)) return '—';
    return `${(val * 100).toFixed(1)}%`;
  };

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
  const renderPriorityBadge = (level, score) => {
    if (!level) {
      return <span className="record-badge badge-unclassified">Unclassified</span>;
    }
    const norm = level.toLowerCase();
    let badgeClass = 'badge-unclassified';
    if (norm === 'high') badgeClass = 'badge-priority-high';
    else if (norm === 'medium') badgeClass = 'badge-priority-medium';
    else if (norm === 'low') badgeClass = 'badge-priority-low';

    return (
      <div className="priority-cell">
        <span className={`record-badge ${badgeClass}`}>{level}</span>
        {typeof score === 'number' && (
          <span className="priority-score-pill" title="Deterministic priority score">
            {score}/100
          </span>
        )}
      </div>
    );
  };

  return (
    <section className="feedback-records-section" aria-label="Feedback Records Management">
      {/* Section Header */}
      <div className="records-header">
        <div className="records-header-text">
          <h3 className="records-title">Feedback Records Management</h3>
          <p className="records-subtitle">
            Search, filter, and inspect individual student feedback submissions stored in PostgreSQL.
          </p>
        </div>
        <div className="records-header-meta">
          <span className="records-total-badge" aria-live="polite">
            {total} {total === 1 ? 'Record' : 'Records'} Matching
          </span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="records-toolbar" role="search" aria-label="Filter feedback records">
        {/* Keyword Search */}
        <div className="search-input-wrapper">
          <span className="search-icon" aria-hidden="true">&#128269;</span>
          <input
            id="feedback-search-input"
            type="text"
            className="search-input"
            placeholder="Search feedback..."
            value={search}
            onChange={handleSearchChange}
            aria-label="Search feedback text"
          />
          {search && (
            <button
              type="button"
              className="clear-search-btn"
              onClick={() => { setSearch(''); setDebouncedSearch(''); setPage(1); }}
              aria-label="Clear search input"
            >
              &times;
            </button>
          )}
        </div>

        {/* Filter Controls Group */}
        <div className="filter-controls-group">
          {/* Sentiment Filter */}
          <div className="filter-select-wrapper">
            <label htmlFor="sentiment-filter" className="filter-label">Sentiment:</label>
            <select
              id="sentiment-filter"
              className="filter-select"
              value={sentiment}
              onChange={handleSentimentChange}
              aria-label="Filter by sentiment"
            >
              <option value="all">All Sentiments</option>
              <option value="positive">Positive</option>
              <option value="neutral">Neutral</option>
              <option value="negative">Negative</option>
            </select>
          </div>

          {/* Priority Filter */}
          <div className="filter-select-wrapper">
            <label htmlFor="priority-filter" className="filter-label">Priority:</label>
            <select
              id="priority-filter"
              className="filter-select"
              value={priority}
              onChange={handlePriorityChange}
              aria-label="Filter by priority"
            >
              <option value="all">All Priorities</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Category Filter (Dynamic) */}
          <div className="filter-select-wrapper">
            <label htmlFor="category-filter" className="filter-label">Category:</label>
            <select
              id="category-filter"
              className="filter-select"
              value={category}
              onChange={handleCategoryChange}
              aria-label="Filter by category"
            >
              <option value="all">All Categories</option>
              {categoryOptions.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          {/* Clear Filters Button */}
          {hasActiveFilters && (
            <button
              type="button"
              className="clear-filters-btn"
              onClick={handleClearFilters}
              aria-label="Clear all active filters"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Error Alert State */}
      {error && (
        <div className="records-error-banner" role="alert">
          <div className="records-error-content">
            <span className="records-error-icon" aria-hidden="true">&#9888;</span>
            <div className="records-error-text">
              <strong>Unable to Retrieve Feedback Records</strong>
              <p>{error}</p>
            </div>
          </div>
          <button
            type="button"
            className="records-retry-btn"
            onClick={fetchRecords}
            disabled={loading}
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading State Overlay / Spinner */}
      {loading && (
        <div className="records-loading-indicator" role="status" aria-live="polite">
          <div className="records-spinner" aria-hidden="true"></div>
          <span>Loading feedback records from database...</span>
        </div>
      )}

      {/* Records Table */}
      {!error && (
        <div className="table-responsive-container">
          <table className="feedback-table" aria-label="Feedback records data table">
            <thead>
              <tr>
                <th scope="col" className="col-id">ID</th>
                <th scope="col" className="col-feedback">Feedback Message</th>
                <th scope="col" className="col-sentiment">Sentiment</th>
                <th scope="col" className="col-confidence">Sentiment Conf.</th>
                <th scope="col" className="col-category">Category</th>
                <th scope="col" className="col-confidence">Category Conf.</th>
                <th scope="col" className="col-priority">Priority</th>
                <th scope="col" className="col-submitted">Submitted</th>
                <th scope="col" className="col-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.length === 0 && !loading ? (
                <tr>
                  <td colSpan="9" className="empty-table-cell">
                    <div className="empty-records-state">
                      <span className="empty-icon" aria-hidden="true">&#128269;</span>
                      <p className="empty-primary-text">
                        {hasActiveFilters ? 'No feedback records match the active filters.' : 'No feedback records found.'}
                      </p>
                      {hasActiveFilters && (
                        <button
                          type="button"
                          className="empty-clear-btn"
                          onClick={handleClearFilters}
                        >
                          Clear Filters
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                records.map((record) => (
                  <tr key={record.id} className="feedback-row">
                    <td className="cell-id">#{record.id}</td>
                    <td className="cell-feedback">
                      <p className="feedback-text-main">{record.feedback_text}</p>
                      {(record.department || record.semester) && (
                        <div className="feedback-meta-sub">
                          {record.department && <span className="meta-dept">{record.department}</span>}
                          {record.department && record.semester && <span className="meta-sep">&bull;</span>}
                          {record.semester && <span className="meta-sem">{record.semester}</span>}
                        </div>
                      )}
                    </td>
                    <td className="cell-sentiment">
                      {renderSentimentBadge(record.sentiment_name)}
                    </td>
                    <td className="cell-confidence">
                      {formatConfidence(record.sentiment_confidence)}
                    </td>
                    <td className="cell-category">
                      {record.category_name ? (
                        <span className="category-text-label">{record.category_name}</span>
                      ) : (
                        <span className="unclassified-text">Unclassified</span>
                      )}
                    </td>
                    <td className="cell-confidence">
                      {formatConfidence(record.category_confidence)}
                    </td>
                    <td className="cell-priority">
                      {renderPriorityBadge(record.priority_level, record.priority_score)}
                    </td>
                    <td className="cell-submitted">
                      <span className="timestamp-text">{formatTimestamp(record.created_at)}</span>
                    </td>
                    <td className="cell-actions">
                      <button
                        type="button"
                        className="view-details-btn"
                        onClick={() => setSelectedRecord(record)}
                        aria-label={`View details for feedback #${record.id}`}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Footer */}
      <div className="records-pagination-bar" aria-label="Pagination Navigation">
        <div className="pagination-info" aria-live="polite">
          {total > 0 ? (
            <span>
              Showing page <strong>{page}</strong> of <strong>{totalPages || 1}</strong> &middot;{' '}
              <strong>{total}</strong> matching {total === 1 ? 'record' : 'records'}
            </span>
          ) : (
            <span>0 matching records</span>
          )}
        </div>

        <div className="pagination-controls">
          {/* Page Size Selector */}
          <div className="page-size-selector">
            <label htmlFor="page-size-select" className="page-size-label">Rows per page:</label>
            <select
              id="page-size-select"
              className="page-size-select"
              value={pageSize}
              onChange={handlePageSizeChange}
              disabled={loading}
              aria-label="Select number of rows per page"
            >
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
          </div>

          {/* Prev / Next Page Buttons */}
          <div className="page-nav-buttons">
            <button
              type="button"
              className="page-btn prev-btn"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              aria-label="Go to previous page"
            >
              &larr; Previous
            </button>

            <span className="current-page-indicator" aria-current="page">
              Page {page} of {totalPages || 1}
            </span>

            <button
              type="button"
              className="page-btn next-btn"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              aria-label="Go to next page"
            >
              Next &rarr;
            </button>
          </div>
        </div>
      </div>

      {/* Detail Modal View (Step 9.10) */}
      {selectedRecord && (
        <FeedbackRecordDetail
          record={selectedRecord}
          onClose={() => setSelectedRecord(null)}
        />
      )}
    </section>
  );
}
