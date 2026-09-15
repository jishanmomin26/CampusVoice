/**
 * CampusVoice Feedback Records API Service (Step 9.9)
 * 
 * Handles HTTP communication with the FastAPI backend endpoint:
 * - GET /api/v1/feedback/records
 */

import { apiClient } from './apiClient';

/**
 * Fetches paginated, filtered feedback records from the PostgreSQL database.
 * 
 * @param {Object} [options={}] - Query filter and pagination options.
 * @param {number} [options.page=1] - 1-indexed page number.
 * @param {number} [options.pageSize=10] - Number of items per page.
 * @param {string} [options.search] - Case-insensitive search keyword for feedback text.
 * @param {string} [options.sentiment] - Filter by sentiment ('positive', 'neutral', 'negative').
 * @param {string} [options.category] - Dynamic category filter.
 * @param {string} [options.priority] - Filter by priority tier ('high', 'medium', 'low').
 * @param {string} [options.token] - Optional JWT bearer token override.
 * @returns {Promise<Object>} Object matching FeedbackRecordsResponse schema ({ items, total, page, page_size, total_pages }).
 * @throws {Error} User-friendly error message on failure.
 */
export async function getFeedbackRecords({
  page = 1,
  pageSize = 10,
  search,
  sentiment,
  category,
  priority,
  token: tokenOverride,
} = {}) {
  const params = new URLSearchParams();

  if (page && Number(page) > 0) {
    params.append('page', String(page));
  }

  if (pageSize && Number(pageSize) > 0) {
    params.append('page_size', String(pageSize));
  }

  if (search && typeof search === 'string' && search.trim()) {
    params.append('search', search.trim());
  }

  if (sentiment && typeof sentiment === 'string' && sentiment.trim() && sentiment.toLowerCase() !== 'all') {
    params.append('sentiment', sentiment.trim().toLowerCase());
  }

  if (category && typeof category === 'string' && category.trim() && category.toLowerCase() !== 'all') {
    params.append('category', category.trim());
  }

  if (priority && typeof priority === 'string' && priority.trim() && priority.toLowerCase() !== 'all') {
    params.append('priority', priority.trim().toLowerCase());
  }

  const queryString = params.toString();
  const path = `/api/v1/feedback/records${queryString ? `?${queryString}` : ''}`;
  const options = tokenOverride ? { token: tokenOverride } : {};

  const data = await apiClient.get(path, options);

  // Defensive validation of expected response structure
  if (
    !data ||
    !Array.isArray(data.items) ||
    typeof data.total !== 'number' ||
    typeof data.page !== 'number' ||
    typeof data.page_size !== 'number' ||
    typeof data.total_pages !== 'number'
  ) {
    throw new Error('Received an unexpected response structure from the feedback records service.');
  }

  return data;
}

/**
 * Sequentially fetches all feedback records matching active filters across all pages (Step 9.11).
 * Respects backend maximum page_size constraint (100) and preserves deterministic newest-first ordering.
 * 
 * @param {Object} [filters={}] - Active search and categorization filters
 * @param {string} [filters.search] - Search keyword
 * @param {string} [filters.sentiment] - Sentiment filter
 * @param {string} [filters.category] - Category filter
 * @param {string} [filters.priority] - Priority filter
 * @param {Function} [onProgress] - Optional callback (currentPage, totalPages, loadedCount, totalExpected)
 * @returns {Promise<Array<Object>>} Array of all matching record objects
 */
export async function fetchAllMatchingFeedbackRecords(filters = {}, onProgress = null) {
  const EXPORT_PAGE_SIZE = 100;

  // Fetch first page to obtain total and total_pages
  const firstPageData = await getFeedbackRecords({
    page: 1,
    pageSize: EXPORT_PAGE_SIZE,
    search: filters.search,
    sentiment: filters.sentiment,
    category: filters.category,
    priority: filters.priority,
  });

  const total = firstPageData.total || 0;
  const totalPages = firstPageData.total_pages || 0;
  const allRecords = [...(firstPageData.items || [])];

  if (typeof onProgress === 'function') {
    onProgress(1, totalPages || 1, allRecords.length, total);
  }

  // Fetch subsequent pages sequentially if total_pages > 1
  if (totalPages > 1) {
    for (let p = 2; p <= totalPages; p++) {
      const pageData = await getFeedbackRecords({
        page: p,
        pageSize: EXPORT_PAGE_SIZE,
        search: filters.search,
        sentiment: filters.sentiment,
        category: filters.category,
        priority: filters.priority,
      });

      if (Array.isArray(pageData.items)) {
        allRecords.push(...pageData.items);
      }

      if (typeof onProgress === 'function') {
        onProgress(p, totalPages, allRecords.length, total);
      }
    }
  }

  return allRecords;
}

