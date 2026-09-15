import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UserManagement from '../UserManagement';
import * as usersApi from '../../services/usersApi';
import * as AuthContext from '../../context/AuthContext';

describe('UserManagement Component', () => {
  const currentAdmin = { id: 1, username: 'admin', role: 'admin', is_active: true };

  const mockUsersList = [
    { id: 1, username: 'admin', role: 'admin', is_active: true, created_at: '2026-09-01T00:00:00Z' },
    { id: 2, username: 'student_jane', role: 'student', is_active: true, created_at: '2026-09-02T00:00:00Z' },
    { id: 3, username: 'inactive_student', role: 'student', is_active: false, created_at: '2026-09-03T00:00:00Z' },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
      user: currentAdmin,
      isAdmin: true,
      isAuthenticated: true,
    });
  });

  it('renders user list and displays "You" badge on current admin with disabled deactivation', async () => {
    vi.spyOn(usersApi, 'getUsers').mockResolvedValueOnce({
      items: mockUsersList,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<UserManagement />);

    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument();
      expect(screen.getByText('You')).toBeInTheDocument();
      expect(screen.getByText('student_jane')).toBeInTheDocument();
      expect(screen.getByText('inactive_student')).toBeInTheDocument();
    });

    // Check that admin's own deactivate button is disabled
    const adminRow = screen.getByText('admin').closest('tr');
    const deactivateBtn = adminRow.querySelector('.deactivate-action-btn');
    expect(deactivateBtn).toBeDisabled();
  });

  it('renders error banner and retry button when fetching users fails', async () => {
    const getUsersSpy = vi.spyOn(usersApi, 'getUsers')
      .mockRejectedValueOnce(new Error('Failed to load user accounts'))
      .mockResolvedValueOnce({
        items: mockUsersList,
        total: 3,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

    render(<UserManagement />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/unable to retrieve user accounts/i);
    });

    const retryBtn = screen.getByRole('button', { name: /retry/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByText('student_jane')).toBeInTheDocument();
    });

    expect(getUsersSpy).toHaveBeenCalledTimes(2);
  });

  it('opens Create User modal, creates user, and shows success banner', async () => {
    vi.spyOn(usersApi, 'getUsers').mockResolvedValue({
      items: mockUsersList,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    const createUserSpy = vi.spyOn(usersApi, 'createUser').mockResolvedValueOnce({
      id: 4,
      username: 'student_bob',
      role: 'student',
      is_active: true,
    });

    render(<UserManagement />);

    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument();
    });

    // Open create user modal
    const createBtn = screen.getByRole('button', { name: /create new user account/i });
    fireEvent.click(createBtn);

    expect(screen.getByRole('dialog', { name: /create new user/i })).toBeInTheDocument();

    const usernameInput = screen.getByPlaceholderText('e.g. student_john');
    const passwordInput = screen.getByPlaceholderText('Minimum 8 characters');

    await userEvent.type(usernameInput, 'student_bob');
    await userEvent.type(passwordInput, 'ValidSecret123!');

    const submitBtn = screen.getByRole('button', { name: /^create user$/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createUserSpy).toHaveBeenCalledWith({
        username: 'student_bob',
        password: 'ValidSecret123!',
        role: 'student',
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/created successfully/i)).toBeInTheDocument();
    });
  });

  it('displays error banner inside Create User modal when username already exists (409 conflict)', async () => {
    vi.spyOn(usersApi, 'getUsers').mockResolvedValue({
      items: mockUsersList,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    const conflictErr = new Error('That username is already in use.');
    conflictErr.status = 409;
    vi.spyOn(usersApi, 'createUser').mockRejectedValueOnce(conflictErr);

    render(<UserManagement />);

    await waitFor(() => {
      expect(screen.getByText('student_jane')).toBeInTheDocument();
    });

    const createBtn = screen.getByRole('button', { name: /create new user account/i });
    fireEvent.click(createBtn);

    await userEvent.type(screen.getByPlaceholderText('e.g. student_john'), 'admin');
    await userEvent.type(screen.getByPlaceholderText('Minimum 8 characters'), 'ValidSecret123!');

    fireEvent.click(screen.getByRole('button', { name: /^create user$/i }));

    await waitFor(() => {
      expect(screen.getByText(/already in use/i)).toBeInTheDocument();
    });

    // Modal must remain open so user can correct the input
    expect(screen.getByRole('dialog', { name: /create new user/i })).toBeInTheDocument();
  });

  it('opens Edit User modal with read-only username and updates user role', async () => {
    vi.spyOn(usersApi, 'getUsers').mockResolvedValue({
      items: mockUsersList,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    const updateUserSpy = vi.spyOn(usersApi, 'updateUser').mockResolvedValueOnce({
      id: 2,
      username: 'student_jane',
      role: 'admin',
      is_active: true,
    });

    render(<UserManagement />);

    await waitFor(() => {
      expect(screen.getByText('student_jane')).toBeInTheDocument();
    });

    const studentRow = screen.getByText('student_jane').closest('tr');
    const editBtn = studentRow.querySelector('.edit-action-btn');
    fireEvent.click(editBtn);

    expect(screen.getByRole('dialog', { name: /edit user/i })).toBeInTheDocument();

    // Username must be disabled / read-only
    const usernameField = screen.getByDisplayValue('student_jane');
    expect(usernameField).toBeDisabled();

    // Password reset input must be initially empty
    const passwordInput = screen.getByPlaceholderText(/leave blank to preserve current password/i);
    expect(passwordInput).toHaveValue('');

    // Change role to admin
    const roleSelect = screen.getByLabelText(/assigned role/i);
    fireEvent.change(roleSelect, { target: { value: 'admin' } });

    // Save changes
    const saveBtn = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(updateUserSpy).toHaveBeenCalledWith(2, {
        role: 'admin',
      });
    });
  });

  it('shows deactivation confirmation dialog and deactivates student user', async () => {
    vi.spyOn(usersApi, 'getUsers').mockResolvedValue({
      items: mockUsersList,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    const updateUserSpy = vi.spyOn(usersApi, 'updateUser').mockResolvedValueOnce({
      id: 2,
      username: 'student_jane',
      role: 'student',
      is_active: false,
    });

    render(<UserManagement />);

    await waitFor(() => {
      expect(screen.getByText('student_jane')).toBeInTheDocument();
    });

    const studentRow = screen.getByText('student_jane').closest('tr');
    const deactivateBtn = studentRow.querySelector('.deactivate-action-btn');
    fireEvent.click(deactivateBtn);

    // Confirmation dialog appears
    const confirmModal = screen.getByRole('dialog', { name: /confirm account deactivation/i });
    expect(confirmModal).toBeInTheDocument();
    expect(within(confirmModal).getByText(/are you sure you want to deactivate/i)).toBeInTheDocument();

    const confirmBtn = within(confirmModal).getByRole('button', { name: /deactivate user/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(updateUserSpy).toHaveBeenCalledWith(2, { isActive: false });
    });
  });
});
