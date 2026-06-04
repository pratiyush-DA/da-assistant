"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopHeader } from "./TopHeader";

export function AppShellLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isHome = pathname === "/";

  if (isHome) {
    return (
      <div className="flex min-h-screen">
        <aside className="hidden lg:flex lg:w-64 lg:shrink-0">
          <Sidebar />
        </aside>
        <div className="flex min-w-0 flex-1 flex-col">
          <TopHeader hamburgerMode="home" />
          <main className="flex-1 overflow-auto bg-page p-4 lg:p-6">{children}</main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <TopHeader hamburgerMode="always" />
      <main className="flex-1 overflow-auto bg-page p-4 lg:p-6">{children}</main>
    </div>
  );
}
