"use client";

import ReactMarkdown from "react-markdown";

export type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Array<{
    section_header?: string;
    page_number?: number | null;
    source?: string;
    display_label?: string;
    chunk_type?: string;
  }>;
};

function formatSourceLabel(s: NonNullable<Message["sources"]>[number]): string {
  if (s.display_label?.trim()) return s.display_label.trim();
  if (s.source?.trim()) return s.source.trim();
  if (s.section_header?.trim()) return s.section_header.trim();
  if (s.page_number != null) return `page ${s.page_number}`;
  return "Source";
}

function stripDuplicateSourcesSection(content: string): string {
  return content.replace(/\n##\s*Sources\b[\s\S]*$/i, "").trimEnd();
}

function uniqueSourceLabels(sources: NonNullable<Message["sources"]>): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const s of sources) {
    const label = formatSourceLabel(s);
    if (seen.has(label)) continue;
    seen.add(label);
    out.push(label);
  }
  return out;
}

type Props = {
  messages: Message[];
  loading?: boolean;
};

export function MessageThread({ messages, loading }: Props) {
  return (
    <div className="flex-1 space-y-4 overflow-y-auto p-4">
      {messages.length === 0 && (
        <p className="text-center text-sm text-gray-400">
          Select a client and ask a question about their documents.
        </p>
      )}
      {messages.map((msg, i) => (
        <div
          key={i}
          className={`max-w-[90%] rounded-lg px-4 py-3 text-sm ${
            msg.role === "user"
              ? "ml-auto bg-primary text-white"
              : "mr-auto border border-gray-200 bg-white text-gray-800"
          }`}
        >
          {msg.role === "assistant" ? (
            <ReactMarkdown className="prose prose-sm max-w-none">
              {msg.sources && msg.sources.length > 0
                ? stripDuplicateSourcesSection(msg.content)
                : msg.content}
            </ReactMarkdown>
          ) : (
            <p className="whitespace-pre-wrap">{msg.content}</p>
          )}
          {msg.sources && msg.sources.length > 0 && (
            <div className="mt-2 border-t border-gray-100 pt-2 text-xs text-gray-500">
              Sources: {uniqueSourceLabels(msg.sources).join("; ")}
            </div>
          )}
        </div>
      ))}
      {loading && (
        <div className="mr-auto rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm text-gray-500">
          Thinking…
        </div>
      )}
    </div>
  );
}
