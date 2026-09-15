import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { login as apiLogin, getCurrentUser as apiGetCurrentUser } from '../services/authApi';
import { onUnauthorized } from '../services/apiClient';
import { getStoredToken, setStoredToken, removeStoredToken } from '../utils/tokenStorage';

const AuthContext = createContext(null);

/**
 * Authentication Provider Component (Step 9.13.1 & 9.13.2)
 * 
 * Manages global authentication state, token persistence, and role-based permissions:
 * - Automatically restores user session from localStorage on application startup.
 * - Handles login credential validation and JWT storage.
 * - Manages clean session termination upon logout or 401 session expiration.
 * - Strictly avoids storing plaintext passwords.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  // Subscribe to centralized 401 Unauthorized session expiration events
  useEffect(() => {
    const unsubscribe = onUnauthorized((_error) => {
      // Clear authenticated state cleanly without direct React manipulation from API layer
      setToken(null);
      setUser(null);
      setSessionExpired(true);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  // Restore session from localStorage on initial mount
  useEffect(() => {
    let isMounted = true;

    async function initializeAuth() {
      const storedToken = getStoredToken();

      if (!storedToken) {
        if (isMounted) {
          setToken(null);
          setUser(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const userData = await apiGetCurrentUser(storedToken);
        if (isMounted) {
          setToken(storedToken);
          setUser(userData);
        }
      } catch (err) {
        // Token is invalid, expired, or malformed; clear it cleanly
        console.warn('Authentication token validation failed on startup. Clearing session.', err.message);
        removeStoredToken();
        if (isMounted) {
          setToken(null);
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    initializeAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  /**
   * Authenticates user with username and password, then stores the JWT token.
   * 
   * @param {string} username - User login name.
   * @param {string} password - User plain-text password.
   * @returns {Promise<Object>} Authenticated user profile.
   */
  const login = useCallback(async (username, password) => {
    // 1. Authenticate with backend
    const authData = await apiLogin(username, password);
    const accessToken = authData.access_token;

    // 2. Fetch full authenticated profile using the new token
    const userProfile = await apiGetCurrentUser(accessToken);

    // 3. Persist token to localStorage
    setStoredToken(accessToken);

    // 4. Update auth state and reset sessionExpired flag
    setToken(accessToken);
    setUser(userProfile);
    setSessionExpired(false);

    return userProfile;
  }, []);

  /**
   * Clears the sessionExpired flag once acknowledged by the UI.
   */
  const clearSessionExpired = useCallback(() => {
    setSessionExpired(false);
  }, []);

  /**
   * Logs out the current user, removing the token and resetting state.
   */
  const logout = useCallback(() => {
    removeStoredToken();
    setToken(null);
    setUser(null);
    setSessionExpired(false);
  }, []);

  const value = {
    user,
    token,
    isAuthenticated: Boolean(user && token),
    isAdmin: Boolean(user && user.role === 'admin'),
    isLoading,
    sessionExpired,
    clearSessionExpired,
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Custom React hook to consume Authentication Context.
 * 
 * @returns {{
 *   user: Object|null,
 *   token: string|null,
 *   isAuthenticated: boolean,
 *   isAdmin: boolean,
 *   isLoading: boolean,
 *   login: (username: string, password: string) => Promise<Object>,
 *   logout: () => void
 * }}
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
