import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBoundary from '../ErrorBoundary';

// Helper component that throws an error conditionally
function ProblemChild({ shouldThrow }) {
  if (shouldThrow) {
    throw new Error('Secret internal failure in component tree');
  }
  return <div>Healthy Child Content</div>;
}

describe('ErrorBoundary Component', () => {
  it('renders children normally when no error occurs', () => {
    render(
      <ErrorBoundary>
        <ProblemChild shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Healthy Child Content')).toBeInTheDocument();
  });

  it('catches render errors, shows safe fallback, and does not expose stack traces', () => {
    // Suppress console.error/warn output from React test renderer during boundary trigger
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary
        fallbackTitle="Custom Error Title"
        fallbackDescription="Custom safe error description"
      >
        <ProblemChild shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Custom Error Title')).toBeInTheDocument();
    expect(screen.getByText('Custom safe error description')).toBeInTheDocument();

    // Verify secret internal stack trace or raw message is not shown in DOM
    expect(screen.queryByText(/Secret internal failure/i)).not.toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  it('provides a retry control that triggers onRetry callback', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const onRetryMock = vi.fn();

    render(
      <ErrorBoundary onRetry={onRetryMock}>
        <ProblemChild shouldThrow={true} />
      </ErrorBoundary>
    );

    const retryBtn = screen.getByRole('button', { name: /retry loading/i });
    expect(retryBtn).toBeInTheDocument();

    fireEvent.click(retryBtn);
    expect(onRetryMock).toHaveBeenCalledTimes(1);

    consoleSpy.mockRestore();
  });
});
