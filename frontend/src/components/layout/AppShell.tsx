"use client";

import { useState } from "react";

import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

import { AppSidebar } from "./AppSidebar";
import { Topbar } from "./Topbar";

const COLLAPSED_KEY = "job-search-sidebar-collapsed";

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

/** Sidebar + top bar around every app page. On phones the sidebar opens as a slide-in menu. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggle = () => {
    setCollapsed((current) => {
      try {
        window.localStorage.setItem(COLLAPSED_KEY, current ? "0" : "1");
      } catch {
        // storage blocked: the choice just isn't remembered
      }
      return !current;
    });
  };

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex min-h-svh">
        <aside className={cn("sticky top-0 hidden h-svh shrink-0 border-r bg-sidebar transition-[width] md:block", collapsed ? "w-16" : "w-60")}>
          <AppSidebar collapsed={collapsed} />
        </aside>
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar onToggleSidebar={toggle} onOpenMobileMenu={() => setMobileOpen(true)} />
          <main className="mx-auto w-full max-w-[1400px] flex-1 p-4 md:p-6">{children}</main>
        </div>
      </div>
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 bg-sidebar p-0">
          <SheetTitle className="sr-only">Menu</SheetTitle>
          <AppSidebar onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>
    </TooltipProvider>
  );
}
