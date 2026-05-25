import { Bot, GitBranch, Home, MessageSquare, LucideIcon } from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  subtitle: string;
  icon: LucideIcon;
  disabled?: boolean;
};

export const navItems: NavItem[] = [
  { href: "/", label: "Home", subtitle: "Dashboard overview", icon: Home },
  {
    href: "/assistant",
    label: "Business Assistant",
    subtitle: "RAG chat & documents",
    icon: Bot,
  },
  {
    href: "/assistant#documents",
    label: "Document Manager",
    subtitle: "Upload & manage files",
    icon: MessageSquare,
  },
];

export const phase2NavItem: NavItem = {
  href: "#",
  label: "SQL Lineage Explorer",
  subtitle: "Phase 2 — coming soon",
  icon: GitBranch,
  disabled: true,
};
