"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Client, createClient, fetchClients } from "@/lib/api";
import { useClientContext } from "@/context/ClientContext";

type Props = {
  active: boolean;
};

export function ClientManagementPanel({ active }: Props) {
  const { clientId, setClientId } = useClientContext();
  const [clients, setClients] = useState<Client[]>([]);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchClients();
      setClients(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load clients");
    }
  }, []);

  useEffect(() => {
    if (active) load();
  }, [active, load]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    setError(null);
    try {
      const client = await createClient(name);
      setNewName("");
      await load();
      setClientId(client.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create client");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-h-[60vh] overflow-y-auto p-5">
      <form
        onSubmit={handleCreate}
        className="mb-6 space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4"
      >
        <p className="text-xs font-medium text-gray-500">Add new client</p>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="New client name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={creating || !newName.trim()}
            className="rounded-lg bg-primary px-4 py-2 text-sm text-white hover:bg-primary-hover disabled:opacity-50"
          >
            {creating ? "Adding…" : "Add"}
          </button>
        </div>
        {error && <p className="text-xs text-red-600">{error}</p>}
      </form>
      <ul className="divide-y divide-gray-100">
        {clients.length === 0 && (
          <li className="py-3 text-sm text-gray-500">No clients yet. Add one above.</li>
        )}
        {clients.map((c) => (
          <li key={c.id} className="flex items-center justify-between gap-2 py-3">
            <p
              className={`truncate text-sm font-medium ${
                clientId === c.id ? "text-primary" : "text-gray-900"
              }`}
            >
              {c.name}
            </p>
            <button
              type="button"
              onClick={() => setClientId(c.id)}
              className={`shrink-0 text-xs hover:underline ${
                clientId === c.id ? "font-medium text-primary" : "text-gray-600"
              }`}
            >
              {clientId === c.id ? "Selected" : "Select"}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
