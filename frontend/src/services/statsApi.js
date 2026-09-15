/**
 * CampusVoice Feedback Statistics API Service (Step 9.6)
 * 
 * Handles HTTP communication with the FastAPI backend endpoint:
 * - GET /api/v1/feedback/stats
 */

import { getStoredToken } from '../utils/tokenStorage';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * Fetches database-backed feedback statistics from the backend for the Admin Dashboard.
 * 
 * @param {string} [tokenOverride] - Optional JWT token override.
 * @returns {Promise<Object>} Structured statistics object matching FeedbackStatsResponse contract.
 * @throws {Error} User-friendly error message on failure.
 */
export async function getFeedbackStats(tokenOverride = null) {
  const endpoint = `${API_BASE_URL}/api/v1/feedback/stats`;
  const token = tokenOverride || getStoredToken();

  const headers = {
    'Accept': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  };

  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Administrative authentication required (HTTP 401). Please sign in.');
      }

      if (response.status === 403) {
        throw new Error('Access denied (HTTP 403). Administrator privileges are required.');
      }

      if (response.status === 503) {
        throw new Error('Database statistics service is temporarily unavailable. Please try again later.');
      }

      if (response.status >= 500) {
        throw new Error('An unexpected server error occurred while retrieving statistics. Please try again.');
      }

      throw new Error(`Unable to load statistics (HTTP ${response.status}). Please try again.`);
    }

    const data = await response.json();

    // Defensive validation of expected response structure
    if (
      !data ||
      typeof data.total_feedback !== 'number' ||
      typeof data.analyzed_feedback !== 'number' ||
      typeof data.unclassified_feedback !== 'number' ||
      !data.sentiment ||
      !data.priority ||
      typeof data.categories !== 'object' ||
      data.categories === null
    ) {
      throw new Error('Received an unexpected response structure from the feedback statistics service.');
    }

    return data;
  } catch (err) {
    // Distinguish network connection failures from application errors
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error(
        `Unable to connect to the CampusVoice statistics service. Please ensure the backend server is running at ${API_BASE_URL}`
      );
    }
    throw err;
  }
}
