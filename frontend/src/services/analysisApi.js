/**
 * CampusVoice Feedback Analysis API Service
 * 
 * Handles HTTP communication with the FastAPI backend endpoint:
 * POST /api/v1/feedback/analyze
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * Analyzes raw student feedback text via the CampusVoice ML intelligence pipeline.
 * 
 * @param {string} feedbackText - Raw student feedback message.
 * @returns {Promise<Object>} The structured feedback intelligence result.
 * @throws {Error} User-friendly error message on failure.
 */
export async function analyzeFeedback(feedbackText) {
  if (!feedbackText || typeof feedbackText !== 'string' || !feedbackText.trim()) {
    throw new Error('Please enter meaningful feedback before analyzing.');
  }

  const endpoint = `${API_BASE_URL}/api/v1/feedback/analyze`;

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ feedback: feedbackText }),
    });

    if (!response.ok) {
      if (response.status === 422) {
        let message = 'Please enter meaningful feedback before analyzing.';
        try {
          const errorData = await response.json();
          if (errorData.detail && Array.isArray(errorData.detail)) {
            const firstMsg = errorData.detail[0]?.msg;
            if (firstMsg && !firstMsg.includes('Value error,')) {
              message = firstMsg;
            }
          }
        } catch {
          // Fall back to default friendly message
        }
        throw new Error(message);
      }

      if (response.status === 503) {
        throw new Error('Feedback analysis models are temporarily unavailable. Please try again later.');
      }

      if (response.status >= 500) {
        throw new Error('An unexpected server error occurred while analyzing your feedback. Please try again.');
      }

      throw new Error(`Request failed with status code ${response.status}. Please try again.`);
    }

    const data = await response.json();

    // Verify response structure matches expected contract
    if (!data || !data.sentiment || !data.category || !data.priority) {
      throw new Error('Received an unexpected response format from the analysis service.');
    }

    return data;
  } catch (err) {
    // Distinguish network connection failures from application errors
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error(
        'Unable to connect to the CampusVoice analysis service. Please ensure the backend server is running at ' +
        API_BASE_URL
      );
    }
    throw err;
  }
}
