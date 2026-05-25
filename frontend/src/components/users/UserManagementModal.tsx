"use client";

import { ManageAccountsModal } from "@/components/accounts/ManageAccountsModal";

type Props = {
  open: boolean;
  onClose: () => void;
};

/** @deprecated Use ManageAccountsModal directly */
export function UserManagementModal({ open, onClose }: Props) {
  return <ManageAccountsModal open={open} onClose={onClose} initialTab="users" />;
}
