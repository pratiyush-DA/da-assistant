import { ReactNode } from "react";
import { AppShellLayout } from "./AppShellLayout";

export function AppShell({ children }: { children: ReactNode }) {
  return <AppShellLayout>{children}</AppShellLayout>;
}
