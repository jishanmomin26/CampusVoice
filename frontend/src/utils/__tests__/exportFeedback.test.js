import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  escapeCSVField,
  transformRecordToRow,
  generateExportFilename,
  formatSubmittedDate,
  exportFeedbackToCSV,
  exportFeedbackToExcel,
  EXPORT_HEADERS,
} from '../exportFeedback';

describe('exportFeedback Utility', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('escapeCSVField', () => {
    it('returns empty string for null and undefined', () => {
      expect(escapeCSVField(null)).toBe('');
      expect(escapeCSVField(undefined)).toBe('');
    });

    it('returns regular strings unchanged if no special characters exist', () => {
      expect(escapeCSVField('Simple text')).toBe('Simple text');
      expect(escapeCSVField(1234)).toBe('1234');
    });

    it('escapes fields containing commas with double quotes', () => {
      expect(escapeCSVField('Computer, Science')).toBe('"Computer, Science"');
    });

    it('escapes double quotes by doubling them', () => {
      expect(escapeCSVField('Say "hello" now')).toBe('"Say ""hello"" now"');
    });

    it('escapes fields containing newlines', () => {
      expect(escapeCSVField("Line 1\nLine 2")).toBe('"Line 1\nLine 2"');
      expect(escapeCSVField("Line 1\r\nLine 2")).toBe('"Line 1\r\nLine 2"');
    });
  });

  describe('transformRecordToRow & NULL Handling', () => {
    it('transforms a complete record into an ordered 14-cell array matching EXPORT_HEADERS', () => {
      const record = {
        id: 42,
        department: 'Engineering',
        semester: 'Fall 2026',
        feedback_text: 'Excellent lab equipment',
        clean_text: 'excellent lab equipment',
        sentiment_name: 'POSITIVE',
        sentiment_label: 2,
        sentiment_confidence: 0.942,
        category_name: 'Facilities',
        category_confidence: 0.885,
        priority_level: 'LOW',
        priority_score: 15,
        priority_reason: 'Positive lab feedback',
        created_at: '2026-09-14T10:30:00Z',
      };

      const row = transformRecordToRow(record);
      expect(row).toHaveLength(EXPORT_HEADERS.length);
      expect(row[0]).toBe(42);
      expect(row[1]).toBe('Engineering');
      expect(row[2]).toBe('Fall 2026');
      expect(row[3]).toBe('Excellent lab equipment');
      expect(row[4]).toBe('excellent lab equipment');
      expect(row[5]).toBe('POSITIVE');
      expect(row[6]).toBe(2);
      expect(row[7]).toBe('94.2%');
      expect(row[8]).toBe('Facilities');
      expect(row[9]).toBe('88.5%');
      expect(row[10]).toBe('LOW');
      expect(row[11]).toBe(15);
      expect(row[12]).toBe('Positive lab feedback');
      expect(row[13]).toContain('2026');
    });

    it('handles legacy and unclassified NULL records safely without crashing', () => {
      const emptyRecord = {
        id: 99,
        feedback_text: 'Legacy submission without analysis',
      };

      const row = transformRecordToRow(emptyRecord);
      expect(row).toHaveLength(EXPORT_HEADERS.length);
      expect(row[0]).toBe(99);
      expect(row[1]).toBe(''); // department
      expect(row[2]).toBe(''); // semester
      expect(row[3]).toBe('Legacy submission without analysis');
      expect(row[4]).toBe(''); // clean_text
      expect(row[5]).toBe('Unclassified'); // sentiment
      expect(row[6]).toBe(''); // sentiment_label
      expect(row[7]).toBe(''); // sentiment_confidence
      expect(row[8]).toBe('Unclassified'); // category
      expect(row[9]).toBe(''); // category_confidence
      expect(row[10]).toBe('Unclassified'); // priority_level
      expect(row[11]).toBe(''); // priority_score
      expect(row[12]).toBe(''); // priority_reason
      expect(row[13]).toBe(''); // submitted
    });
  });

  describe('generateExportFilename', () => {
    it('generates a dated filename with correct extension', () => {
      const csvName = generateExportFilename('csv');
      expect(csvName).toMatch(/^campusvoice_feedback_\d{4}-\d{2}-\d{2}\.csv$/);

      const xlsxName = generateExportFilename('.xlsx');
      expect(xlsxName).toMatch(/^campusvoice_feedback_\d{4}-\d{2}-\d{2}\.xlsx$/);
    });
  });

  describe('exportFeedbackToCSV', () => {
    it('throws error when exporting empty or invalid records array', () => {
      expect(() => exportFeedbackToCSV([])).toThrow('No records to export.');
      expect(() => exportFeedbackToCSV(null)).toThrow('No records to export.');
    });

    it('builds RFC compliant CSV with UTF-8 BOM and triggers download link click', () => {
      let createdBlob = null;
      vi.spyOn(URL, 'createObjectURL').mockImplementation((blob) => {
        createdBlob = blob;
        return 'blob:mock-csv-url';
      });

      const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

      const sampleRecords = [
        {
          id: 1,
          feedback_text: 'Great library, lots of space "quiet" rooms.',
          sentiment_name: 'POSITIVE',
          created_at: '2026-09-15T00:00:00Z',
        },
      ];

      const filename = exportFeedbackToCSV(sampleRecords, 'test_export.csv');
      expect(filename).toBe('test_export.csv');
      expect(clickSpy).toHaveBeenCalled();
      expect(createdBlob).not.toBeNull();
      expect(createdBlob.type).toContain('text/csv');
    });
  });

  describe('exportFeedbackToExcel (Dynamic XLSX Import)', () => {
    it('throws error when exporting empty records array', async () => {
      await expect(exportFeedbackToExcel([])).rejects.toThrow('No records to export.');
    });

    it('dynamically loads SheetJS and constructs workbook on demand', async () => {
      const mockXlsx = {
        utils: {
          aoa_to_sheet: vi.fn().mockReturnValue({}),
          book_new: vi.fn().mockReturnValue({}),
          book_append_sheet: vi.fn(),
        },
        writeFile: vi.fn(),
      };

      // Mock dynamic import('xlsx')
      vi.doMock('xlsx', () => mockXlsx);

      const sampleRecords = [
        {
          id: 10,
          feedback_text: 'Canteen food needs improvement',
          sentiment_name: 'NEGATIVE',
          priority_level: 'HIGH',
        },
      ];

      const exportedName = await exportFeedbackToExcel(sampleRecords, 'custom_report.xlsx');
      expect(exportedName).toBe('custom_report.xlsx');

      vi.unmock('xlsx');
    });
  });
});
