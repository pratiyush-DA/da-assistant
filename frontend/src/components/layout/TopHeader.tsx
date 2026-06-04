"use client";

import Link from "next/link";
import { useState } from "react";
import { ManageAccountsModal } from "@/components/accounts/ManageAccountsModal";
import { UserPickerTrigger } from "@/components/users/UserPickerTrigger";
import { HamburgerNav } from "./HamburgerNav";

type Props = {
  hamburgerMode?: "always" | "home";
};

export function TopHeader({ hamburgerMode = "always" }: Props) {
  const [accountsOpen, setAccountsOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6">
        <div className="flex items-center gap-3">
          <div className={hamburgerMode === "home" ? "lg:hidden" : undefined}>
            <HamburgerNav />
          </div>
          <Link
            href="/"
            className="text-sm font-medium text-gray-500 hover:text-primary lg:hidden"
          >
            Data Axle
          </Link>
        </div>
        <div className="flex items-center gap-6">
          <button
            type="button"
            onClick={() => setAccountsOpen(true)}
            className="text-sm text-gray-500 hover:text-primary"
          >
            Manage Accounts
          </button>
          <button type="button" className="text-sm text-gray-500 hover:text-primary">
            Feedback
          </button>
          <UserPickerTrigger />
        </div>
      </header>
      <ManageAccountsModal open={accountsOpen} onClose={() => setAccountsOpen(false)} />
    </>
  );
}
