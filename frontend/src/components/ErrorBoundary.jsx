import React from 'react';

/**
 * ErrorBoundary Component (Step 9.15.1)
 * 
 * Catches JavaScript errors anywhere in its child component tree,
 * logs the error internally, and displays a friendly, accessible fallback UI.
 * 
 * Avoids exposing raw stack traces, file paths, or internal error objects to users.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Internal logging without exposing details to user interface
    if (process.env.NODE_ENV === 'development') {
      console.warn('ErrorBoundary caught an error:', error?.message);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onRetry) {
      this.props.onRetry();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="lazy-error-container" role="alert" aria-live="assertive">
          <div className="lazy-error-card">
            <span className="lazy-error-icon" aria-hidden="true">&#9888;</span>
            <h3 className="lazy-error-title">
              {this.props.fallbackTitle || 'Unable to Load Component'}
            </h3>
            <p className="lazy-error-description">
              {this.props.fallbackDescription || 'A network error or loading issue occurred while loading this section.'}
            </p>
            <div className="lazy-error-actions">
              <button
                type="button"
                className="lazy-retry-btn"
                onClick={this.handleRetry}
              >
                Retry Loading
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
