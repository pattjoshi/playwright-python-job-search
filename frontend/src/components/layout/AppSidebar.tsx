"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useConfig } from "@/providers/ConfigProvider";

import { LOCAL_ONLY_PATHS, NAV_ITEMS, type NavItem, SETTINGS_ITEM } from "./nav";

interface AppSidebarProps {
  collapsed?: boolean;
  onNavigate?: () => void;
}

/** The left navigation. `collapsed` shows icons only (with tooltips). */
export function AppSidebar({ collapsed = false, onNavigate }: AppSidebarProps) {
  const { config } = useConfig();
  const items = config.hosted ? NAV_ITEMS.filter((item) => !LOCAL_ONLY_PATHS.includes(item.href)) : NAV_ITEMS;
  return (
    <nav aria-label="Main" className="flex h-full flex-col gap-1 p-3">
      <Link href="/dashboard" onClick={onNavigate} className={cn("mb-4 flex items-center gap-2.5 px-2 py-1", collapsed && "justify-center px-0")}>
        <span className="grid grid-cols-1 size-8 shrink-0 place-items-center rounded-lg bg-primary text-[15px] font-bold text-primary-foreground">J</span>
        {!collapsed ? <span className="text-base font-bold">Job Search</span> : null}
      </Link>
      {items.map((item) => <SidebarLink key={item.href} item={item} collapsed={collapsed} onNavigate={onNavigate} />)}
      <div className="mt-auto flex flex-col gap-1 border-t border-sidebar-border pt-3">
        <SidebarLink item={SETTINGS_ITEM} collapsed={collapsed} onNavigate={onNavigate} />
        {!collapsed ? (
          <p className="px-2.5 pt-2 text-xs text-muted-foreground">{config.hosted ? "Online · Search runs on your computer" : "Runs on your computer · private"}</p>
        ) : null}
      </div>
    </nav>
  );
}

function SidebarLink({ item, collapsed, onNavigate }: { item: NavItem; collapsed: boolean; onNavigate?: () => void }) {
  const pathname = usePathname();
  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
  const Icon = item.icon;
  const link = (
    <Link
      href={item.href} onClick={onNavigate} aria-current={active ? "page" : undefined}
      className={cn(
        "flex h-9 items-center gap-2.5 rounded-md px-2.5 text-sm font-medium text-sidebar-foreground/80 transition-colors",
        "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        active && "bg-sidebar-accent text-sidebar-accent-foreground",
        collapsed && "justify-center px-0",
      )}
    >
      <Icon className="size-4 shrink-0" aria-hidden="true" />
      {collapsed ? <span className="sr-only">{item.label}</span> : <span className="flex-1 truncate">{item.label}</span>}
      {!collapsed && item.soon ? <Badge variant="secondary" className="px-1.5 py-0 text-[10px]">Soon</Badge> : null}
    </Link>
  );
  if (!collapsed) return link;
  return (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      <TooltipContent side="right">{item.label}{item.soon ? " (soon)" : ""}</TooltipContent>
    </Tooltip>
  );
}
