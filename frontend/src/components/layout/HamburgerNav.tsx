"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { useState } from "react";
import { navItems, phase2NavItem } from "./navConfig";

export function HamburgerNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-lg p-2 text-gray-600 hover:bg-gray-100"
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40"
          onClick={() => setOpen(false)}
          aria-hidden
        />
      )}

      <aside
        className={`fixed left-0 top-0 z-50 flex h-full w-64 flex-col bg-sidebar text-gray-300 transition-transform duration-200 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-gray-800 px-5 py-5">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded bg-primary font-bold text-white">
              X
            </div>
            <span className="text-lg font-semibold text-white">Data Axle</span>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded p-1 hover:bg-gray-800"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {navItems.map((item) => {
            const active =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href.split("#")[0]));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={`block rounded-lg px-3 py-3 transition ${
                  active ? "bg-primary text-white" : "hover:bg-gray-800"
                }`}
              >
                <div className="flex items-start gap-3">
                  <Icon className="mt-0.5 h-5 w-5 shrink-0" />
                  <div>
                    <div className="text-sm font-medium">{item.label}</div>
                    <div
                      className={`text-xs ${active ? "text-orange-100" : "text-gray-500"}`}
                    >
                      {item.subtitle}
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
          <div className="mt-4 block cursor-not-allowed rounded-lg px-3 py-3 opacity-50">
            <div className="flex items-start gap-3">
              <phase2NavItem.icon className="mt-0.5 h-5 w-5 shrink-0" />
              <div>
                <div className="text-sm font-medium">{phase2NavItem.label}</div>
                <div className="text-xs text-gray-500">{phase2NavItem.subtitle}</div>
              </div>
            </div>
          </div>
        </nav>
      </aside>
    </>
  );
}
