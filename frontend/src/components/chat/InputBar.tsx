"use client";

import { Send } from "lucide-react";
import { FormEvent, useRef } from "react";
import { Document } from "@/lib/api";
import { DocumentScopePicker } from "./DocumentScopePicker";

type Props = {
  disabled?: boolean;
  documents: Document[];
  selectedDocumentIds: string[];
  onSelectionChange: (ids: string[]) => void;
  scopeRequired?: boolean;
  onSend: (message: string) => void;
};

export function InputBar({
  disabled,
  documents,
  selectedDocumentIds,
  onSelectionChange,
  scopeRequired = true,
  onSend,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  const needsScope = scopeRequired && selectedDocumentIds.length === 0;
  const sendDisabled = disabled || needsScope;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const value = inputRef.current?.value.trim();
    if (!value || sendDisabled) return;
    onSend(value);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 border-t border-gray-200 bg-white p-4"
    >
      <DocumentScopePicker
        documents={documents}
        selectedIds={selectedDocumentIds}
        onChange={onSelectionChange}
        disabled={disabled}
      />
      <input
        ref={inputRef}
        type="text"
        placeholder={
          needsScope ? "Select documents to search…" : "Ask about your documents…"
        }
        disabled={disabled}
        className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:bg-gray-50"
      />
      <button
        type="submit"
        disabled={sendDisabled}
        className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-50"
      >
        <Send className="h-4 w-4" />
        Send
      </button>
    </form>
  );
}
