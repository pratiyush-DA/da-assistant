import { ReactNode } from "react";
import { TopHeader } from "./TopHeader";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <TopHeader />
      <main className="flex-1 overflow-auto bg-page p-4 lg:p-6">{children}</main>
    </div>
  );
}
