import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { analyzeFeedback, analyzeAndSaveFeedback } from '../analysisApi';

describe('analysisApi Service (Regression Tests)', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = global.fetch;
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('analyzeFeedback remains public and sends feedback text to /api/v1/feedback/analyze', async () => {
    const mockAnalysisResponse = {
      clean_text: 'great professors',
      sentiment: { name: 'POSITIVE', confidence: 0.95 },
      category: { name: 'Academics', confidence: 0.88 },
      priority: { level: 'LOW', score: 20, reason: 'Positive feedback' },
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockAnalysisResponse,
    });

    const result = await analyzeFeedback('Great professors this term!');

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [calledUrl, calledOptions] = global.fetch.mock.calls[0];

    expect(calledUrl).toContain('/api/v1/feedback/analyze');
    expect(calledOptions.method).toBe('POST');
    // Ensure no Authorization header is attached (public endpoint)
    expect(calledOptions.headers.Authorization).toBeUndefined();
    expect(JSON.parse(calledOptions.body)).toEqual({ feedback: 'Great professors this term!' });

    expect(result).toEqual(mockAnalysisResponse);
  });

  it('analyzeAndSaveFeedback remains public and sends payload with metadata to /api/v1/feedback/analyze-and-save', async () => {
    const mockPersistedResponse = {
      id: 101,
      feedback: 'The wifi in library keeps dropping.',
      department: 'Computer Science',
      semester: 'Fall 2026',
      clean_text: 'wifi library keeps dropping',
      sentiment: { name: 'NEGATIVE', confidence: 0.92 },
      category: { name: 'Facilities', confidence: 0.94 },
      priority: { level: 'HIGH', score: 85, reason: 'Negative facility issue' },
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => mockPersistedResponse,
    });

    const result = await analyzeAndSaveFeedback('The wifi in library keeps dropping.', {
      department: 'Computer Science',
      semester: 'Fall 2026',
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [calledUrl, calledOptions] = global.fetch.mock.calls[0];

    expect(calledUrl).toContain('/api/v1/feedback/analyze-and-save');
    expect(calledOptions.method).toBe('POST');
    expect(calledOptions.headers.Authorization).toBeUndefined();
    expect(JSON.parse(calledOptions.body)).toEqual({
      feedback: 'The wifi in library keeps dropping.',
      department: 'Computer Science',
      semester: 'Fall 2026',
    });

    expect(result).toEqual(mockPersistedResponse);
  });

  it('validates empty feedback text client-side before dispatching network request', async () => {
    await expect(analyzeFeedback('')).rejects.toThrow('Please enter meaningful feedback before analyzing.');
    await expect(analyzeFeedback('   ')).rejects.toThrow('Please enter meaningful feedback before analyzing.');
    await expect(analyzeAndSaveFeedback(null)).rejects.toThrow('Please enter meaningful feedback before analyzing.');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('translates HTTP 422, 503, and 500 into user-friendly messages', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ msg: 'Text too short' }] }),
    });
    await expect(analyzeFeedback('a')).rejects.toThrow('Text too short');

    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
    });
    await expect(analyzeFeedback('valid text')).rejects.toThrow('temporarily unavailable');

    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });
    await expect(analyzeFeedback('valid text')).rejects.toThrow('unexpected server error');
  });
});
