/**
 * CampusVoice Authentication API Service (Step 9.13.1)
 * 
 * Handles HTTP communication with the FastAPI backend authentication endpoints:
 * - POST /api/v1/auth/login
 * - GET  /api/v1/auth/me
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * Authenticates user credentials against the backend login endpoint.
 * 
 * @param {string} username - User login name.
 * @param {string} password - User plain-text password.
 * @returns {Promise<Object>} Object matching TokenResponse ({ access_token, token_type, role?, username? }).
 * @throws {Error} User-friendly error message on failure.
 */
export async function login(username, password) {
  if (!username || !username.trim()) {
    throw new Error('Please enter your username.');
  }

  if (!password) {
    throw new Error('Please enter your password.');
  }

  const endpoint = `${API_BASE_URL}/api/v1/auth/login`;

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        username: username.trim(),
        password: password,
      }),
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Invalid username or password.');
      }

      if (response.status === 422) {
        throw new Error('Please enter a valid username and password.');
      }

      if (response.status === 503) {
        throw new Error('Authentication service is temporarily unavailable. Please try again later.');
      }

      if (response.status >= 500) {
        throw new Error('An unexpected server error occurred during authentication. Please try again.');
      }

      throw new Error(`Authentication failed (HTTP ${response.status}). Please try again.`);
    }

    const data = await response.json();

    if (!data || !data.access_token) {
      throw new Error('Received an unexpected authentication response from the server.');
    }

    return data;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error(
        `Unable to connect to the CampusVoice authentication service. Please ensure the backend server is running at ${API_BASE_URL}`
      );
    }
    throw err;
  }
}

/**
 * Retrieves the authenticated user profile using a JWT access token.
 * 
 * @param {string} token - Signed JWT bearer access token.
 * @returns {Promise<Object>} Object matching CurrentUserResponse ({ id, username, role, is_active, created_at }).
 * @throws {Error} User-friendly error message on failure.
 */
export async function getCurrentUser(token) {
  if (!token || typeof token !== 'string') {
    throw new Error('Authentication token is required.');
  }

  const endpoint = `${API_BASE_URL}/api/v1/auth/me`;

  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token.trim()}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Your session has expired or is invalid. Please sign in again.');
      }

      if (response.status >= 500) {
        throw new Error('Server error occurred while validating user session.');
      }

      throw new Error(`Unable to verify user session (HTTP ${response.status}).`);
    }

    const data = await response.json();

    if (!data || typeof data.id !== 'number' || !data.username || !data.role) {
      throw new Error('Invalid user profile received from the authentication service.');
    }

    return data;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error(
        `Unable to connect to the CampusVoice service. Please verify server connectivity.`
      );
    }
    throw err;
  }
}
