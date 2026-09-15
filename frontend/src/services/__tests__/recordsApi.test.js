import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getFeedbackRecords, fetchAllMatchingFeedbackRecords } from '../recordsApi';
import { apiClient } from '../apiClient';

describe('recordsApi Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('constructs query parameters correctly for page, pageSize, search, and filters', async () => {
    const mockResponse = {
      items: [{ id: 1, feedback_text: 'Library quiet hours' }],
      total: 1,
      page: 2,
      page_size: 15,
      total_pages: 1,
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValueOnce(mockResponse);

    const result = await getFeedbackRecords({
      page: 2,
      pageSize: 15,
      search: 'library',
      sentiment: 'positive',
      category: 'Facilities',
      priority: 'high',
      token: 'admin-jwt',
    });

    expect(getSpy).toHaveBeenCalledTimes(1);
    const [calledPath, calledOptions] = getSpy.mock.calls[0];

    expect(calledPath).toContain('page=2');
    expect(calledPath).toContain('page_size=15');
    expect(calledPath).toContain('search=library');
    expect(calledPath).toContain('sentiment=positive');
    expect(calledPath).toContain('category=Facilities');
    expect(calledPath).toContain('priority=high');
    expect(calledOptions.token).toBe('admin-jwt');

    expect(result).toEqual(mockResponse);
  });

  it('omits filter parameters when set to "all" or empty string', async () => {
    const mockResponse = {
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValueOnce(mockResponse);

    await getFeedbackRecords({
      sentiment: 'all',
      category: 'all',
      priority: 'all',
      search: '   ',
    });

    const [calledPath] = getSpy.mock.calls[0];
    expect(calledPath).not.toContain('sentiment=');
    expect(calledPath).not.toContain('category=');
    expect(calledPath).not.toContain('priority=');
    expect(calledPath).not.toContain('search=');
  });

  it('defensively throws if response structure is malformed', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      items: 'not-an-array',
    });

    await expect(getFeedbackRecords()).rejects.toThrow(
      'Received an unexpected response structure from the feedback records service.'
    );
  });

  it('fetchAllMatchingFeedbackRecords fetches pages sequentially and aggregates all items', async () => {
    const page1Data = {
      items: [{ id: 1 }, { id: 2 }],
      total: 4,
      page: 1,
      page_size: 2,
      total_pages: 2,
    };

    const page2Data = {
      items: [{ id: 3 }, { id: 4 }],
      total: 4,
      page: 2,
      page_size: 2,
      total_pages: 2,
    };

    const getSpy = vi.spyOn(apiClient, 'get')
      .mockResolvedValueOnce(page1Data)
      .mockResolvedValueOnce(page2Data);

    const progressReports = [];
    const onProgress = (curr, totalP, loaded, totalExp) => {
      progressReports.push({ curr, totalP, loaded, totalExp });
    };

    const allRecords = await fetchAllMatchingFeedbackRecords({ sentiment: 'negative' }, onProgress);

    expect(allRecords).toHaveLength(4);
    expect(allRecords.map((r) => r.id)).toEqual([1, 2, 3, 4]);
    expect(getSpy).toHaveBeenCalledTimes(2);
    expect(progressReports.length).toBeGreaterThan(0);
  });

  it('fetchAllMatchingFeedbackRecords halts immediately and throws on 401 error without returning partial results', async () => {
    const page1Data = {
      items: [{ id: 1 }],
      total: 2,
      page: 1,
      page_size: 1,
      total_pages: 2,
    };

    vi.spyOn(apiClient, 'get')
      .mockResolvedValueOnce(page1Data)
      .mockRejectedValueOnce(new Error('Session expired 401'));

    await expect(fetchAllMatchingFeedbackRecords()).rejects.toThrow('Session expired 401');
  });
});
