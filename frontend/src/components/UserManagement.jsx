import React, { useState, useEffect, useCallback } from 'react';
import { getUsers, createUser, updateUser } from '../services/usersApi';
import { useAuth } from '../context/AuthContext';
import './UserManagement.css';

/**
 * UserManagement Component (Step 9.14.2)
 * 
 * Provides full administrative user management for the CampusVoice Admin Dashboard:
 * - Search by username with 350ms debounce
 * - Role and status filters with clear filters action
 * - Server-side pagination (10, 20, 50 rows per page)
 * - User list table with role/status badges and "(You)" indicator for active admin
 * - Create User modal dialog (with 409 conflict handling)
 * - Edit User modal dialog (read-only username, role, active status, optional password reset)
 * - Deactivation confirmation dialog
 * - Self-deactivation disabled with assistive tooltip
 * - Last-active-admin safe error handling
 * - Zero password leakage or persistence
 */
export default function UserManagement() {
  const { user: currentUser, isAdmin } = useAuth();

  // Data & pagination state
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(0);

  // Status & notifications
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Filters state
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  // Modal dialog states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    username: '',
    password: '',
    role: 'student',
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState(null);

  const [editUser, setEditUser] = useState(null);
  const [editForm, setEditForm] = useState({
    role: 'student',
    isActive: true,
    password: '',
  });
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState(null);

  const [deactivateTarget, setDeactivateTarget] = useState(null);
  const [deactivateLoading, setDeactivateLoading] = useState(false);
  const [deactivateError, setDeactivateError] = useState(null);

  // Debounce search input by 350ms
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
    }, 350);
    return () => clearTimeout(handler);
  }, [search]);

  // Check if any filter is active
  const hasActiveFilters = Boolean(
    debouncedSearch.trim() ||
    roleFilter !== 'all' ||
    statusFilter !== 'all'
  );

  // Fetch users from API
  const fetchUsers = useCallback(async () => {
    if (!isAdmin) return;

    setLoading(true);
    setError(null);

    try {
      const data = await getUsers({
        page,
        pageSize,
        search: debouncedSearch.trim() || undefined,
        role: roleFilter !== 'all' ? roleFilter : undefined,
        isActive: statusFilter !== 'all' ? statusFilter : undefined,
      });

      setUsers(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 0);
    } catch (err) {
      setError(err.message || 'Unable to load users. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [isAdmin, page, pageSize, debouncedSearch, roleFilter, statusFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Auto-dismiss success notification after 5 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => {
        setSuccessMessage(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // Handle global Escape key to dismiss any open modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (isCreateOpen) setIsCreateOpen(false);
        if (editUser) setEditUser(null);
        if (deactivateTarget) setDeactivateTarget(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCreateOpen, editUser, deactivateTarget]);

  // Filter change handlers (resets page to 1)
  const handleSearchChange = (e) => {
    setSearch(e.target.value);
    setPage(1);
  };

  const handleRoleFilterChange = (e) => {
    setRoleFilter(e.target.value);
    setPage(1);
  };

  const handleStatusFilterChange = (e) => {
    setStatusFilter(e.target.value);
    setPage(1);
  };

  const handlePageSizeChange = (e) => {
    setPageSize(Number(e.target.value));
    setPage(1);
  };

  const handleClearFilters = () => {
    setSearch('');
    setDebouncedSearch('');
    setRoleFilter('all');
    setStatusFilter('all');
    setPage(1);
  };

  // Helper formatting
  const formatTimestamp = (isoString) => {
    if (!isoString) return '—';
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) return '—';
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return '—';
    }
  };

  const isSelf = (targetUser) => {
    if (!currentUser || !targetUser) return false;
    if (currentUser.id && targetUser.id) {
      return Number(currentUser.id) === Number(targetUser.id);
    }
    return currentUser.username?.toLowerCase() === targetUser.username?.toLowerCase();
  };

  // Create User Handlers
  const handleOpenCreate = () => {
    setCreateForm({ username: '', password: '', role: 'student' });
    setCreateError(null);
    setIsCreateOpen(true);
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setCreateError(null);

    if (!createForm.username.trim()) {
      setCreateError('Username is required.');
      return;
    }
    if (!createForm.password || createForm.password.length < 8) {
      setCreateError('Password must be at least 8 characters long.');
      return;
    }

    setCreateLoading(true);
    try {
      const created = await createUser({
        username: createForm.username.trim(),
        password: createForm.password,
        role: createForm.role,
      });
      setIsCreateOpen(false);
      setSuccessMessage(`User '${created.username}' created successfully.`);
      fetchUsers();
    } catch (err) {
      if (err.status === 409) {
        setCreateError('That username is already in use.');
      } else {
        setCreateError(err.message || 'Failed to create user. Please check your inputs.');
      }
    } finally {
      setCreateLoading(false);
    }
  };

  // Edit User Handlers
  const handleOpenEdit = (target) => {
    setEditUser(target);
    setEditForm({
      role: target.role?.toLowerCase() || 'student',
      isActive: Boolean(target.is_active),
      password: '',
    });
    setEditError(null);
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    if (!editUser) return;
    setEditError(null);

    const payload = {};
    if (editForm.role !== editUser.role?.toLowerCase()) {
      payload.role = editForm.role;
    }
    if (editForm.isActive !== editUser.is_active) {
      payload.isActive = editForm.isActive;
    }
    if (editForm.password && editForm.password.trim()) {
      if (editForm.password.trim().length < 8) {
        setEditError('New password must be at least 8 characters long.');
        return;
      }
      payload.password = editForm.password.trim();
    }

    if (Object.keys(payload).length === 0) {
      setEditError('No changes were made.');
      return;
    }

    setEditLoading(true);
    try {
      const updated = await updateUser(editUser.id, payload);
      setEditUser(null);
      setSuccessMessage(`User '${updated.username}' updated successfully.`);
      fetchUsers();
    } catch (err) {
      if (err.status === 400) {
        setEditError('Administrators cannot deactivate their own account.');
      } else if (err.status === 409) {
        setEditError(err.message || 'Operation rejected: Cannot deactivate or demote the last active administrator account.');
      } else {
        setEditError(err.message || 'Failed to update user.');
      }
    } finally {
      setEditLoading(false);
    }
  };

  // Deactivate / Activate Handlers
  const handleOpenDeactivateConfirm = (target) => {
    setDeactivateTarget(target);
    setDeactivateError(null);
  };

  const handleConfirmDeactivation = async () => {
    if (!deactivateTarget) return;

    setDeactivateLoading(true);
    setDeactivateError(null);

    try {
      await updateUser(deactivateTarget.id, { isActive: false });
      setDeactivateTarget(null);
      setSuccessMessage(`User '${deactivateTarget.username}' has been deactivated.`);
      fetchUsers();
    } catch (err) {
      if (err.status === 400) {
        setDeactivateError('Administrators cannot deactivate their own account.');
      } else if (err.status === 409) {
        setDeactivateError(err.message || 'Operation rejected: Cannot deactivate or demote the last active administrator account.');
      } else {
        setDeactivateError(err.message || 'Failed to deactivate user.');
      }
    } finally {
      setDeactivateLoading(false);
    }
  };

  const handleDirectActivate = async (target) => {
    try {
      await updateUser(target.id, { isActive: true });
      setSuccessMessage(`User '${target.username}' has been reactivated.`);
      fetchUsers();
    } catch (err) {
      setError(err.message || 'Failed to activate user.');
    }
  };

  // Only render for authenticated administrators
  if (!isAdmin) {
    return null;
  }

  return (
    <section className="user-management-section" aria-label="User Management">
      {/* Section Header */}
      <div className="users-header">
        <div className="users-header-text">
          <h3 className="users-title">User Account Management</h3>
          <p className="users-subtitle">
            Provision, monitor, update roles, and manage activation states for institutional administrators and students.
          </p>
        </div>
        <div className="users-header-actions">
          <span className="users-total-badge" aria-live="polite">
            {total} {total === 1 ? 'User' : 'Users'} Registered
          </span>
          <button
            type="button"
            id="create-user-btn"
            className="create-user-btn"
            onClick={handleOpenCreate}
            aria-label="Create new user account"
          >
            <span className="create-btn-icon" aria-hidden="true">&#43;</span>
            <span>Create User</span>
          </button>
        </div>
      </div>

      {/* Success Notification Banner */}
      {successMessage && (
        <div className="users-success-banner" role="status" aria-live="polite">
          <div className="users-success-content">
            <span className="users-success-icon" aria-hidden="true">&#10003;</span>
            <span>{successMessage}</span>
          </div>
          <button
            type="button"
            className="users-banner-dismiss"
            onClick={() => setSuccessMessage(null)}
            aria-label="Dismiss success message"
          >
            &times;
          </button>
        </div>
      )}

      {/* Error Alert State */}
      {error && (
        <div className="users-error-banner" role="alert">
          <div className="users-error-content">
            <span className="users-error-icon" aria-hidden="true">&#9888;</span>
            <div className="users-error-text">
              <strong>Unable to Retrieve User Accounts</strong>
              <p>{error}</p>
            </div>
          </div>
          <button
            type="button"
            className="users-retry-btn"
            onClick={fetchUsers}
            disabled={loading}
          >
            Retry
          </button>
        </div>
      )}

      {/* Search & Filter Toolbar */}
      <div className="users-toolbar" role="search" aria-label="Filter users">
        {/* Search Input */}
        <div className="search-input-wrapper">
          <span className="search-icon" aria-hidden="true">&#128269;</span>
          <input
            id="user-search-input"
            type="text"
            className="search-input"
            placeholder="Search by username..."
            value={search}
            onChange={handleSearchChange}
            aria-label="Search users by username"
          />
          {search && (
            <button
              type="button"
              className="clear-search-btn"
              onClick={() => { setSearch(''); setDebouncedSearch(''); setPage(1); }}
              aria-label="Clear username search"
            >
              &times;
            </button>
          )}
        </div>

        {/* Filter Controls Group */}
        <div className="filter-controls-group">
          {/* Role Filter */}
          <div className="filter-select-wrapper">
            <label htmlFor="user-role-filter" className="filter-label">Role:</label>
            <select
              id="user-role-filter"
              className="filter-select"
              value={roleFilter}
              onChange={handleRoleFilterChange}
              aria-label="Filter by user role"
            >
              <option value="all">All Roles</option>
              <option value="admin">Admin</option>
              <option value="student">Student</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="filter-select-wrapper">
            <label htmlFor="user-status-filter" className="filter-label">Status:</label>
            <select
              id="user-status-filter"
              className="filter-select"
              value={statusFilter}
              onChange={handleStatusFilterChange}
              aria-label="Filter by activation status"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>

          {/* Clear Filters Button */}
          {hasActiveFilters && (
            <button
              type="button"
              className="clear-filters-btn"
              onClick={handleClearFilters}
              aria-label="Clear all active user filters"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Inline Loading Indicator */}
      {loading && (
        <div className="users-loading-indicator" role="status" aria-live="polite">
          <div className="users-spinner" aria-hidden="true"></div>
          <span>Loading user accounts from database...</span>
        </div>
      )}

      {/* Users Table */}
      {!error && (
        <div className="table-responsive-container">
          <table className="users-table" aria-label="Users data table">
            <thead>
              <tr>
                <th scope="col" className="col-id">ID</th>
                <th scope="col" className="col-username">Username</th>
                <th scope="col" className="col-role">Role</th>
                <th scope="col" className="col-status">Status</th>
                <th scope="col" className="col-created">Created</th>
                <th scope="col" className="col-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 && !loading ? (
                <tr>
                  <td colSpan="6" className="empty-table-cell">
                    <div className="empty-users-state">
                      <span className="empty-icon" aria-hidden="true">&#128101;</span>
                      <p className="empty-primary-text">
                        {hasActiveFilters ? 'No users match the active filters.' : 'No users found.'}
                      </p>
                      {hasActiveFilters && (
                        <button
                          type="button"
                          className="empty-clear-btn"
                          onClick={handleClearFilters}
                        >
                          Clear Filters
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                users.map((item) => {
                  const selfUser = isSelf(item);
                  return (
                    <tr key={item.id} className="user-row">
                      <td className="cell-id">#{item.id}</td>
                      <td className="cell-username">
                        <div className="username-wrapper">
                          <span className="user-name-text">{item.username}</span>
                          {selfUser && (
                            <span className="self-indicator-pill" title="You are currently signed in as this account">
                              You
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="cell-role">
                        <span className={`role-badge ${item.role?.toLowerCase() === 'admin' ? 'badge-role-admin' : 'badge-role-student'}`}>
                          {item.role?.toLowerCase() === 'admin' ? 'Admin' : 'Student'}
                        </span>
                      </td>
                      <td className="cell-status">
                        <span className={`status-badge ${item.is_active ? 'badge-status-active' : 'badge-status-inactive'}`}>
                          <span className="status-dot" aria-hidden="true"></span>
                          {item.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="cell-created">
                        <span className="timestamp-text">{formatTimestamp(item.created_at)}</span>
                      </td>
                      <td className="cell-actions">
                        <div className="actions-cluster">
                          <button
                            type="button"
                            className="action-btn edit-action-btn"
                            onClick={() => handleOpenEdit(item)}
                            aria-label={`Edit user ${item.username}`}
                          >
                            Edit
                          </button>

                          {item.is_active ? (
                            <button
                              type="button"
                              className={`action-btn deactivate-action-btn ${selfUser ? 'btn-disabled' : ''}`}
                              onClick={() => !selfUser && handleOpenDeactivateConfirm(item)}
                              disabled={selfUser}
                              title={selfUser ? 'You cannot deactivate your own account.' : `Deactivate ${item.username}`}
                              aria-label={selfUser ? 'Deactivation disabled for own account' : `Deactivate user ${item.username}`}
                            >
                              Deactivate
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="action-btn activate-action-btn"
                              onClick={() => handleDirectActivate(item)}
                              aria-label={`Activate user ${item.username}`}
                            >
                              Activate
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Bar */}
      <div className="users-pagination-bar" aria-label="User Pagination Navigation">
        <div className="pagination-info" aria-live="polite">
          {total > 0 ? (
            <span>
              Showing page <strong>{page}</strong> of <strong>{totalPages || 1}</strong> &middot;{' '}
              <strong>{total}</strong> {total === 1 ? 'user' : 'users'}
            </span>
          ) : (
            <span>0 users</span>
          )}
        </div>

        <div className="pagination-controls">
          <div className="page-size-selector">
            <label htmlFor="users-page-size-select" className="page-size-label">Rows per page:</label>
            <select
              id="users-page-size-select"
              className="page-size-select"
              value={pageSize}
              onChange={handlePageSizeChange}
              disabled={loading}
              aria-label="Select number of users per page"
            >
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
          </div>

          <div className="page-nav-buttons">
            <button
              type="button"
              className="page-btn prev-btn"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              aria-label="Go to previous users page"
            >
              &larr; Previous
            </button>

            <span className="current-page-indicator" aria-current="page">
              Page {page} of {totalPages || 1}
            </span>

            <button
              type="button"
              className="page-btn next-btn"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              aria-label="Go to next users page"
            >
              Next &rarr;
            </button>
          </div>
        </div>
      </div>

      {/* CREATE USER MODAL */}
      {isCreateOpen && (
        <div className="modal-backdrop" onClick={() => setIsCreateOpen(false)} role="presentation">
          <div
            className="modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-user-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 id="create-user-title" className="modal-title">Create New User</h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setIsCreateOpen(false)}
                aria-label="Close user creation dialog"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="modal-form">
              {createError && (
                <div className="modal-error-banner" role="alert">
                  <span className="error-icon" aria-hidden="true">&times;</span>
                  <span>{createError}</span>
                </div>
              )}

              <div className="form-field">
                <label htmlFor="create-username-input" className="form-label">
                  Username <span className="required-star">*</span>
                </label>
                <input
                  id="create-username-input"
                  type="text"
                  className="modal-input"
                  placeholder="e.g. student_john"
                  value={createForm.username}
                  onChange={(e) => setCreateForm({ ...createForm, username: e.target.value })}
                  disabled={createLoading}
                  required
                  autoFocus
                />
              </div>

              <div className="form-field">
                <label htmlFor="create-password-input" className="form-label">
                  Password <span className="required-star">*</span>
                </label>
                <input
                  id="create-password-input"
                  type="password"
                  className="modal-input"
                  placeholder="Minimum 8 characters"
                  value={createForm.password}
                  onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                  disabled={createLoading}
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
                <span className="field-hint">Must be at least 8 characters long.</span>
              </div>

              <div className="form-field">
                <label htmlFor="create-role-select" className="form-label">
                  Role <span className="required-star">*</span>
                </label>
                <select
                  id="create-role-select"
                  className="modal-select"
                  value={createForm.role}
                  onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}
                  disabled={createLoading}
                >
                  <option value="student">Student</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="modal-btn-cancel"
                  onClick={() => setIsCreateOpen(false)}
                  disabled={createLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="modal-btn-primary"
                  disabled={createLoading}
                  aria-busy={createLoading}
                >
                  {createLoading ? 'Creating User...' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT USER MODAL */}
      {editUser && (
        <div className="modal-backdrop" onClick={() => setEditUser(null)} role="presentation">
          <div
            className="modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-user-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 id="edit-user-title" className="modal-title">Edit User Account</h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setEditUser(null)}
                aria-label="Close edit dialog"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleEditSubmit} className="modal-form">
              {editError && (
                <div className="modal-error-banner" role="alert">
                  <span className="error-icon" aria-hidden="true">&times;</span>
                  <span>{editError}</span>
                </div>
              )}

              {/* Read-Only Username */}
              <div className="form-field">
                <label htmlFor="edit-username-display" className="form-label">Username</label>
                <input
                  id="edit-username-display"
                  type="text"
                  className="modal-input input-readonly"
                  value={editUser.username}
                  readOnly
                  disabled
                />
                <span className="field-hint">Usernames are permanent and cannot be modified.</span>
              </div>

              {/* Role Selection */}
              <div className="form-field">
                <label htmlFor="edit-role-select" className="form-label">Assigned Role</label>
                <select
                  id="edit-role-select"
                  className="modal-select"
                  value={editForm.role}
                  onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                  disabled={editLoading}
                >
                  <option value="student">Student</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              {/* Activation Status */}
              <div className="form-field">
                <label htmlFor="edit-status-select" className="form-label">Account Status</label>
                <select
                  id="edit-status-select"
                  className="modal-select"
                  value={editForm.isActive ? 'active' : 'inactive'}
                  onChange={(e) => setEditForm({ ...editForm, isActive: e.target.value === 'active' })}
                  disabled={editLoading || (isSelf(editUser) && editForm.isActive)}
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
                {isSelf(editUser) && (
                  <span className="field-hint hint-warning">
                    You cannot deactivate your own administrative account.
                  </span>
                )}
              </div>

              {/* Optional Password Reset */}
              <div className="form-field">
                <label htmlFor="edit-password-input" className="form-label">
                  Reset Password <span className="optional-tag">(Optional)</span>
                </label>
                <input
                  id="edit-password-input"
                  type="password"
                  className="modal-input"
                  placeholder="Leave blank to preserve current password"
                  value={editForm.password}
                  onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                  disabled={editLoading}
                  autoComplete="new-password"
                />
                <span className="field-hint">If entered, must be at least 8 characters.</span>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="modal-btn-cancel"
                  onClick={() => setEditUser(null)}
                  disabled={editLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="modal-btn-primary"
                  disabled={editLoading}
                  aria-busy={editLoading}
                >
                  {editLoading ? 'Saving Changes...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DEACTIVATE CONFIRMATION MODAL */}
      {deactivateTarget && (
        <div className="modal-backdrop" onClick={() => setDeactivateTarget(null)} role="presentation">
          <div
            className="modal-card modal-confirm-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="deactivate-confirm-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 id="deactivate-confirm-title" className="modal-title modal-danger-title">
                Confirm Account Deactivation
              </h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setDeactivateTarget(null)}
                aria-label="Cancel deactivation"
              >
                &times;
              </button>
            </div>

            <div className="modal-body confirm-body">
              {deactivateError && (
                <div className="modal-error-banner" role="alert">
                  <span className="error-icon" aria-hidden="true">&times;</span>
                  <span>{deactivateError}</span>
                </div>
              )}

              <p className="confirm-text">
                Are you sure you want to deactivate user <strong>'{deactivateTarget.username}'</strong>?
              </p>
              <div className="confirm-consequences">
                <span className="consequence-icon" aria-hidden="true">&#9888;</span>
                <p className="consequence-text">
                  The user will immediately lose access and will no longer be able to sign in. Historical feedback records associated with this account remain preserved.
                </p>
              </div>
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="modal-btn-cancel"
                onClick={() => setDeactivateTarget(null)}
                disabled={deactivateLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="modal-btn-danger"
                onClick={handleConfirmDeactivation}
                disabled={deactivateLoading}
                aria-busy={deactivateLoading}
              >
                {deactivateLoading ? 'Deactivating...' : 'Deactivate User'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
