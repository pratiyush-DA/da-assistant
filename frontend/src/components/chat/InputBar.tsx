"use client";

import { Paperclip, Send } from "lucide-react";
import { FormEvent, useRef } from "react";
import { ACCEPTED_FILE_INPUT } from "@/lib/acceptedFileTypes";

type Props = {
  disabled?: boolean;
  onSend: (message: string) => void;
  onAttach?: (file: File) => void;
};

export function InputBar({ disabled, onSend, onAttach }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const value = inputRef.current?.value.trim();
    if (!value || disabled) return;
    onSend(value);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 border-t border-gray-200 bg-white p-4"
    >
      <input
        ref={fileRef}
        type="file"
        accept={ACCEPTED_FILE_INPUT}
        className="hidden"
        onChange={(e) => {
        const file = e.target.files?.[0];
        if (file && onAttach) onAttach(file);
        e.target.value = "";
      }} />
      <button
        type="button"
        disabled={disabled}
        onClick={() => fileRef.current?.click()}
        className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 disabled:opacity-50"
        aria-label="Attach file"
      >
        <Paperclip className="h-5 w-5" />
      </button>
      <input
        ref={inputRef}
        type="text"
        placeholder="Ask about your documents…"
        disabled={disabled}
        className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:bg-gray-50"
      />
      <button
        type="submit"
        disabled={disabled}
        className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-50"
      >
        <Send className="h-4 w-4" />
        Send
      </button>
    </form>
  );
}
