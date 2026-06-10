import {
  File,
  FileSpreadsheet,
  FileText,
  FileType,
  Table,
  type LucideIcon,
} from "lucide-react";

export function getDocumentFileIcon(fileType: string): LucideIcon {
  const ext = fileType.toLowerCase().replace(/^\./, "");
  switch (ext) {
    case "pdf":
    case "txt":
      return FileText;
    case "xlsx":
    case "xls":
    case "xlsm":
      return FileSpreadsheet;
    case "docx":
    case "doc":
      return FileType;
    case "csv":
      return Table;
    default:
      return File;
  }
}
