import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FeedbackRecords from '../FeedbackRecords';
import * as recordsApi from '../../services/recordsApi';
import * as exportFeedback from '../../utils/exportFeedback';

describe('FeedbackRecords Component', () => {
  const mockRecords = [
    {
      id: 1,
      feedback_text: 'The campus library should extend weekend hours.',
      clean_text: 'campus library extend weekend hours',
      department: 'Library Sciences',
      semester: 'Fall 2026',
      sentiment_name: 'NEUTRAL',
      sentiment_confidence: 0.81,
      category_name: 'Facilities',
      category_confidence: 0.95,
      priority_level: 'MEDIUM',
      priority_score: 55,
      priority_reason: 'Facility hours request',
      created_at: '2026-09-14T10:00:00Z',
    },
    {
      id: 2,
      feedback_text: 'Outstanding teaching in data structures course!',
      clean_text: 'outstanding teaching data structures course',
      department: 'Computer Science',
      semester: 'Fall 2026',
      sentiment_name: 'POSITIVE',
      sentiment_confidence: 0.98,
      category_name: 'Academics',
      category_confidence: 0.92,
      priority_level: 'LOW',
      priority_score: 10,
      priority_reason: 'Commendation',
      created_at: '2026-09-14T11:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('displays loading state and then renders records table with row contents', async () => {
    vi.spyOn(recordsApi, 'getFeedbackRecords').mockResolvedValueOnce({
      items: mockRecords,
      total: 2,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    render(<FeedbackRecords />);

    expect(screen.getByText(/loading feedback records from database/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('#1')).toBeInTheDocument();
      expect(screen.getByText('The campus library should extend weekend hours.')).toBeInTheDocument();
      expect(screen.getByText('#2')).toBeInTheDocument();
      expect(screen.getByText('Outstanding teaching in data structures course!')).toBeInTheDocument();
    });
  });

  it('renders empty state when no records match filter', async () => {
    vi.spyOn(recordsApi, 'getFeedbackRecords').mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    });

    render(<FeedbackRecords />);

    await waitFor(() => {
      expect(screen.getByText(/no feedback records found/i)).toBeInTheDocument();
    });
  });

  it('renders error state and triggers retry when retry button is clicked', async () => {
    const getRecordsSpy = vi.spyOn(recordsApi, 'getFeedbackRecords')
      .mockRejectedValueOnce(new Error('Network connection dropped'))
      .mockResolvedValueOnce({
        items: mockRecords,
        total: 2,
        page: 1,
        page_size: 10,
        total_pages: 1,
      });

    render(<FeedbackRecords />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/unable to retrieve feedback records/i)).toBeInTheDocument();
    });

    const retryBtn = screen.getByRole('button', { name: /retry/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByText('#1')).toBeInTheDocument();
    });

    expect(getRecordsSpy).toHaveBeenCalledTimes(2);
  });

  it('opens record detail view when "View Details" button is clicked', async () => {
    vi.spyOn(recordsApi, 'getFeedbackRecords').mockResolvedValueOnce({
      items: mockRecords,
      total: 2,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    render(<FeedbackRecords />);

    await waitFor(() => {
      expect(screen.getByText('#1')).toBeInTheDocument();
    });

    const viewDetailButtons = screen.getAllByRole('button', { name: /view details/i });
    fireEvent.click(viewDetailButtons[0]);

    // Modal dialog should open and render original feedback
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Feedback Details')).toBeInTheDocument();
      expect(screen.getByText('Record #1')).toBeInTheDocument();
    });
  });

  it('triggers CSV and Excel exports when export buttons are clicked', async () => {
    vi.spyOn(recordsApi, 'getFeedbackRecords').mockResolvedValueOnce({
      items: mockRecords,
      total: 2,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    vi.spyOn(recordsApi, 'fetchAllMatchingFeedbackRecords').mockResolvedValue(mockRecords);
    const csvExportSpy = vi.spyOn(exportFeedback, 'exportFeedbackToCSV').mockReturnValue('records.csv');
    const excelExportSpy = vi.spyOn(exportFeedback, 'exportFeedbackToExcel').mockResolvedValue('records.xlsx');

    render(<FeedbackRecords />);

    await waitFor(() => {
      expect(screen.getByText('#1')).toBeInTheDocument();
    });

    const csvBtn = screen.getByRole('button', { name: /export.*csv/i });
    fireEvent.click(csvBtn);

    await waitFor(() => {
      expect(csvExportSpy).toHaveBeenCalledWith(mockRecords);
    });

    const excelBtn = screen.getByRole('button', { name: /export.*excel/i });
    fireEvent.click(excelBtn);

    await waitFor(() => {
      expect(excelExportSpy).toHaveBeenCalledWith(mockRecords);
    });
  });
});
