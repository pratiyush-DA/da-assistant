"use client";

import { Plus, Trash2 } from "lucide-react";
import { Conversation } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";

type Props = {
  conversations: Conversation[];
  activeId: string | null;
  disabled: boolean;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onDelete?: (id: string) => void;
};

export function ChatHistoryPanel({
  conversations,
  activeId,
  disabled,
  onSelect,
  onNewChat,
  onDelete,
}: Props) {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-gray-200 bg-gray-50">
      <div className="flex items-center justify-between border-b border-gray-200 px-3 py-3">
        <h2 className="text-sm font-semibold text-gray-800">Chat history</h2>
        <button
          type="button"
          onClick={onNewChat}
          disabled={disabled}
          className="inline-flex items-center gap-1 rounded-lg bg-primary px-2 py-1 text-xs text-white hover:bg-primary-hover disabled:opacity-50"
          title="New chat"
        >
          <Plus className="h-3.5 w-3.5" />
          New
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {disabled && (
          <p className="px-2 py-4 text-center text-xs text-gray-400">
            Select client and user
          </p>
        )}
        {!disabled && conversations.length === 0 && (
          <p className="px-2 py-4 text-center text-xs text-gray-400">No chats yet</p>
        )}
        <ul className="space-y-1">
          {conversations.map((c) => (
            <li key={c.id}>
              <div
                className={`group flex items-start gap-1 rounded-lg px-2 py-2 ${
                  activeId === c.id
                    ? "bg-white shadow-sm ring-1 ring-primary/30"
                    : "hover:bg-white"
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelect(c.id)}
                  className="min-w-0 flex-1 text-left"
                >
                  <p className="truncate text-sm font-medium text-gray-900">{c.title}</p>
                  <p className="text-xs text-gray-500">{formatRelativeTime(c.updated_at)}</p>
                </button>
                {onDelete && (
                  <button
                    type="button"
                    onClick={() => onDelete(c.id)}
                    className="shrink-0 rounded p-1 text-gray-400 opacity-0 hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
                    title="Delete chat"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
