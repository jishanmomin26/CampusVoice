import React, { Suspense, lazy } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import LazyFallback from '../LazyFallback';
import ErrorBoundary from '../ErrorBoundary';

describe('Lazy Loading & Suspense Fallbacks', () => {
  it('LazyFallback component renders with role="status" and custom message', () => {
    render(<LazyFallback message="Loading Administrative Tools..." minHeight="250px" />);

    const statusEl = screen.getByRole('status');
    expect(statusEl).toBeInTheDocument();
    expect(statusEl).toHaveTextContent('Loading Administrative Tools...');
  });

  it('renders fallback while resolving lazy component and then renders resolved component', async () => {
    let resolveComponent;
    const DelayedComponent = lazy(
      () =>
        new Promise((resolve) => {
          resolveComponent = () =>
            resolve({
              default: () => <div>Lazy Loaded Content Ready</div>,
            });
        })
    );

    render(
      <Suspense fallback={<LazyFallback message="Waiting for chunk..." />}>
        <DelayedComponent />
      </Suspense>
    );

    // Initial state: fallback should be in document
    expect(screen.getByText('Waiting for chunk...')).toBeInTheDocument();

    // Resolve the promise
    resolveComponent();

    // Final state: loaded component should be in document
    await waitFor(() => {
      expect(screen.getByText('Lazy Loaded Content Ready')).toBeInTheDocument();
    });
  });

  it('ErrorBoundary catches chunk load rejection and displays retry card', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const FailingLazyComponent = lazy(() => Promise.reject(new Error('Failed to fetch dynamically imported module')));

    render(
      <ErrorBoundary fallbackTitle="Failed to Load Section">
        <Suspense fallback={<LazyFallback message="Loading..." />}>
          <FailingLazyComponent />
        </Suspense>
      </ErrorBoundary>
    );

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Failed to Load Section')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry loading/i })).toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });
});
