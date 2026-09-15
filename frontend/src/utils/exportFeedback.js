/**
 * CampusVoice Feedback Export Utility (Step 9.11)
 * 
 * Provides client-side CSV and Excel (.xlsx) file generation
 * for feedback intelligence records.
 * 
 * - RFC 4180 compliant CSV formatting with UTF-8 BOM
 * - Real .xlsx workbook generation using dynamically loaded SheetJS (xlsx)
 * - Safe NULL handling for legacy / unclassified records
 * - Sanitized, deterministic filenames
 */

/**
 * Generates a clean, sanitized export filename.
 * 
 * @param {'csv'|'xlsx'} extension - File extension without leading dot.
 * @returns {string} Sanitized filename (e.g., campusvoice_feedback_2026-09-14.csv).
 */
export function generateExportFilename(extension) {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const ext = extension.startsWith('.') ? extension.slice(1) : extension;
  return `campusvoice_feedback_${year}-${month}-${day}.${ext}`;
}

/**
 * Formats ISO timestamp to human-readable localized date/time.
 * Returns empty string if timestamp is invalid or null.
 * 
 * @param {string|null} isoString 
 * @returns {string}
 */
export function formatSubmittedDate(isoString) {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return '';
  }
}

/**
 * Escapes a single CSV field value according to RFC 4180 rules.
 * Handles commas, double quotes, and newlines.
 * 
 * @param {*} val - Cell value
 * @returns {string} Escaped CSV cell string
 */
export function escapeCSVField(val) {
  if (val === null || val === undefined) return '';
  const str = String(val);
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/**
 * Standardized 14-column header list for feedback exports.
 */
export const EXPORT_HEADERS = [
  'ID',
  'Department',
  'Semester',
  'Original Feedback',
  'Processed Text',
  'Sentiment',
  'Sentiment Label',
  'Sentiment Confidence',
  'Category',
  'Category Confidence',
  'Priority Level',
  'Priority Score',
  'Priority Reason',
  'Submitted',
];

/**
 * Transforms a raw API record object into an ordered array of 14 formatted cells.
 * Enforces safe NULL handling:
 * - Missing numerical values (confidence, score) -> empty string
 * - Missing metadata/text (department, semester, clean_text, reason) -> empty string
 * - Missing classifications -> 'Unclassified'
 * 
 * @param {Object} record - Feedback record object from database/API
 * @returns {Array} Array of cell values matching EXPORT_HEADERS
 */
export function transformRecordToRow(record) {
  if (!record || typeof record !== 'object') {
    return Array(EXPORT_HEADERS.length).fill('');
  }

  // ID
  const idVal = record.id !== null && record.id !== undefined ? record.id : '';

  // Department / Semester
  const deptVal = record.department || '';
  const semVal = record.semester || '';

  // Original & Processed Text
  const origText = record.feedback_text || '';
  const cleanText = record.clean_text || '';

  // Sentiment
  const sentimentVal = record.sentiment_name || 'Unclassified';
  const sentimentLabel = record.sentiment_label || '';
  const sentimentConf = typeof record.sentiment_confidence === 'number' && !isNaN(record.sentiment_confidence)
    ? `${(record.sentiment_confidence * 100).toFixed(1)}%`
    : '';

  // Category
  const categoryVal = record.category_name || 'Unclassified';
  const categoryConf = typeof record.category_confidence === 'number' && !isNaN(record.category_confidence)
    ? `${(record.category_confidence * 100).toFixed(1)}%`
    : '';

  // Priority
  const priorityLevel = record.priority_level ? record.priority_level.toUpperCase() : 'Unclassified';
  const priorityScore = typeof record.priority_score === 'number' && !isNaN(record.priority_score)
    ? record.priority_score
    : '';
  const priorityReason = record.priority_reason || '';

  // Submitted
  const submittedVal = formatSubmittedDate(record.created_at);

  return [
    idVal,
    deptVal,
    semVal,
    origText,
    cleanText,
    sentimentVal,
    sentimentLabel,
    sentimentConf,
    categoryVal,
    categoryConf,
    priorityLevel,
    priorityScore,
    priorityReason,
    submittedVal,
  ];
}

/**
 * Triggers a browser file download using a temporary Blob Object URL.
 * Cleans up the Object URL after download starts.
 * 
 * @param {Blob} blob 
 * @param {string} filename 
 */
function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 1000);
}

/**
 * Exports feedback records to a downloadable CSV file.
 * 
 * @param {Array<Object>} records - Array of feedback record items
 * @param {string} [customFilename] - Optional custom filename
 * @returns {string} Downloaded filename
 * @throws {Error} If records array is empty or undefined
 */
export function exportFeedbackToCSV(records, customFilename) {
  if (!records || !Array.isArray(records) || records.length === 0) {
    throw new Error('No records to export.');
  }

  const filename = customFilename || generateExportFilename('csv');

  // Build CSV string with UTF-8 BOM
  const csvRows = [];
  csvRows.push(EXPORT_HEADERS.map(escapeCSVField).join(','));

  records.forEach((record) => {
    const row = transformRecordToRow(record);
    csvRows.push(row.map(escapeCSVField).join(','));
  });

  const csvString = '\uFEFF' + csvRows.join('\r\n');
  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });

  triggerBlobDownload(blob, filename);
  return filename;
}

/**
 * Exports feedback records to a downloadable Excel (.xlsx) file using dynamically imported SheetJS.
 * The heavy xlsx library is only downloaded when the user invokes this function.
 * 
 * @param {Array<Object>} records - Array of feedback record items
 * @param {string} [customFilename] - Optional custom filename
 * @returns {Promise<string>} Downloaded filename
 * @throws {Error} If records array is empty or undefined, or if module loading fails
 */
export async function exportFeedbackToExcel(records, customFilename) {
  if (!records || !Array.isArray(records) || records.length === 0) {
    throw new Error('No records to export.');
  }

  let XLSX;
  try {
    XLSX = await import('xlsx');
  } catch (err) {
    throw new Error('Unable to load Excel export engine. Please check your connection and try again.');
  }

  const filename = customFilename || generateExportFilename('xlsx');

  const rows = records.map(transformRecordToRow);
  const aoaData = [EXPORT_HEADERS, ...rows];

  const ws = XLSX.utils.aoa_to_sheet(aoaData);

  // Set readable column widths
  ws['!cols'] = [
    { wch: 8 },   // ID
    { wch: 18 },  // Department
    { wch: 12 },  // Semester
    { wch: 45 },  // Original Feedback
    { wch: 40 },  // Processed Text
    { wch: 16 },  // Sentiment
    { wch: 16 },  // Sentiment Label
    { wch: 20 },  // Sentiment Confidence
    { wch: 24 },  // Category
    { wch: 20 },  // Category Confidence
    { wch: 16 },  // Priority Level
    { wch: 14 },  // Priority Score
    { wch: 40 },  // Priority Reason
    { wch: 22 },  // Submitted
  ];

  // Freeze header row
  ws['!freeze'] = { xSplit: 0, ySplit: 1 };

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Feedback Records');

  XLSX.writeFile(wb, filename);
  return filename;
}
