"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { X } from "lucide-react";
import { navItems, phase2NavItem } from "./navConfig";

type Props = {
  onNavigate?: () => void;
  onClose?: () => void;
  className?: string;
};

export function NavPanel({ onNavigate, onClose, className = "" }: Props) {
  const pathname = usePathname();

  return (
    <div className={`flex flex-col ${className}`}>
      <div className="flex items-center justify-between border-b border-gray-800 px-5 py-5">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary font-bold text-white">
            X
          </div>
          <span className="text-lg font-semibold text-white">Data Axle</span>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 hover:bg-gray-800"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        )}
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
              onClick={onNavigate}
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
        <div
          className="mt-4 block cursor-not-allowed rounded-lg px-3 py-3 opacity-50"
          title="Phase 2"
        >
          <div className="flex items-start gap-3">
            <phase2NavItem.icon className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <div className="text-sm font-medium">{phase2NavItem.label}</div>
              <div className="text-xs text-gray-500">{phase2NavItem.subtitle}</div>
            </div>
          </div>
        </div>
      </nav>
    </div>
  );
}
