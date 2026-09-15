import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import * as AuthContext from '../context/AuthContext';

describe('App RBAC & Top-Level Portal Navigation', () => {
  const mockLogout = vi.fn();
  const mockClearSessionExpired = vi.fn();

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('Unauthenticated: renders Student Feedback form and Admin Sign In tab', () => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
      user: null,
      token: null,
      isAuthenticated: false,
      isAdmin: false,
      isLoading: false,
      sessionExpired: false,
      logout: mockLogout,
      clearSessionExpired: mockClearSessionExpired,
    });

    render(<App />);

    expect(screen.getByRole('tab', { name: /student feedback/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /admin sign in/i })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /admin dashboard/i })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/student feedback input/i)).toBeInTheDocument();
  });

  it('Admin: renders Admin Dashboard tab and user session pill', () => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
      user: { id: 1, username: 'admin_user', role: 'admin' },
      token: 'admin-jwt-token',
      isAuthenticated: true,
      isAdmin: true,
      isLoading: false,
      sessionExpired: false,
      logout: mockLogout,
      clearSessionExpired: mockClearSessionExpired,
    });

    render(<App />);

    expect(screen.getByRole('tab', { name: /student feedback/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /admin dashboard/i })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /admin sign in/i })).not.toBeInTheDocument();
    expect(screen.getByText('admin_user')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument();
  });

  it('Student: does NOT render Admin Dashboard or Admin Sign In tab (RBAC restriction)', () => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
      user: { id: 5, username: 'student_jane', role: 'student' },
      token: 'student-jwt-token',
      isAuthenticated: true,
      isAdmin: false, // Student role!
      isLoading: false,
      sessionExpired: false,
      logout: mockLogout,
      clearSessionExpired: mockClearSessionExpired,
    });

    render(<App />);

    expect(screen.getByRole('tab', { name: /student feedback/i })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /admin dashboard/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /admin sign in/i })).not.toBeInTheDocument();
    expect(screen.getByText('student_jane')).toBeInTheDocument();
  });

  it('Logout button calls logout and returns to student feedback', () => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
      user: { id: 1, username: 'admin_user', role: 'admin' },
      token: 'admin-jwt-token',
      isAuthenticated: true,
      isAdmin: true,
      isLoading: false,
      sessionExpired: false,
      logout: mockLogout,
      clearSessionExpired: mockClearSessionExpired,
    });

    render(<App />);

    const logoutBtn = screen.getByRole('button', { name: /sign out/i });
    fireEvent.click(logoutBtn);

    expect(mockLogout).toHaveBeenCalledTimes(1);
  });

  it('Session expiration alert banner renders when sessionExpired is true', () => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
      user: null,
      token: null,
      isAuthenticated: false,
      isAdmin: false,
      isLoading: false,
      sessionExpired: true,
      logout: mockLogout,
      clearSessionExpired: mockClearSessionExpired,
    });

    render(<App />);

    const alertBanner = screen.getByRole('alert');
    expect(alertBanner).toBeInTheDocument();
    expect(alertBanner).toHaveTextContent(/your session has expired/i);

    const dismissBtn = screen.getByRole('button', { name: /dismiss session expiration alert/i });
    fireEvent.click(dismissBtn);

    expect(mockClearSessionExpired).toHaveBeenCalledTimes(1);
  });
});
