"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { ClientManagementPanel } from "./ClientManagementPanel";
import { UserManagementPanel } from "./UserManagementPanel";

export type AccountsTab = "users" | "clients";

type Props = {
  open: boolean;
  onClose: () => void;
  initialTab?: AccountsTab;
};

const TABS: { id: AccountsTab; label: string }[] = [
  { id: "users", label: "Manage Users" },
  { id: "clients", label: "Add & Manage Clients" },
];

export function ManageAccountsModal({ open, onClose, initialTab = "users" }: Props) {
  const [tab, setTab] = useState<AccountsTab>(initialTab);

  useEffect(() => {
    if (open) setTab(initialTab);
  }, [open, initialTab]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-hidden rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-lg font-semibold text-gray-900">Manage Accounts</h2>
          <button type="button" onClick={onClose} className="rounded p-1 hover:bg-gray-100">
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="flex border-b border-gray-200 px-5">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`mr-6 border-b-2 py-3 text-sm font-medium transition ${
                tab === t.id
                  ? "border-primary text-primary"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
        {tab === "users" && (
          <UserManagementPanel active onUseAsMe={onClose} />
        )}
        {tab === "clients" && <ClientManagementPanel active />}
      </div>
    </div>
  );
}
