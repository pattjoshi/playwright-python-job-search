"use client";

import { Menu, PanelLeft } from "lucide-react";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";

import { findNavItem } from "./nav";
import { SearchStatusChip } from "./SearchStatusChip";
import { ThemeToggle } from "./ThemeToggle";

interface TopbarProps {
  onToggleSidebar: () => void;
  onOpenMobileMenu: () => void;
}

export function Topbar({ onToggleSidebar, onOpenMobileMenu }: TopbarProps) {
  const pathname = usePathname();
  const page = findNavItem(pathname);
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b bg-background/80 px-3 backdrop-blur md:px-4">
      <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu" onClick={onOpenMobileMenu}>
        <Menu className="size-5" />
      </Button>
      <Button variant="ghost" size="icon" className="hidden md:inline-flex" aria-label="Toggle sidebar" onClick={onToggleSidebar}>
        <PanelLeft className="size-4" />
      </Button>
      <h1 className="truncate text-base font-semibold">{page?.label ?? "Job Search"}</h1>
      <div className="ml-auto flex items-center gap-1">
        <SearchStatusChip />
        <ThemeToggle />
      </div>
    </header>
  );
}
