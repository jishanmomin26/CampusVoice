import React from 'react';

/**
 * LazyFallback Component (Step 9.15.1)
 * 
 * Accessible, styled loading placeholder used for React.Suspense fallbacks.
 * Matches CampusVoice dark-glassmorphic aesthetic and prevents layout jumping.
 * 
 * @param {Object} props
 * @param {string} [props.message='Loading...'] - Screen-reader accessible loading message
 * @param {string|number} [props.minHeight] - Optional container minimum height
 */
export default function LazyFallback({ message = 'Loading...', minHeight = '240px' }) {
  return (
    <div
      className="lazy-loading-container"
      role="status"
      aria-live="polite"
      style={{ minHeight }}
    >
      <div className="lazy-loading-card">
        <div className="lazy-loading-spinner" aria-hidden="true"></div>
        <p className="lazy-loading-text">{message}</p>
      </div>
    </div>
  );
}
