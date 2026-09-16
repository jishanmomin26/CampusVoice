import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  apiRequest,
  apiClient,
  ApiError,
  onUnauthorized,
  notifyUnauthorized,
} from '../apiClient';
import { login } from '../authApi';
import {
  TOKEN_STORAGE_KEY,
  getStoredToken,
  setStoredToken,
  removeStoredToken,
  getAuthHeaders,
} from '../../utils/tokenStorage';
import { transformRecordToRow, EXPORT_HEADERS } from '../../utils/exportFeedback';

describe('Frontend Security & Session Hardening', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = global.fetch;
    global.fetch = vi.fn();
    localStorage.clear();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  describe('Token Storage & Session Lifecycle', () => {
    it('stores token in designated localStorage key and retrieves it accurately', () => {
      setStoredToken('test-access-token-xyz');
      expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBe('test-access-token-xyz');
      expect(getStoredToken()).toBe('test-access-token-xyz');
    });

    it('removes stored token cleanly upon logout without residue', () => {
      setStoredToken('to-be-purged-token');
      expect(getStoredToken()).toBe('to-be-purged-token');

      removeStoredToken();
      expect(getStoredToken()).toBeNull();
      expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    });

    it('omits Authorization header entirely when no token is present', () => {
      const headers = getAuthHeaders();
      expect(headers).toEqual({});
      expect(headers.Authorization).toBeUndefined();
    });

    it('injects Bearer token into Authorization header when stored', () => {
      setStoredToken('valid-token-123');
      const headers = getAuthHeaders();
      expect(headers.Authorization).toBe('Bearer valid-token-123');
    });
  });

  describe('401 Unauthorized & Session Expiration Concurrency', () => {
    it('clears stored token and broadcasts session expiration upon 401 response', async () => {
      setStoredToken('expired-token-abc');

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Authentication token has expired.' }),
      });

      const unauthorizedSpy = vi.fn();
      const unsubscribe = onUnauthorized(unauthorizedSpy);

      try {
        await expect(apiRequest('/api/v1/feedback/stats')).rejects.toThrow(ApiError);
        expect(unauthorizedSpy).toHaveBeenCalledTimes(1);
        expect(getStoredToken()).toBeNull();
      } finally {
        unsubscribe();
      }
    });

    it('prevents multiple rapid 401s from triggering alert storms via notification throttling', async () => {
      // Wait for any previous throttling timer to clear
      await new Promise((r) => setTimeout(r, 450));

      const unauthorizedSpy = vi.fn();
      const unsubscribe = onUnauthorized(unauthorizedSpy);

      const err = new ApiError('Session expired', 401);
      notifyUnauthorized(err);
      notifyUnauthorized(err);
      notifyUnauthorized(err);

      expect(unauthorizedSpy).toHaveBeenCalledTimes(1);
      unsubscribe();
    });

    it('does not trigger session-expired handler during login failure with bad credentials', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid username or password.' }),
      });

      const unauthorizedSpy = vi.fn();
      const unsubscribe = onUnauthorized(unauthorizedSpy);

      try {
        await expect(login('wrong_user', 'WrongPassword123!')).rejects.toThrow(
          'Invalid username or password.'
        );
        // Login endpoint uses skipAuthHandler: true; listener MUST NOT be notified
        expect(unauthorizedSpy).not.toHaveBeenCalled();
      } finally {
        unsubscribe();
      }
    });
  });

  describe('Sensitive Data Privacy & Export Safety', () => {
    it('ApiError instances never expose raw bearer tokens or authorization secrets', () => {
      const error = new ApiError('Invalid authentication credentials', 401, {
        detail: 'Authentication token has expired.',
      });

      expect(error.message).not.toContain('Bearer');
      expect(error.message).not.toContain('campusvoice-dev-secret');
      expect(JSON.stringify(error)).not.toContain('Bearer');
    });

    it('export transformation strictly excludes authentication tokens and password hashes', () => {
      const recordWithSecret = {
        id: 42,
        feedback_text: 'The library Wi-Fi connection is fast and reliable.',
        sentiment: 'Positive',
        category: 'Facilities',
        priority: 'Low',
        department: 'CS',
        semester: '4',
        created_at: '2026-09-15T12:00:00Z',
        // Injected unauthorized or accidental fields
        token: 'secret-token-should-never-export',
        access_token: 'secret-access-token',
        password_hash: '$2b$12$secretpasswordhashvalue',
      };

      const row = transformRecordToRow(recordWithSecret);
      expect(row).toHaveLength(EXPORT_HEADERS.length);

      // Verify none of the exported cells contain tokens or hashes
      for (const cell of row) {
        const strCell = String(cell);
        expect(strCell).not.toContain('secret-token-should-never-export');
        expect(strCell).not.toContain('secret-access-token');
        expect(strCell).not.toContain('$2b$12$');
      }
    });
  });
});
