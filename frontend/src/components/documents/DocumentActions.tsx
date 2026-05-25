"use client";

import { useRef, useState } from "react";
import { Document, deleteDocument, reuploadDocument } from "@/lib/api";

type Props = {
  document: Document;
  clientId: string;
  onRefresh: () => void;
};

export function DocumentActions({ document, clientId, onRefresh }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Delete "${document.filename}"?`)) return;
    setBusy(true);
    try {
      await deleteDocument(document.id);
      onRefresh();
    } finally {
      setBusy(false);
    }
  };

  const handleReupload = async (file: File) => {
    setBusy(true);
    try {
      await reuploadDocument(document.id, clientId, file);
      onRefresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex gap-1">
      <input
        ref={fileRef}
        type="file"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleReupload(f);
          e.target.value = "";
        }}
      />
      <button
        type="button"
        disabled={busy}
        onClick={() => fileRef.current?.click()}
        className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-100"
      >
        Re-upload
      </button>
      <button
        type="button"
        disabled={busy}
        onClick={handleDelete}
        className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50"
      >
        Delete
      </button>
    </div>
  );
}
