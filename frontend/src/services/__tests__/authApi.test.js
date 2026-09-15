import { describe, it, expect, beforeEach, vi } from 'vitest';
import { login, getCurrentUser } from '../authApi';
import { apiClient } from '../apiClient';

describe('authApi Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('calls POST /api/v1/auth/login with OAuth2 password request body and skipAuthHandler', async () => {
    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
      access_token: 'mock-access-token-123',
      token_type: 'bearer',
    });

    const result = await login('test-admin-user', 'fake-password-123');

    expect(postSpy).toHaveBeenCalledTimes(1);
    const [calledPath, calledBody, calledOptions] = postSpy.mock.calls[0];

    expect(calledPath).toBe('/api/v1/auth/login');
    expect(calledBody).toEqual({
      username: 'test-admin-user',
      password: 'fake-password-123',
    });
    expect(calledOptions.anonymous).toBe(true);
    expect(calledOptions.skipAuthHandler).toBe(true);

    expect(result).toEqual({
      access_token: 'mock-access-token-123',
      token_type: 'bearer',
    });
  });

  it('calls GET /api/v1/auth/me with Bearer token override', async () => {
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      id: 42,
      username: 'test-admin-user',
      role: 'admin',
      is_active: true,
    });

    const result = await getCurrentUser('test-bearer-token');

    expect(getSpy).toHaveBeenCalledTimes(1);
    const [calledPath, calledOptions] = getSpy.mock.calls[0];

    expect(calledPath).toBe('/api/v1/auth/me');
    expect(calledOptions.token).toBe('test-bearer-token');

    expect(result).toEqual({
      id: 42,
      username: 'test-admin-user',
      role: 'admin',
      is_active: true,
    });
  });

  it('propagates authentication errors safely', async () => {
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new Error('Invalid username or password'));

    await expect(login('unknown-user', 'wrong-password')).rejects.toThrow('Invalid username or password');
  });
});
