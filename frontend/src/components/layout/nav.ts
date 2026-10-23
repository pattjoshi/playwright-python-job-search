import {
  BookOpenText,
  Bot,
  BriefcaseBusiness,
  LayoutDashboard,
  type LucideIcon,
  NotebookPen,
  Search,
  Settings,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  description: string;
  icon: LucideIcon;
  /** Set for pages that arrive in a later phase of the roadmap. */
  soon?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", description: "Your job search at a glance", icon: LayoutDashboard },
  { href: "/search", label: "Search jobs", description: "Find and rank recent jobs from your resume", icon: Search },
  { href: "/applications", label: "Applications", description: "Track every job you apply to", icon: BriefcaseBusiness },
  { href: "/auto-apply", label: "Auto-apply", description: "Apply to matching jobs automatically", icon: Bot, soon: true },
  { href: "/answers", label: "Answer Bank", description: "Answers to application questions", icon: BookOpenText, soon: true },
  { href: "/notes", label: "Notes", description: "Interview prep and research notes", icon: NotebookPen, soon: true },
];

export const SETTINGS_ITEM: NavItem = {
  href: "/settings", label: "Settings", description: "Appearance, AI key and your data", icon: Settings,
};

export function findNavItem(pathname: string): NavItem | undefined {
  return [...NAV_ITEMS, SETTINGS_ITEM].find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
}
