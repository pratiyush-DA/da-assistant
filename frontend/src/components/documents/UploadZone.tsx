"use client";

import { useCallback, useState } from "react";
import { Upload } from "lucide-react";
import { ACCEPTED_FILE_INPUT, UPLOAD_HELP_TEXT } from "@/lib/acceptedFileTypes";
import { uploadDocument } from "@/lib/api";

type Props = {
  clientId: string | null;
  onUploaded: () => void;
};

export function UploadZone({ clientId, onUploaded }: Props) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!clientId || !files?.length) return;
      setUploading(true);
      setError(null);
      try {
        for (const file of Array.from(files)) {
          await uploadDocument(clientId, file);
        }
        onUploaded();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [clientId, onUploaded],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      className={`rounded-xl border-2 border-dashed p-6 text-center transition ${
        dragging ? "border-primary bg-orange-50" : "border-gray-200 bg-gray-50"
      } ${!clientId ? "opacity-50" : ""}`}
    >
      <Upload className="mx-auto h-8 w-8 text-gray-400" />
      <p className="mt-2 text-sm text-gray-600">
        {clientId ? "Drag & drop files here" : "Select a client first"}
      </p>
      <p className="text-xs text-gray-400">{UPLOAD_HELP_TEXT}</p>
      <label className="mt-3 inline-block cursor-pointer rounded-lg bg-primary px-4 py-2 text-sm text-white hover:bg-primary-hover">
        {uploading ? "Uploading…" : "Browse files"}
        <input
          type="file"
          multiple
          accept={ACCEPTED_FILE_INPUT}
          className="hidden"
          disabled={!clientId || uploading}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </label>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}
