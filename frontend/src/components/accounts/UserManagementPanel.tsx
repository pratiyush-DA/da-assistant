"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { User, createUser, fetchUsers } from "@/lib/api";
import { useUserContext } from "@/context/UserContext";

const EMAIL_SUFFIX = "@data-axle.com";

type Props = {
  active: boolean;
  onUseAsMe?: () => void;
};

export function UserManagementPanel({ active, onUseAsMe }: Props) {
  const { setUserId, refreshUser } = useUserContext();
  const [users, setUsers] = useState<User[]>([]);
  const [filter, setFilter] = useState("");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    const data = await fetchUsers(filter || undefined);
    setUsers(data);
  }, [filter]);

  useEffect(() => {
    if (active) load();
  }, [active, load]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const local = email.trim();
    const fullEmail = local.includes("@") ? local : `${local}${EMAIL_SUFFIX}`;
    if (!fullEmail.toLowerCase().endsWith(EMAIL_SUFFIX)) {
      setError(`Email must end with ${EMAIL_SUFFIX}`);
      return;
    }
    setLoading(true);
    try {
      await createUser(fullEmail, displayName.trim());
      setEmail("");
      setDisplayName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-h-[60vh] overflow-y-auto p-5">
      <form
        onSubmit={handleCreate}
        className="mb-6 space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4"
      >
        <p className="text-xs font-medium text-gray-500">Register user</p>
        <input
          type="text"
          placeholder={`name${EMAIL_SUFFIX}`}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        <input
          type="text"
          placeholder="Display name"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        {error && <p className="text-xs text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading || !email.trim() || !displayName.trim()}
          className="rounded-lg bg-primary px-4 py-2 text-sm text-white hover:bg-primary-hover disabled:opacity-50"
        >
          Add user
        </button>
      </form>
      <input
        type="search"
        placeholder="Filter users…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="mb-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
      />
      <ul className="divide-y divide-gray-100">
        {users.map((u) => (
          <li key={u.id} className="flex items-center justify-between gap-2 py-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-gray-900">{u.display_name}</p>
              <p className="truncate text-xs text-gray-500">{u.email}</p>
            </div>
            <button
              type="button"
              onClick={() => {
                setUserId(u.id);
                refreshUser();
                onUseAsMe?.();
              }}
              className="shrink-0 text-xs text-primary hover:underline"
            >
              Use as me
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
