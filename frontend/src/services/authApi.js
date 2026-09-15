/**
 * CampusVoice Authentication API Service (Step 9.13.1)
 * 
 * Handles HTTP communication with the FastAPI backend authentication endpoints:
 * - POST /api/v1/auth/login
 * - GET  /api/v1/auth/me
 */

import { apiClient } from './apiClient';

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

  // Use skipAuthHandler: true so wrong credentials do not trigger session-expiration handlers
  const data = await apiClient.post(
    '/api/v1/auth/login',
    {
      username: username.trim(),
      password,
    },
    {
      anonymous: true,
      skipAuthHandler: true,
    }
  );

  if (!data || !data.access_token) {
    throw new Error('Received an unexpected authentication response from the server.');
  }

  return data;
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

  const data = await apiClient.get('/api/v1/auth/me', {
    token: token.trim(),
    skipAuthHandler: false,
  });

  if (!data || typeof data.id !== 'number' || !data.username || !data.role) {
    throw new Error('Invalid user profile received from the authentication service.');
  }

  return data;
}
