import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  TOKEN_STORAGE_KEY,
  getStoredToken,
  setStoredToken,
  removeStoredToken,
  getAuthHeaders,
} from '../tokenStorage';

describe('tokenStorage Utility', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('stores a valid token in localStorage with whitespace trimmed', () => {
    const success = setStoredToken('  fake-jwt-token-12345  ');
    expect(success).toBe(true);
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBe('fake-jwt-token-12345');
  });

  it('rejects invalid, null, or empty tokens', () => {
    expect(setStoredToken(null)).toBe(false);
    expect(setStoredToken(undefined)).toBe(false);
    expect(setStoredToken('')).toBe(false);
    expect(setStoredToken(12345)).toBe(false);
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });

  it('retrieves an existing token from localStorage', () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, 'stored-test-token');
    expect(getStoredToken()).toBe('stored-test-token');
  });

  it('returns null when no token is present in localStorage', () => {
    expect(getStoredToken()).toBeNull();
  });

  it('removes stored token on removeStoredToken', () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, 'to-be-removed');
    removeStoredToken();
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    expect(getStoredToken()).toBeNull();
  });

  it('generates Authorization Bearer header when token is stored', () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, 'bearer-token-abc');
    const headers = getAuthHeaders();
    expect(headers).toEqual({ Authorization: 'Bearer bearer-token-abc' });
  });

  it('generates empty object when no token is stored', () => {
    const headers = getAuthHeaders();
    expect(headers).toEqual({});
  });

  it('prioritizes tokenOverride over stored token in getAuthHeaders', () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, 'stored-token');
    const headers = getAuthHeaders('override-token-xyz');
    expect(headers).toEqual({ Authorization: 'Bearer override-token-xyz' });
  });

  it('handles localStorage errors gracefully without throwing', () => {
    const getItemSpy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('Storage access blocked');
    });
    expect(getStoredToken()).toBeNull();
    getItemSpy.mockRestore();

    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    expect(setStoredToken('test-token')).toBe(false);
    setItemSpy.mockRestore();
  });
});
