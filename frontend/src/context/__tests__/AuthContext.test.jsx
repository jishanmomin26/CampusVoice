import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import * as authApi from '../../services/authApi';
import * as apiClient from '../../services/apiClient';
import * as tokenStorage from '../../utils/tokenStorage';

describe('AuthContext & AuthProvider', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('A. initializes in unauthenticated state when no token is stored and does not call /auth/me', async () => {
    const getCurrentUserSpy = vi.spyOn(authApi, 'getCurrentUser');

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAdmin).toBe(false);
    expect(getCurrentUserSpy).not.toHaveBeenCalled();
  });

  it('B. restores session when valid token exists in storage', async () => {
    localStorage.setItem(tokenStorage.TOKEN_STORAGE_KEY, 'valid-test-token');

    const mockAdmin = { id: 1, username: 'test_admin', role: 'admin', is_active: true };
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValueOnce(mockAdmin);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(mockAdmin);
    expect(result.current.token).toBe('valid-test-token');
    expect(result.current.isAdmin).toBe(true);
  });

  it('C. handles invalid/expired stored token by purging token and clearing user', async () => {
    localStorage.setItem(tokenStorage.TOKEN_STORAGE_KEY, 'invalid-expired-token');
    const removeTokenSpy = vi.spyOn(tokenStorage, 'removeStoredToken');

    vi.spyOn(authApi, 'getCurrentUser').mockRejectedValueOnce(
      new apiClient.ApiError('Token has expired', 401)
    );

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(removeTokenSpy).toHaveBeenCalled();
  });

  it('D. sets isAdmin true for admin role', async () => {
    localStorage.setItem(tokenStorage.TOKEN_STORAGE_KEY, 'admin-token');
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValueOnce({
      id: 2,
      username: 'boss_admin',
      role: 'admin',
      is_active: true,
    });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAdmin).toBe(true);
  });

  it('E. sets isAdmin false for student role', async () => {
    localStorage.setItem(tokenStorage.TOKEN_STORAGE_KEY, 'student-token');
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValueOnce({
      id: 3,
      username: 'student_alex',
      role: 'student',
      is_active: true,
    });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.isAdmin).toBe(false);
  });

  it('F. login stores token and populates user state', async () => {
    const mockUser = { id: 10, username: 'new_login_user', role: 'admin', is_active: true };
    vi.spyOn(authApi, 'login').mockResolvedValueOnce({ access_token: 'new-jwt-123' });
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValueOnce(mockUser);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let loggedInProfile;
    await act(async () => {
      loggedInProfile = await result.current.login('new_login_user', 'fake-secret-pw');
    });

    expect(loggedInProfile).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.token).toBe('new-jwt-123');
    expect(result.current.isAdmin).toBe(true);
    expect(localStorage.getItem(tokenStorage.TOKEN_STORAGE_KEY)).toBe('new-jwt-123');
  });

  it('G. login failure does not store token or update user state', async () => {
    vi.spyOn(authApi, 'login').mockRejectedValueOnce(new Error('Invalid username or password'));

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await expect(
      act(async () => {
        await result.current.login('wrong_user', 'bad_pw');
      })
    ).rejects.toThrow('Invalid username or password');

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(localStorage.getItem(tokenStorage.TOKEN_STORAGE_KEY)).toBeNull();
  });

  it('H. logout removes stored token and resets user state', async () => {
    localStorage.setItem(tokenStorage.TOKEN_STORAGE_KEY, 'active-token');
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValueOnce({
      id: 5,
      username: 'active_admin',
      role: 'admin',
      is_active: true,
    });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(localStorage.getItem(tokenStorage.TOKEN_STORAGE_KEY)).toBeNull();
  });

  it('I. session expiration event clears auth state and sets sessionExpired true', async () => {
    localStorage.setItem(tokenStorage.TOKEN_STORAGE_KEY, 'will-expire-token');
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValueOnce({
      id: 8,
      username: 'admin_will_expire',
      role: 'admin',
      is_active: true,
    });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    act(() => {
      apiClient.notifyUnauthorized(new apiClient.ApiError('Session expired', 401));
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.sessionExpired).toBe(true);

    // clearSessionExpired resets the flag
    act(() => {
      result.current.clearSessionExpired();
    });
    expect(result.current.sessionExpired).toBe(false);
  });

  it('throws error when useAuth is consumed outside AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used within an AuthProvider');
  });
});
