/**
 * CampusVoice Feedback Records API Service (Step 9.9)
 * 
 * Handles HTTP communication with the FastAPI backend endpoint:
 * - GET /api/v1/feedback/records
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

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
  const endpoint = `${API_BASE_URL}/api/v1/feedback/records${queryString ? `?${queryString}` : ''}`;

  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 422) {
        let message = 'Invalid filter or pagination parameters provided.';
        try {
          const errBody = await response.json();
          if (errBody.detail) {
            if (typeof errBody.detail === 'string') {
              message = errBody.detail;
            } else if (Array.isArray(errBody.detail) && errBody.detail[0]?.msg) {
              message = errBody.detail[0].msg;
            }
          }
        } catch {
          // Fall back to friendly default
        }
        throw new Error(message);
      }

      if (response.status === 503) {
        throw new Error('Feedback records service is temporarily unavailable. Please try again later.');
      }

      if (response.status >= 500) {
        throw new Error('An unexpected server error occurred while retrieving feedback records. Please try again.');
      }

      throw new Error(`Unable to load feedback records (HTTP ${response.status}). Please try again.`);
    }

    const data = await response.json();

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
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error(
        `Unable to connect to the CampusVoice records service. Please ensure the backend server is running at ${API_BASE_URL}`
      );
    }
    throw err;
  }
}
