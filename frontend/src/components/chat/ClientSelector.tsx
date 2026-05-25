"use client";

import { Client } from "@/lib/api";

type Props = {
  clients: Client[];
  value: string | null;
  onChange: (id: string) => void;
  onManageAccounts?: () => void;
};

export function ClientSelector({ clients, value, onChange, onManageAccounts }: Props) {
  return (
    <section className="border-b border-gray-200 bg-white px-4 py-2">
      <label className="mb-1 block text-xs font-medium text-gray-500">Client</label>
      <select
        className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select a client...</option>
        {clients.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>

      {clients.length === 0 && (
        <p className="mt-2 text-xs text-amber-700">
          No clients yet.{" "}
          {onManageAccounts ? (
            <>
              Open{" "}
              <button
                type="button"
                onClick={onManageAccounts}
                className="text-primary underline hover:no-underline"
              >
                Manage Accounts
              </button>{" "}
              to add a client and enable document upload.
            </>
          ) : (
            "Create one via Manage Accounts to enable document upload."
          )}
        </p>
      )}
    </section>
  );
}
