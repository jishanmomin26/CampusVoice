import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import './LoginPage.css';

/**
 * LoginPage Component (Step 9.13.1)
 * 
 * Provides an accessible, responsive, and secure authentication interface:
 * - Direct authentication against FastAPI backend via AuthContext
 * - Never stores or logs plaintext passwords
 * - Displays safe, sanitized error messages
 * - Includes proper autocomplete attributes and accessible ARIA attributes
 */
export default function LoginPage({ onSuccess, onCancel }) {
  const { login } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    const trimmedUsername = username.trim();

    if (!trimmedUsername) {
      setErrorMessage('Please enter your username.');
      return;
    }

    if (!password) {
      setErrorMessage('Please enter your password.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const userProfile = await login(trimmedUsername, password);
      // Immediately clear password from memory
      setPassword('');
      if (typeof onSuccess === 'function') {
        onSuccess(userProfile);
      }
    } catch (err) {
      // Safe, sanitized error message without exposing backend internals
      setErrorMessage(err.message || 'Invalid username or password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-card">
        {/* Brand Header */}
        <div className="login-brand-header">
          <div className="login-brand-badge">
            <span className="login-pulse-dot" aria-hidden="true"></span>
            CampusVoice &bull; Admin Security
          </div>
          <h2 className="login-title">Administrator Sign In</h2>
          <p className="login-subtitle">
            Enter your credentials to access the feedback intelligence dashboard and analytics.
          </p>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div
            role="alert"
            aria-live="polite"
            id="login-error-alert"
            className="login-error-alert"
          >
            <span className="login-error-icon" aria-hidden="true">&#9888;</span>
            <span className="login-error-text">{errorMessage}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="login-form" noValidate>
          {/* Username Field */}
          <div className="login-form-group">
            <label htmlFor="login-username" className="login-form-label">
              Username
            </label>
            <input
              id="login-username"
              name="username"
              type="text"
              autoComplete="username"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck="false"
              autoFocus
              className="login-form-input"
              placeholder="Enter your admin username"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (errorMessage) setErrorMessage(null);
              }}
              disabled={isSubmitting}
              aria-describedby={errorMessage ? "login-error-alert" : undefined}
              required
            />
          </div>

          {/* Password Field */}
          <div className="login-form-group">
            <label htmlFor="login-password" className="login-form-label">
              Password
            </label>
            <div className="password-input-wrapper">
              <input
                id="login-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                className="login-form-input password-input"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (errorMessage) setErrorMessage(null);
                }}
                disabled={isSubmitting}
                aria-describedby={errorMessage ? "login-error-alert" : undefined}
                required
              />
              <button
                type="button"
                className="password-visibility-toggle"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                disabled={isSubmitting}
                tabIndex={0}
              >
                {showPassword ? (
                  <span aria-hidden="true">&#128064;</span>
                ) : (
                  <span aria-hidden="true">&#128065;</span>
                )}
              </button>
            </div>
          </div>

          {/* Form Actions */}
          <div className="login-actions">
            <button
              type="submit"
              id="btn-login-submit"
              className="login-submit-btn"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <span className="login-btn-content">
                  <span className="login-spinner" aria-hidden="true"></span>
                  Signing In...
                </span>
              ) : (
                'Sign In'
              )}
            </button>

            {onCancel && (
              <button
                type="button"
                id="btn-login-cancel"
                className="login-cancel-btn"
                onClick={onCancel}
                disabled={isSubmitting}
              >
                &larr; Return to Student Portal
              </button>
            )}
          </div>
        </form>

        {/* Security / Help Note */}
        <div className="login-card-footer">
          <p className="login-note">
            Students do not require an account to submit course or campus feedback.
          </p>
        </div>
      </div>
    </div>
  );
}
