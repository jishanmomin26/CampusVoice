import React, { useState, useEffect, useCallback } from 'react';
import { getFeedbackStats } from '../services/statsApi';
import {
  SentimentChart,
  PriorityChart,
  CategoryChart,
} from './DashboardCharts';
import FeedbackRecords from './FeedbackRecords';
import UserManagement from './UserManagement';
import { useAuth } from '../context/AuthContext';
import './AdminDashboard.css';

/**
 * AdminDashboard Component (Step 9.6 - Step 9.14.2)
 * 
 * Renders the foundation for the CampusVoice Admin Dashboard:
 * - Subnavigation tabs: Feedback Analytics, Feedback Records, User Management
 * - High-level summary cards (Total, Analyzed, Unclassified, High Priority)
 * - Sentiment breakdown with accessible CSS meters & Recharts
 * - Priority tiers breakdown
 * - Dynamically discovered category distribution (zero hardcoding)
 * - Feedback records table with filtering, search, export, and detail view
 * - User Management for provision, role assignment, and status control
 * - Interactive refresh capability and resilient error handling
 */
export default function AdminDashboard() {
  const { isAdmin } = useAuth();
  const [activeSection, setActiveSection] = useState('analytics'); // 'analytics' | 'records' | 'users'
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchStats = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const data = await getFeedbackStats();
      setStats(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message || 'Unable to load dashboard statistics. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchStats(false);
  }, [fetchStats]);

  const handleRefresh = () => {
    fetchStats(true);
  };

  // Helper for formatting percentage
  const calcPercent = (val, total) => {
    if (!total || total <= 0 || typeof val !== 'number') return '0.0%';
    return `${((val / total) * 100).toFixed(1)}%`;
  };

  // Helper for formatting last updated time
  const formatTime = (date) => {
    if (!date) return '';
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });
  };

  // Safe data accessors
  const total = stats?.total_feedback ?? 0;
  const analyzed = stats?.analyzed_feedback ?? 0;
  const unclassified = stats?.unclassified_feedback ?? 0;

  const sentiment = stats?.sentiment || {
    positive: 0,
    neutral: 0,
    negative: 0,
    unclassified: 0,
  };

  const priority = stats?.priority || {
    high: 0,
    medium: 0,
    low: 0,
    unclassified: 0,
  };

  const categories = stats?.categories || {};
  const categoryEntries = Object.entries(categories).sort(([, a], [, b]) => b - a);

  return (
    <div className="admin-dashboard" aria-label="Admin Dashboard Overview">
      {/* Dashboard Top Bar */}
      <div className="dashboard-topbar">
        <div className="dashboard-intro">
          <h2 className="dashboard-heading">
            {activeSection === 'analytics' && 'Feedback Statistics & Intelligence Overview'}
            {activeSection === 'records' && 'Student Feedback Records & Export'}
            {activeSection === 'users' && 'User Accounts & Access Management'}
          </h2>
          <p className="dashboard-description">
            {activeSection === 'analytics' && 'Live, database-backed aggregations across all student feedback submissions and machine learning predictions.'}
            {activeSection === 'records' && 'Search, filter, inspect full analysis details, and export student feedback datasets.'}
            {activeSection === 'users' && 'Provision student and administrator accounts, manage roles, and enforce security policies.'}
          </p>
        </div>

        {activeSection === 'analytics' && (
          <div className="dashboard-actions">
            {lastUpdated && (
              <span className="last-updated-text">
                Updated at {formatTime(lastUpdated)}
              </span>
            )}
            <button
              type="button"
              className="refresh-btn"
              onClick={handleRefresh}
              disabled={loading || refreshing}
              aria-label="Refresh feedback statistics"
              aria-busy={refreshing}
            >
              <span className={`refresh-icon ${refreshing ? 'spinning' : ''}`} aria-hidden="true">
                &#8635;
              </span>
              <span>{refreshing ? 'Refreshing...' : 'Refresh Data'}</span>
            </button>
          </div>
        )}
      </div>

      {/* Admin Subnav Navigation */}
      <nav className="admin-subnav" aria-label="Admin Dashboard Sections">
        <button
          type="button"
          id="subnav-analytics-btn"
          className={`subnav-btn ${activeSection === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveSection('analytics')}
          aria-current={activeSection === 'analytics' ? 'page' : undefined}
        >
          <span className="subnav-icon" aria-hidden="true">&#128202;</span>
          <span>Feedback Analytics</span>
        </button>

        <button
          type="button"
          id="subnav-records-btn"
          className={`subnav-btn ${activeSection === 'records' ? 'active' : ''}`}
          onClick={() => setActiveSection('records')}
          aria-current={activeSection === 'records' ? 'page' : undefined}
        >
          <span className="subnav-icon" aria-hidden="true">&#128221;</span>
          <span>Feedback Records</span>
        </button>

        {isAdmin && (
          <button
            type="button"
            id="subnav-users-btn"
            className={`subnav-btn ${activeSection === 'users' ? 'active' : ''}`}
            onClick={() => setActiveSection('users')}
            aria-current={activeSection === 'users' ? 'page' : undefined}
          >
            <span className="subnav-icon" aria-hidden="true">&#128101;</span>
            <span>User Management</span>
          </button>
        )}
      </nav>

      {/* 1. Analytics Subview */}
      {activeSection === 'analytics' && (
        <>
          {/* Error Alert State */}
          {error && (
        <div className="dashboard-error-banner" role="alert">
          <div className="error-message-row">
            <span className="error-alert-icon" aria-hidden="true">&#9888;</span>
            <div className="error-content">
              <strong className="error-title">Unable to Load Statistics</strong>
              <p className="error-detail">{error}</p>
            </div>
          </div>
          <button
            type="button"
            className="retry-btn"
            onClick={() => fetchStats(false)}
            disabled={loading || refreshing}
          >
            Retry
          </button>
        </div>
      )}

      {/* Initial Loading State */}
      {loading && !stats && (
        <div className="dashboard-loading-state" role="status" aria-live="polite">
          <div className="dashboard-spinner" aria-hidden="true"></div>
          <p className="loading-text">Loading dashboard statistics from database...</p>
        </div>
      )}

      {/* Main Statistics Content */}
      {stats && (
        <div className={`dashboard-content ${refreshing ? 'content-refreshing' : ''}`}>
          {/* 1. Summary KPI Cards */}
          <section className="kpi-grid" aria-label="Key Performance Indicators">
            {/* Total Feedback */}
            <div className="kpi-card">
              <div className="kpi-header">
                <span className="kpi-label">Total Submissions</span>
                <span className="kpi-badge total-badge">All Records</span>
              </div>
              <div className="kpi-value">{total}</div>
              <div className="kpi-footer">
                <span>Database row count</span>
              </div>
            </div>

            {/* Analyzed Feedback */}
            <div className="kpi-card">
              <div className="kpi-header">
                <span className="kpi-label">Analyzed Feedback</span>
                <span className="kpi-badge analyzed-badge">ML Processed</span>
              </div>
              <div className="kpi-value">{analyzed}</div>
              <div className="kpi-footer">
                <span>{calcPercent(analyzed, total)} of total feedback</span>
              </div>
            </div>

            {/* Unclassified Feedback */}
            <div className="kpi-card">
              <div className="kpi-header">
                <span className="kpi-label">Unclassified Feedback</span>
                <span className="kpi-badge unclassified-badge">Legacy / Pending</span>
              </div>
              <div className="kpi-value">{unclassified}</div>
              <div className="kpi-footer">
                <span>{calcPercent(unclassified, total)} of total feedback</span>
              </div>
            </div>

            {/* High Priority */}
            <div className="kpi-card highlight-card">
              <div className="kpi-header">
                <span className="kpi-label">High Priority</span>
                <span className="kpi-badge priority-high-badge">Immediate Action</span>
              </div>
              <div className="kpi-value high-priority-value">{priority.high}</div>
              <div className="kpi-footer">
                <span>{calcPercent(priority.high, total)} of all feedback</span>
              </div>
            </div>
          </section>

          {/* 2. Breakdown Sections (Sentiment & Priority Grid) */}
          <div className="breakdown-grid">
            {/* Sentiment Summary */}
            <section className="breakdown-card" aria-label="Sentiment Breakdown">
              <div className="breakdown-header">
                <h3 className="breakdown-title">Sentiment Distribution</h3>
                <span className="breakdown-subtitle">Model-classified polarity breakdown</span>
              </div>

              {/* Step 9.7: Sentiment Donut Chart */}
              <SentimentChart sentiment={sentiment} total={total} />

              <div className="stats-list">
                {/* Positive */}
                <div className="stat-row">
                  <div className="stat-info">
                    <span className="stat-badge sentiment-positive-badge">Positive</span>
                    <span className="stat-count">{sentiment.positive}</span>
                  </div>
                  <div className="meter-track" aria-hidden="true">
                    <div
                      className="meter-fill sentiment-positive-fill"
                      style={{ width: calcPercent(sentiment.positive, total) }}
                    ></div>
                  </div>
                  <div className="stat-meta">
                    <span>{calcPercent(sentiment.positive, total)} of all feedback</span>
                  </div>
                </div>

                {/* Neutral */}
                <div className="stat-row">
                  <div className="stat-info">
                    <span className="stat-badge sentiment-neutral-badge">Neutral</span>
                    <span className="stat-count">{sentiment.neutral}</span>
                  </div>
                  <div className="meter-track" aria-hidden="true">
                    <div
                      className="meter-fill sentiment-neutral-fill"
                      style={{ width: calcPercent(sentiment.neutral, total) }}
                    ></div>
                  </div>
                  <div className="stat-meta">
                    <span>{calcPercent(sentiment.neutral, total)} of all feedback</span>
                  </div>
                </div>

                {/* Negative */}
                <div className="stat-row">
                  <div className="stat-info">
                    <span className="stat-badge sentiment-negative-badge">Negative</span>
                    <span className="stat-count">{sentiment.negative}</span>
                  </div>
                  <div className="meter-track" aria-hidden="true">
                    <div
                      className="meter-fill sentiment-negative-fill"
                      style={{ width: calcPercent(sentiment.negative, total) }}
                    ></div>
                  </div>
                  <div className="stat-meta">
                    <span>{calcPercent(sentiment.negative, total)} of all feedback</span>
                  </div>
                </div>

                {/* Unclassified */}
                <div className="stat-row">
                  <div className="stat-info">
                    <span className="stat-badge sentiment-unclassified-badge">Unclassified</span>
                    <span className="stat-count">{sentiment.unclassified}</span>
                  </div>
                  <div className="meter-track" aria-hidden="true">
                    <div
                      className="meter-fill sentiment-unclassified-fill"
                      style={{ width: calcPercent(sentiment.unclassified, total) }}
                    ></div>
                  </div>
                  <div className="stat-meta">
                    <span>{calcPercent(sentiment.unclassified, total)} of all feedback</span>
                  </div>
                </div>
              </div>
            </section>

            {/* Priority Summary */}
            <section className="breakdown-card" aria-label="Priority Tiers Breakdown">
              <div className="breakdown-header">
                <h3 className="breakdown-title">Priority Tiers</h3>
                <span className="breakdown-subtitle">Deterministic urgency distribution</span>
              </div>

              {/* Step 9.7: Priority Bar Chart */}
              <PriorityChart priority={priority} total={total} />

              <div className="stats-list">
                {/* High */}
                <div className="stat-row">
                  <div className="stat-info">
                    <span className="stat-badge priority-high-badge">High</span>
                    <span className="stat-count">{priority.high}</span>
                  </div>
                  <div className="meter-track" aria-hidden="true">
                    <div
                      className="meter-fill priority-high-fill"
                      style={{ width: calcPercent(priority.high, total) }}
                    ></div>
                  </div>
                  <div className="stat-meta">
                    <span>{calcPercent(priority.high, total)} of all feedback</span>
                  </div>
                </div>

                {/* Medium */}
                <div className="stat-row">
                  <div className="stat-info">
                    <span className="stat-badge priority-medium-badge">Medium</span>
                    <span className="stat-count">{priority.medium}</span>
                  </div>
                  <div className="meter-track" aria-hidden="true">
                    <div
                      className="meter-fill priority-medium-fill"
                      style={{ width: calcPercent(priority.medium, total) }}
                    ></div>
                  </div>
                  <div className="stat-meta">
                    <span>{calcPercent(priority.medium, total)} of all feedback</span>
                  </div>
                </div>

                {/* Low */}
                <div className="stat-row">
                  <div className="stat-info">
                    <span className="stat-badge priority-low-badge">Low</span>
                    <span className="stat-count">{priority.low}</span>
                  </div>
                  <div className="meter-track" aria-hidden="true">
                    <div
                      className="meter-fill priority-low-fill"
                      style={{ width: calcPercent(priority.low, total) }}
                    ></div>
                  </div>
                  <div className="stat-meta">
                    <span>{calcPercent(priority.low, total)} of all feedback</span>
                  </div>
                </div>

                {/* Unclassified */}
                <div className="stat-row">
                  <div className="stat-info">
                    <span className="stat-badge priority-unclassified-badge">Unclassified</span>
                    <span className="stat-count">{priority.unclassified}</span>
                  </div>
                  <div className="meter-track" aria-hidden="true">
                    <div
                      className="meter-fill priority-unclassified-fill"
                      style={{ width: calcPercent(priority.unclassified, total) }}
                    ></div>
                  </div>
                  <div className="stat-meta">
                    <span>{calcPercent(priority.unclassified, total)} of all feedback</span>
                  </div>
                </div>
              </div>
            </section>
          </div>

          {/* 3. Dynamic Category Summary Section */}
          <section className="category-section" aria-label="Departmental and Topic Categories">
            <div className="category-section-header">
              <div>
                <h3 className="breakdown-title">Topic &amp; Departmental Categories</h3>
                <p className="breakdown-subtitle">
                  Dynamically aggregated from database records (zero hardcoded categories).
                </p>
              </div>
              <span className="category-count-pill">
                {categoryEntries.length} Active {categoryEntries.length === 1 ? 'Category' : 'Categories'}
              </span>
            </div>

            {categoryEntries.length === 0 ? (
              <div className="category-empty-state">
                <p>No categorized feedback records found in the database.</p>
              </div>
            ) : (
              <>
                {/* Step 9.7: Dynamic Category Horizontal Bar Chart */}
                <CategoryChart categories={categories} total={total} />

                <div className="categories-grid">
                {categoryEntries.map(([catName, count]) => (
                  <div key={catName} className="category-item-card">
                    <div className="category-item-header">
                      <span className="category-name-title">{catName}</span>
                      <span className="category-item-count">{count}</span>
                    </div>
                    <div className="meter-track" aria-hidden="true">
                      <div
                        className="meter-fill category-meter-fill"
                        style={{ width: calcPercent(count, total) }}
                      ></div>
                    </div>
                    <div className="category-item-meta">
                      <span>{calcPercent(count, total)} of all feedback</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
          </section>
        </div>
      )}
    </>
  )}

  {/* 2. Feedback Records Subview */}
  {activeSection === 'records' && (
    <FeedbackRecords categories={stats?.categories} />
  )}

  {/* 3. User Management Subview (Admin Only) */}
  {activeSection === 'users' && isAdmin && (
    <UserManagement />
  )}
</div>
);
}
