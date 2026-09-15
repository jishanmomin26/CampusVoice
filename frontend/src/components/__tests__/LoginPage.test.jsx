import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginPage from '../LoginPage';
import * as AuthContext from '../../context/AuthContext';

describe('LoginPage Component', () => {
  const mockLogin = vi.fn();
  const mockOnSuccess = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
      login: mockLogin,
      user: null,
      token: null,
      isAuthenticated: false,
      isAdmin: false,
      isLoading: false,
    });
  });

  it('renders username and password fields with accessible labels and login button', () => {
    render(<LoginPage onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /return to student portal/i })).toBeInTheDocument();
  });

  it('validates empty fields and displays client validation alerts', async () => {
    render(<LoginPage onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    const submitBtn = screen.getByRole('button', { name: /sign in/i });

    // Submit with empty username
    fireEvent.click(submitBtn);
    expect(screen.getByRole('alert')).toHaveTextContent(/please enter your username/i);
    expect(mockLogin).not.toHaveBeenCalled();

    // Fill username, leave password empty
    const usernameInput = screen.getByLabelText(/username/i);
    await userEvent.type(usernameInput, 'admin_user');
    fireEvent.click(submitBtn);

    expect(screen.getByRole('alert')).toHaveTextContent(/please enter your password/i);
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('calls login with trimmed username and password on valid submit', async () => {
    mockLogin.mockResolvedValueOnce({ id: 1, username: 'admin_user', role: 'admin' });

    render(<LoginPage onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    await userEvent.type(screen.getByLabelText(/username/i), '  admin_user  ');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'fake-password-123');

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('admin_user', 'fake-password-123');
      expect(mockOnSuccess).toHaveBeenCalledWith({ id: 1, username: 'admin_user', role: 'admin' });
    });

    // Password input must be cleared from memory after successful login
    expect(screen.getByLabelText(/^password$/i)).toHaveValue('');
  });

  it('displays user-safe error alert when login fails', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials provided.'));

    render(<LoginPage onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    await userEvent.type(screen.getByLabelText(/username/i), 'admin_user');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'wrong-password');

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials provided.');
    });
  });

  it('toggles password visibility when toggle button is clicked', async () => {
    render(<LoginPage onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    const passwordInput = screen.getByLabelText(/^password$/i);
    const toggleBtn = screen.getByRole('button', { name: /show password/i });

    expect(passwordInput).toHaveAttribute('type', 'password');

    // Click toggle to show
    fireEvent.click(toggleBtn);
    expect(passwordInput).toHaveAttribute('type', 'text');
    expect(screen.getByRole('button', { name: /hide password/i })).toBeInTheDocument();

    // Click toggle to hide again
    fireEvent.click(screen.getByRole('button', { name: /hide password/i }));
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('executes onCancel callback when return button is clicked', () => {
    render(<LoginPage onSuccess={mockOnSuccess} onCancel={mockOnCancel} />);

    const cancelBtn = screen.getByRole('button', { name: /return to student portal/i });
    fireEvent.click(cancelBtn);

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });
});
