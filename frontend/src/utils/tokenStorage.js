/**
 * CampusVoice Token Storage Utility (Step 9.13.1)
 * 
 * Provides safe, centralized access to browser localStorage for the JWT access token.
 * Strictly avoids storing passwords, sensitive user claims, or credentials.
 */

export const TOKEN_STORAGE_KEY = 'campusvoice_access_token';

/**
 * Retrieves the stored JWT access token from localStorage.
 * 
 * @returns {string|null} The stored JWT token, or null if absent or unavailable.
 */
export function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch (err) {
    console.warn('Unable to read authentication token from localStorage:', err);
    return null;
  }
}

/**
 * Persists the JWT access token in localStorage.
 * 
 * @param {string} token - Signed JWT bearer access token.
 * @returns {boolean} True if successfully stored, false otherwise.
 */
export function setStoredToken(token) {
  if (!token || typeof token !== 'string') {
    return false;
  }

  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token.trim());
    return true;
  } catch (err) {
    console.error('Unable to save authentication token to localStorage:', err);
    return false;
  }
}

/**
 * Removes the stored JWT access token from localStorage upon logout or session invalidation.
 */
export function removeStoredToken() {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (err) {
    console.warn('Unable to remove authentication token from localStorage:', err);
  }
}

/**
 * Constructs an Authorization header object with the Bearer token if available.
 * 
 * @param {string} [tokenOverride] - Optional token override.
 * @returns {Object} Headers object containing Authorization if token exists, or empty object.
 */
export function getAuthHeaders(tokenOverride = null) {
  const token = tokenOverride || getStoredToken();
  if (token) {
    return {
      Authorization: `Bearer ${token}`,
    };
  }
  return {};
}
