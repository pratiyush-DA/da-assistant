"use client";

import { Pin } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Document } from "@/lib/api";
import { getDocumentFileIcon } from "@/lib/documentFileIcon";

type Props = {
  documents: Document[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
};

function StatusChip({ status }: { status: Document["status"] }) {
  const styles = {
    processing: "bg-yellow-100 text-yellow-800",
    ready: "bg-green-100 text-green-800",
    error: "bg-red-100 text-red-800",
  };
  return (
    <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}

export function DocumentScopePicker({
  documents,
  selectedIds,
  onChange,
  disabled,
}: Props) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const readyDocs = documents.filter((d) => d.status === "ready");
  const allSelected =
    readyDocs.length > 0 && selectedIds.length === readyDocs.length;

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  const toggleSelectAll = () => {
    if (allSelected) {
      onChange([]);
    } else {
      onChange(readyDocs.map((d) => d.id));
    }
  };

  const toggleDoc = (id: string) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((x) => x !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  };

  const hasSelection = selectedIds.length > 0;

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className={`relative rounded-lg p-2 transition-colors disabled:opacity-50 ${
          hasSelection
            ? "bg-primary/10 text-primary hover:bg-primary/15"
            : "text-gray-500 hover:bg-gray-100"
        }`}
        aria-label="Select documents to search"
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <Pin className="h-5 w-5" />
        {hasSelection && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-white">
            {selectedIds.length}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute bottom-full left-0 z-50 mb-2 w-72 max-h-80 overflow-y-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
          role="listbox"
          aria-label="Document scope"
        >
          {readyDocs.length === 0 ? (
            <p className="px-3 py-4 text-center text-xs text-gray-500">
              No ready documents — upload files in the panel on the right.
            </p>
          ) : (
            <>
              <label className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm font-medium text-gray-900 hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleSelectAll}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                Select all files
              </label>
              <div className="my-1 border-t border-gray-100" />
              {documents.map((doc) => {
                const Icon = getDocumentFileIcon(doc.file_type);
                const isReady = doc.status === "ready";
                const checked = selectedIds.includes(doc.id);
                return (
                  <label
                    key={doc.id}
                    className={`flex cursor-pointer items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 ${
                      !isReady ? "cursor-not-allowed opacity-60" : ""
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={!isReady}
                      onChange={() => isReady && toggleDoc(doc.id)}
                      className="h-4 w-4 shrink-0 rounded border-gray-300 text-primary focus:ring-primary disabled:opacity-50"
                    />
                    <Icon className="h-4 w-4 shrink-0 text-gray-500" />
                    <span className="min-w-0 flex-1 truncate text-gray-800" title={doc.filename}>
                      {doc.filename}
                    </span>
                    {doc.status !== "ready" && <StatusChip status={doc.status} />}
                  </label>
                );
              })}
            </>
          )}
        </div>
      )}
    </div>
  );
}
