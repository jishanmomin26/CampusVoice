import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getUsers, getUser, createUser, updateUser } from '../usersApi';
import { apiClient } from '../apiClient';

describe('usersApi Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('getUsers serializes pagination, search, role, and active status query parameters', async () => {
    const mockResponse = {
      items: [{ id: 1, username: 'admin', role: 'admin', is_active: true }],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValueOnce(mockResponse);

    const result = await getUsers({
      page: 1,
      pageSize: 20,
      search: 'admin',
      role: 'admin',
      isActive: true,
    });

    expect(getSpy).toHaveBeenCalledTimes(1);
    const [calledPath] = getSpy.mock.calls[0];

    expect(calledPath).toContain('/api/v1/users?');
    expect(calledPath).toContain('page=1');
    expect(calledPath).toContain('page_size=20');
    expect(calledPath).toContain('search=admin');
    expect(calledPath).toContain('role=admin');
    expect(calledPath).toContain('is_active=true');
    expect(result).toEqual(mockResponse);
  });

  it('getUsers safely encodes search terms with special characters', async () => {
    const mockResponse = { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 };
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValueOnce(mockResponse);

    await getUsers({ search: 'user & student' });
    const [calledPath] = getSpy.mock.calls[0];
    expect(calledPath).toContain('search=user+%26+student');
  });

  it('getUser calls GET /api/v1/users/{userId}', async () => {
    const mockUser = { id: 7, username: 'student_seven', role: 'student', is_active: true };
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValueOnce(mockUser);

    const result = await getUser(7);
    expect(getSpy).toHaveBeenCalledWith('/api/v1/users/7');
    expect(result).toEqual(mockUser);
  });

  it('getUser throws client validation error if userId is missing', async () => {
    await expect(getUser(null)).rejects.toThrow('User identifier is required.');
  });

  it('createUser validates inputs and posts payload to /api/v1/users', async () => {
    const createdUser = { id: 15, username: 'new_student', role: 'student', is_active: true };
    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValueOnce(createdUser);

    const result = await createUser({
      username: '  new_student  ',
      password: 'valid-secret-password-123',
      role: 'student',
    });

    expect(postSpy).toHaveBeenCalledWith('/api/v1/users', {
      username: 'new_student',
      password: 'valid-secret-password-123',
      role: 'student',
    });
    expect(result).toEqual(createdUser);
  });

  it('createUser throws validation error if username or password length is insufficient', async () => {
    await expect(createUser({ username: '', password: 'valid-secret-password' })).rejects.toThrow(
      'Username is required.'
    );
    await expect(createUser({ username: 'valid_user', password: 'short' })).rejects.toThrow(
      'Password must be at least 8 characters long.'
    );
  });

  it('updateUser sends PATCH request with only modified fields and omits empty password', async () => {
    const updatedUser = { id: 20, username: 'student_target', role: 'admin', is_active: false };
    const patchSpy = vi.spyOn(apiClient, 'patch').mockResolvedValueOnce(updatedUser);

    const result = await updateUser(20, {
      role: 'admin',
      isActive: false,
      password: '', // Empty password must be omitted!
    });

    expect(patchSpy).toHaveBeenCalledWith('/api/v1/users/20', {
      role: 'admin',
      is_active: false,
    });
    expect(result).toEqual(updatedUser);
  });

  it('updateUser attaches password when non-empty string is provided with >= 8 characters', async () => {
    const updatedUser = { id: 20, username: 'student_target', role: 'student', is_active: true };
    const patchSpy = vi.spyOn(apiClient, 'patch').mockResolvedValueOnce(updatedUser);

    await updateUser(20, {
      password: 'brand-new-secret-pw',
    });

    expect(patchSpy).toHaveBeenCalledWith('/api/v1/users/20', {
      password: 'brand-new-secret-pw',
    });
  });

  it('updateUser throws error if no fields are provided to update', async () => {
    await expect(updateUser(20, {})).rejects.toThrow('At least one field must be provided to update.');
  });
});
