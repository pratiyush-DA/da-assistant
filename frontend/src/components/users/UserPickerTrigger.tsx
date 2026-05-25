"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { User, searchUsers } from "@/lib/api";
import { useUserContext } from "@/context/UserContext";

export function UserPickerTrigger() {
  const { userId, user, setUserId, refreshUser } = useUserContext();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const runSearch = useCallback(async (q: string) => {
    setLoading(true);
    try {
      const data = await searchUsers(q);
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSearch(query), 200);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, open, runSearch]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const select = (u: User) => {
    setUserId(u.id);
    refreshUser();
    setQuery("");
    setOpen(false);
  };

  const label = user?.display_name
    ? `Welcome, ${user.display_name}`
    : "Select user";

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => {
          setOpen((v) => !v);
          if (!open) {
            setQuery("");
            runSearch("");
          }
        }}
        className="inline-flex items-center gap-1 text-sm text-gray-700 hover:text-primary"
      >
        <span>{label}</span>
        <ChevronDown className={`h-4 w-4 transition ${open ? "rotate-180" : ""}`} />
      </button>
      {!userId && (
        <span className="ml-2 text-xs text-amber-600">(required for chat history)</span>
      )}
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-72 rounded-lg border border-gray-200 bg-white shadow-lg">
          <div className="border-b p-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name or email…"
              autoFocus
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <ul className="max-h-48 overflow-auto py-1">
            {loading && (
              <li className="px-3 py-2 text-xs text-gray-400">Searching…</li>
            )}
            {!loading && results.length === 0 && (
              <li className="px-3 py-2 text-xs text-gray-400">No users found</li>
            )}
            {results.map((u) => (
              <li key={u.id}>
                <button
                  type="button"
                  onClick={() => select(u)}
                  className={`w-full px-3 py-2 text-left text-sm hover:bg-orange-50 ${
                    userId === u.id ? "bg-orange-50 font-medium" : ""
                  }`}
                >
                  <span className="block text-gray-900">{u.display_name}</span>
                  <span className="block text-xs text-gray-500">{u.email}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
