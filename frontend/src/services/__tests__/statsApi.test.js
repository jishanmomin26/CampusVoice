import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getFeedbackStats } from '../statsApi';
import { apiClient } from '../apiClient';

describe('statsApi Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('calls GET /api/v1/feedback/stats through apiClient with authentication', async () => {
    const mockStats = {
      total_feedback: 50,
      analyzed_feedback: 45,
      unclassified_feedback: 5,
      sentiment: { positive: 25, neutral: 10, negative: 15 },
      priority: { high: 10, medium: 20, low: 20 },
      categories: { Facilities: 20, Academics: 30 },
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValueOnce(mockStats);

    const result = await getFeedbackStats('optional-token-override');

    expect(getSpy).toHaveBeenCalledWith('/api/v1/feedback/stats', { token: 'optional-token-override' });
    expect(result).toEqual(mockStats);
  });

  it('defensively validates response structure and throws if missing required fields', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      total_feedback: 50,
      // missing analyzed_feedback, sentiment, etc.
    });

    await expect(getFeedbackStats()).rejects.toThrow(
      'Received an unexpected response structure from the feedback statistics service.'
    );
  });

  it('propagates 401 authentication errors safely', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new Error('Session expired'));

    await expect(getFeedbackStats()).rejects.toThrow('Session expired');
  });
});
