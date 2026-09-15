/**
 * CampusVoice Feedback Statistics API Service (Step 9.6)
 * 
 * Handles HTTP communication with the FastAPI backend endpoint:
 * - GET /api/v1/feedback/stats
 */

import { apiClient } from './apiClient';

/**
 * Fetches database-backed feedback statistics from the backend for the Admin Dashboard.
 * 
 * @param {string} [tokenOverride] - Optional JWT token override.
 * @returns {Promise<Object>} Structured statistics object matching FeedbackStatsResponse contract.
 * @throws {Error} User-friendly error message on failure.
 */
export async function getFeedbackStats(tokenOverride = null) {
  const options = tokenOverride ? { token: tokenOverride } : {};
  const data = await apiClient.get('/api/v1/feedback/stats', options);

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
}
