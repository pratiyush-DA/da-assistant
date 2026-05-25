export const ACCEPTED_FILE_EXTENSIONS =
  ".pdf,.docx,.xlsx,.xlsm,.xls,.csv,.txt";

export const ACCEPTED_FILE_MIME =
  "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,text/csv,text/plain";

export const ACCEPTED_FILE_INPUT = `${ACCEPTED_FILE_EXTENSIONS},${ACCEPTED_FILE_MIME}`;

export const UPLOAD_HELP_TEXT =
  "PDF, DOCX, TXT · XLSX, XLS, CSV (sheet-aware table indexing)";
