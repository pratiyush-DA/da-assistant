"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, GitBranch, Home, MessageSquare } from "lucide-react";

const navItems = [
  { href: "/", label: "Home", subtitle: "Dashboard overview", icon: Home },
  { href: "/assistant", label: "Business Assistant", subtitle: "RAG chat & documents", icon: Bot },
  {
    href: "/assistant#documents",
    label: "Document Manager",
    subtitle: "Upload & manage files",
    icon: MessageSquare,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-64 flex-col bg-sidebar text-gray-300">
      <div className="flex items-center gap-2 border-b border-gray-800 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded bg-primary font-bold text-white">
          X
        </div>
        <span className="text-lg font-semibold text-white">Data Axle</span>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href.split("#")[0]));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block rounded-lg px-3 py-3 transition ${
                active ? "bg-primary text-white" : "hover:bg-gray-800"
              }`}
            >
              <div className="flex items-start gap-3">
                <Icon className="mt-0.5 h-5 w-5 shrink-0" />
                <div>
                  <div className="text-sm font-medium">{item.label}</div>
                  <div className={`text-xs ${active ? "text-orange-100" : "text-gray-500"}`}>
                    {item.subtitle}
                  </div>
                </div>
              </div>
            </Link>
          );
        })}
        <div
          className="mt-4 block cursor-not-allowed rounded-lg px-3 py-3 opacity-50"
          title="Phase 2"
        >
          <div className="flex items-start gap-3">
            <GitBranch className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <div className="text-sm font-medium">SQL Lineage Explorer</div>
              <div className="text-xs text-gray-500">Phase 2 — coming soon</div>
            </div>
          </div>
        </div>
      </nav>
    </aside>
  );
}
