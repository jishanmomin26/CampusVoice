/**
 * CampusVoice Centralized API Client (Step 9.13.2)
 * 
 * Provides unified HTTP request dispatching, automatic Bearer token injection,
 * standardized ApiError classification, and centralized 401 session expiration handling.
 * 
 * Strict Security Guarantees:
 * - Tokens, passwords, and raw stack traces are never logged or exposed.
 * - Authorization headers are never logged to console.
 * - No automatic retry on 401 to prevent infinite request loops.
 */

import { getStoredToken, removeStoredToken } from '../utils/tokenStorage';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * Standardized API Error Representation
 */
export class ApiError extends Error {
  /**
   * @param {string} message - User-safe error description.
   * @param {number} status - HTTP status code (0 for network errors).
   * @param {Object} [options={}] - Additional error attributes.
   * @param {boolean} [options.isNetworkError=false] - Whether failure was due to network drop.
   * @param {any} [options.detail=null] - Optional sanitized detail from response.
   */
  constructor(message, status = 0, { isNetworkError = false, detail = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.isAuthError = status === 401;
    this.isForbidden = status === 403;
    this.isValidationError = status === 422;
    this.isServerError = status >= 500;
    this.isNetworkError = isNetworkError;
    this.detail = detail;
  }
}

// Global listeners for 401 Unauthorized session expiration
const unauthorizedListeners = new Set();
let isHandlingUnauthorized = false;

/**
 * Subscribes a callback to receive notification when a 401 Unauthorized response occurs.
 * 
 * @param {Function} callback - Function invoked on session invalidation.
 * @returns {Function} Unsubscribe function.
 */
export function onUnauthorized(callback) {
  if (typeof callback === 'function') {
    unauthorizedListeners.add(callback);
  }
  return () => {
    unauthorizedListeners.delete(callback);
  };
}

/**
 * Notifies all registered listeners of a 401 session invalidation in a concurrency-safe manner.
 * 
 * @param {ApiError} error - The 401 error instance.
 */
export function notifyUnauthorized(error) {
  if (isHandlingUnauthorized) {
    return;
  }
  isHandlingUnauthorized = true;

  try {
    unauthorizedListeners.forEach((listener) => {
      try {
        listener(error);
      } catch (listenerErr) {
        console.warn('Error in unauthorized listener:', listenerErr);
      }
    });
  } finally {
    // Reset flag after microtask tick to allow subsequent authentications
    setTimeout(() => {
      isHandlingUnauthorized = false;
    }, 400);
  }
}

/**
 * Core HTTP Request Dispatcher
 * 
 * @param {string} path - API endpoint path (e.g. '/api/v1/feedback/stats').
 * @param {Object} [options={}] - Request configuration options.
 * @param {string} [options.method='GET'] - HTTP method.
 * @param {any} [options.body] - Request payload.
 * @param {Object} [options.headers] - Custom HTTP headers.
 * @param {string} [options.token] - Optional token override.
 * @param {boolean} [options.anonymous=false] - If true, omits Authorization header.
 * @param {boolean} [options.skipAuthHandler=false] - If true, suppresses 401 listener notification (e.g. for login).
 * @returns {Promise<any>} Parsed JSON response body.
 * @throws {ApiError} Structured API error.
 */
export async function apiRequest(path, options = {}) {
  const {
    method = 'GET',
    body,
    headers: customHeaders = {},
    token: tokenOverride,
    anonymous = false,
    skipAuthHandler = false,
  } = options;

  // Build target URL
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${API_BASE_URL}${normalizedPath}`;

  // Assemble headers
  const headers = {
    Accept: 'application/json',
    ...customHeaders,
  };

  // Attach Content-Type if a request body is present
  if (body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  // Inject Bearer token if not explicitly anonymous
  if (!anonymous) {
    const activeToken = tokenOverride || getStoredToken();
    if (activeToken) {
      headers.Authorization = `Bearer ${activeToken.trim()}`;
    }
  }

  let response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
    });
  } catch (fetchErr) {
    // Distinguish network connection failures from server responses
    throw new ApiError('Unable to connect to the server. Please check your network connection.', 0, {
      isNetworkError: true,
    });
  }

  // Handle successful responses
  if (response.ok) {
    // For 204 No Content
    if (response.status === 204) {
      return null;
    }

    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  // Parse error details safely without leaking raw exceptions
  let responseDetail = null;
  try {
    const errorJson = await response.json();
    if (errorJson && errorJson.detail) {
      if (typeof errorJson.detail === 'string') {
        responseDetail = errorJson.detail;
      } else if (Array.isArray(errorJson.detail) && errorJson.detail[0]?.msg) {
        responseDetail = errorJson.detail[0].msg;
      }
    }
  } catch {
    // Response was not JSON; use null
  }

  // 1. Handle HTTP 401 Unauthorized (Session Expired / Invalid)
  if (response.status === 401) {
    const authMessage = responseDetail || 'Your session has expired. Please sign in again.';
    const apiError = new ApiError(authMessage, 401, { detail: responseDetail });

    if (!skipAuthHandler) {
      // Purge invalid token and notify auth state
      removeStoredToken();
      notifyUnauthorized(apiError);
    }

    throw apiError;
  }

  // 2. Handle HTTP 403 Forbidden (Insufficient Role Permissions)
  if (response.status === 403) {
    const forbiddenMessage = responseDetail || 'You do not have permission to access this area.';
    throw new ApiError(forbiddenMessage, 403, { detail: responseDetail });
  }

  // 3. Handle HTTP 422 Unprocessable Entity (Validation Error)
  if (response.status === 422) {
    const validationMessage = responseDetail || 'The submitted data was invalid. Please check your input.';
    throw new ApiError(validationMessage, 422, { detail: responseDetail });
  }

  // 4. Handle HTTP 503 Service Unavailable
  if (response.status === 503) {
    const unavailableMessage = responseDetail || 'The service is temporarily unavailable. Please try again later.';
    throw new ApiError(unavailableMessage, 503, { detail: responseDetail });
  }

  // 5. Handle HTTP 500+ Internal Server Error
  if (response.status >= 500) {
    throw new ApiError('Something went wrong on the server. Please try again.', response.status, {
      detail: responseDetail,
    });
  }

  // 6. Generic Fallback
  const fallbackMessage = responseDetail || `Request failed with status code ${response.status}.`;
  throw new ApiError(fallbackMessage, response.status, { detail: responseDetail });
}

/**
 * Convenient API Client Wrapper with Semantic HTTP Methods
 */
export const apiClient = {
  request: apiRequest,

  get(path, options = {}) {
    return apiRequest(path, { ...options, method: 'GET' });
  },

  post(path, body, options = {}) {
    return apiRequest(path, { ...options, method: 'POST', body });
  },

  put(path, body, options = {}) {
    return apiRequest(path, { ...options, method: 'PUT', body });
  },

  patch(path, body, options = {}) {
    return apiRequest(path, { ...options, method: 'PATCH', body });
  },

  delete(path, options = {}) {
    return apiRequest(path, { ...options, method: 'DELETE' });
  },
};
