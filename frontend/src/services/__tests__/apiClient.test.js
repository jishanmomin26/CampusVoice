import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  apiRequest,
  apiClient,
  ApiError,
  onUnauthorized,
  notifyUnauthorized,
} from '../apiClient';
import * as tokenStorage from '../../utils/tokenStorage';

describe('apiClient & apiRequest', () => {
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

  it('constructs correct URL with normalized leading slash and Accept headers', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ status: 'success' }),
    });

    const result = await apiRequest('/api/v1/health');
    expect(result).toEqual({ status: 'success' });
    expect(global.fetch).toHaveBeenCalledTimes(1);

    const [calledUrl, calledOptions] = global.fetch.mock.calls[0];
    expect(calledUrl).toContain('/api/v1/health');
    expect(calledOptions.method).toBe('GET');
    expect(calledOptions.headers.Accept).toBe('application/json');
  });

  it('handles paths without leading slash properly', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    });

    await apiRequest('api/v1/test');
    const [calledUrl] = global.fetch.mock.calls[0];
    expect(calledUrl).toContain('/api/v1/test');
  });

  it('attaches Content-Type application/json when request body is present', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ id: 1 }),
    });

    await apiClient.post('/api/v1/feedback', { text: 'Great faculty' });
    const [, calledOptions] = global.fetch.mock.calls[0];
    expect(calledOptions.method).toBe('POST');
    expect(calledOptions.headers['Content-Type']).toBe('application/json');
    expect(calledOptions.body).toBe(JSON.stringify({ text: 'Great faculty' }));
  });

  it('supports semantic HTTP methods: get, post, put, patch, delete', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    });

    await apiClient.get('/test');
    expect(global.fetch.mock.calls[0][1].method).toBe('GET');

    await apiClient.post('/test', { a: 1 });
    expect(global.fetch.mock.calls[1][1].method).toBe('POST');

    await apiClient.put('/test', { b: 2 });
    expect(global.fetch.mock.calls[2][1].method).toBe('PUT');

    await apiClient.patch('/test', { c: 3 });
    expect(global.fetch.mock.calls[3][1].method).toBe('PATCH');

    await apiClient.delete('/test');
    expect(global.fetch.mock.calls[4][1].method).toBe('DELETE');
  });

  it('injects Authorization Bearer header when token exists in storage', async () => {
    vi.spyOn(tokenStorage, 'getStoredToken').mockReturnValue('active-jwt-token');

    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: 123 }),
    });

    await apiRequest('/api/v1/admin/records');
    const [, calledOptions] = global.fetch.mock.calls[0];
    expect(calledOptions.headers.Authorization).toBe('Bearer active-jwt-token');
  });

  it('omits Authorization header when anonymous: true even if token exists', async () => {
    vi.spyOn(tokenStorage, 'getStoredToken').mockReturnValue('active-jwt-token');

    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: 123 }),
    });

    await apiRequest('/api/v1/public/feedback', { anonymous: true });
    const [, calledOptions] = global.fetch.mock.calls[0];
    expect(calledOptions.headers.Authorization).toBeUndefined();
  });

  it('uses explicit token override over stored token', async () => {
    vi.spyOn(tokenStorage, 'getStoredToken').mockReturnValue('stored-token');

    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: 123 }),
    });

    await apiRequest('/api/v1/admin/records', { token: 'override-token-777' });
    const [, calledOptions] = global.fetch.mock.calls[0];
    expect(calledOptions.headers.Authorization).toBe('Bearer override-token-777');
  });

  it('returns null for HTTP 204 No Content', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    const result = await apiRequest('/api/v1/logout');
    expect(result).toBeNull();
  });

  it('classifies network connection drops as isNetworkError', async () => {
    global.fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

    await expect(apiRequest('/api/v1/feedback')).rejects.toMatchObject({
      name: 'ApiError',
      status: 0,
      isNetworkError: true,
    });
  });

  it('classifies HTTP 401 Unauthorized, removes token, and fires unauthorized notification', async () => {
    const removeTokenSpy = vi.spyOn(tokenStorage, 'removeStoredToken');
    const listener = vi.fn();
    const unsubscribe = onUnauthorized(listener);

    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Token has expired' }),
    });

    await expect(apiRequest('/api/v1/admin/records')).rejects.toMatchObject({
      name: 'ApiError',
      status: 401,
      isAuthError: true,
      message: 'Token has expired',
    });

    expect(removeTokenSpy).toHaveBeenCalled();
    expect(listener).toHaveBeenCalledTimes(1);

    unsubscribe();
  });

  it('suppresses unauthorized listener notification when skipAuthHandler is true', async () => {
    const listener = vi.fn();
    const unsubscribe = onUnauthorized(listener);

    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Incorrect username or password' }),
    });

    await expect(apiRequest('/api/v1/auth/login', { skipAuthHandler: true })).rejects.toMatchObject({
      status: 401,
      isAuthError: true,
      message: 'Incorrect username or password',
    });

    expect(listener).not.toHaveBeenCalled();
    unsubscribe();
  });

  it('classifies HTTP 403 Forbidden', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 403,
      json: async () => ({ detail: 'Insufficient permissions' }),
    });

    await expect(apiRequest('/api/v1/admin/users')).rejects.toMatchObject({
      status: 403,
      isForbidden: true,
      message: 'Insufficient permissions',
    });
  });

  it('classifies HTTP 422 Unprocessable Entity validation errors', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ msg: 'Feedback text cannot be empty' }] }),
    });

    await expect(apiRequest('/api/v1/feedback', { method: 'POST' })).rejects.toMatchObject({
      status: 422,
      isValidationError: true,
      message: 'Feedback text cannot be empty',
    });
  });

  it('classifies HTTP 500+ Internal Server Error with user-safe message', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal database connection failed' }),
    });

    await expect(apiRequest('/api/v1/feedback')).rejects.toMatchObject({
      status: 500,
      isServerError: true,
      message: 'Something went wrong on the server. Please try again.',
    });
  });

  it('prevents duplicate concurrent 401 notifications', async () => {
    // Wait for any previous 400ms throttle timer to expire
    await new Promise((r) => setTimeout(r, 450));

    const listener = vi.fn();
    const unsubscribe = onUnauthorized(listener);

    const error = new ApiError('Unauthorized', 401);
    notifyUnauthorized(error);
    notifyUnauthorized(error); // Second immediate invocation should be throttled

    expect(listener).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it('does not perform automatic retry on 401 to prevent infinite loops', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Expired' }),
    });

    await expect(apiRequest('/api/v1/records')).rejects.toThrow();
    expect(global.fetch).toHaveBeenCalledTimes(1); // strictly 1 attempt, zero retries
  });
});
