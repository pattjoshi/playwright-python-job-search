"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Spinner } from "@/components/ui/spinner";
import { formatClock } from "@/lib/format";
import { useSearchSession } from "@/providers/SearchSessionProvider";

/** While a search runs, shows "Searching · 1:23" in the top bar on every page (links to it). */
export function SearchStatusChip() {
  const { search } = useSearchSession();
  const pathname = usePathname();
  if (search.view !== "running" || pathname === "/search") return null;
  return (
    <Link
      href="/search"
      className="mr-1 inline-flex items-center gap-2 rounded-full bg-accent px-3 py-1 text-xs font-semibold text-accent-foreground"
    >
      <Spinner className="size-3.5" aria-hidden="true" />
      Searching · {formatClock(search.elapsed)}
    </Link>
  );
}
