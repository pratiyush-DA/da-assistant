"use client";

import { NavPanel } from "./NavPanel";

export function Sidebar() {
  return (
    <aside className="flex h-screen w-64 flex-col bg-sidebar text-gray-300">
      <NavPanel className="h-full" />
    </aside>
  );
}
