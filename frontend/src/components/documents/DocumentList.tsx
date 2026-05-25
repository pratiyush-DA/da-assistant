"use client";

import { Document } from "@/lib/api";
import { DocumentActions } from "./DocumentActions";
import { DocumentRowTooltip } from "./DocumentRowTooltip";

function StatusBadge({ status }: { status: Document["status"] }) {
  const styles = {
    processing: "bg-yellow-100 text-yellow-800",
    ready: "bg-green-100 text-green-800",
    error: "bg-red-100 text-red-800",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}

type Props = {
  documents: Document[];
  clientId: string;
  onRefresh: () => void;
};

export function DocumentList({ documents, clientId, onRefresh }: Props) {
  if (documents.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-gray-400">No documents uploaded yet.</p>
    );
  }

  return (
    <ul className="divide-y divide-gray-100">
      {documents.map((doc) => (
        <li key={doc.id} className="flex items-center justify-between gap-2 py-3">
          <DocumentRowTooltip
            filename={doc.filename}
            chunkCount={doc.chunk_count}
            fileSizeBytes={doc.file_size_bytes}
          >
            <p className="truncate text-sm font-medium text-gray-900">{doc.filename}</p>
            <p className="text-xs text-gray-500">
              {new Date(doc.uploaded_at).toLocaleDateString()} · {doc.chunk_count} chunks
            </p>
          </DocumentRowTooltip>
          <div className="flex shrink-0 items-center gap-2">
            <StatusBadge status={doc.status} />
            <DocumentActions document={doc} clientId={clientId} onRefresh={onRefresh} />
          </div>
        </li>
      ))}
    </ul>
  );
}
