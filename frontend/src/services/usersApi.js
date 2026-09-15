/**
 * CampusVoice User Management API Service (Step 9.14.2)
 * 
 * Handles administrative HTTP communication with FastAPI backend endpoints:
 * - GET   /api/v1/users
 * - GET   /api/v1/users/{user_id}
 * - POST  /api/v1/users
 * - PATCH /api/v1/users/{user_id}
 * 
 * Enforces:
 * - Safe URLSearchParams query construction (no manual unescaped string concat)
 * - Reuse of centralized apiClient and ApiError models
 * - Clean separation of payload construction (no empty string passwords sent on patch)
 */

import { apiClient } from './apiClient';

/**
 * Fetches paginated, filtered user accounts from PostgreSQL.
 * 
 * @param {Object} [options={}] - Query filter and pagination parameters.
 * @param {number} [options.page=1] - 1-indexed page number.
 * @param {number} [options.pageSize=20] - Number of items per page.
 * @param {string} [options.search] - Optional username search query.
 * @param {string} [options.role] - Role filter ('admin', 'student', or 'all').
 * @param {boolean|string} [options.isActive] - Status filter (true, false, 'active', 'inactive', or 'all').
 * @returns {Promise<Object>} Object matching UserListResponse schema ({ items, total, page, page_size, total_pages }).
 */
export async function getUsers({
  page = 1,
  pageSize = 20,
  search,
  role,
  isActive,
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

  if (role && typeof role === 'string' && role.trim() && role.toLowerCase() !== 'all') {
    params.append('role', role.trim().toLowerCase());
  }

  if (isActive !== undefined && isActive !== null && isActive !== 'all' && isActive !== '') {
    if (typeof isActive === 'boolean') {
      params.append('is_active', String(isActive));
    } else if (typeof isActive === 'string') {
      const norm = isActive.trim().toLowerCase();
      if (norm === 'active' || norm === 'true') {
        params.append('is_active', 'true');
      } else if (norm === 'inactive' || norm === 'false') {
        params.append('is_active', 'false');
      }
    }
  }

  const queryString = params.toString();
  const path = `/api/v1/users${queryString ? `?${queryString}` : ''}`;

  const data = await apiClient.get(path);

  // Defensive validation of response structure
  if (
    !data ||
    !Array.isArray(data.items) ||
    typeof data.total !== 'number' ||
    typeof data.page !== 'number' ||
    typeof data.page_size !== 'number' ||
    typeof data.total_pages !== 'number'
  ) {
    throw new Error('Received an unexpected response structure from the user management service.');
  }

  return data;
}

/**
 * Fetches detail for an individual user account.
 * 
 * @param {number|string} userId - Target user identifier.
 * @returns {Promise<Object>} User detail object ({ id, username, role, is_active, created_at }).
 */
export async function getUser(userId) {
  if (!userId) {
    throw new Error('User identifier is required.');
  }
  return await apiClient.get(`/api/v1/users/${encodeURIComponent(userId)}`);
}

/**
 * Creates a new user account.
 * 
 * @param {Object} payload - User creation data.
 * @param {string} payload.username - Username (trimmed, 1-100 characters).
 * @param {string} payload.password - Plaintext password (min 8 characters).
 * @param {string} [payload.role='student'] - Assigned role ('student' or 'admin').
 * @returns {Promise<Object>} Created user representation.
 */
export async function createUser({ username, password, role = 'student' }) {
  if (!username || !username.trim()) {
    throw new Error('Username is required.');
  }
  if (!password || password.length < 8) {
    throw new Error('Password must be at least 8 characters long.');
  }

  const body = {
    username: username.trim(),
    password,
    role: role || 'student',
  };

  return await apiClient.post('/api/v1/users', body);
}

/**
 * Updates an existing user account.
 * Only sends fields that are explicitly provided and non-empty.
 * 
 * @param {number|string} userId - Target user identifier.
 * @param {Object} payload - Fields to update.
 * @param {string} [payload.role] - Optional updated role.
 * @param {boolean} [payload.isActive] - Optional updated active status.
 * @param {string} [payload.password] - Optional new password (min 8 chars).
 * @returns {Promise<Object>} Updated user representation.
 */
export async function updateUser(userId, { role, isActive, password } = {}) {
  if (!userId) {
    throw new Error('User identifier is required.');
  }

  const body = {};

  if (role !== undefined && role !== null) {
    body.role = role;
  }

  if (isActive !== undefined && isActive !== null) {
    body.is_active = Boolean(isActive);
  }

  if (password && typeof password === 'string' && password.trim()) {
    if (password.trim().length < 8) {
      throw new Error('New password must be at least 8 characters long.');
    }
    body.password = password.trim();
  }

  if (Object.keys(body).length === 0) {
    throw new Error('At least one field must be provided to update.');
  }

  return await apiClient.patch(`/api/v1/users/${encodeURIComponent(userId)}`, body);
}
