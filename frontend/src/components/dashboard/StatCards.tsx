import { CircleCheckBig, EyeOff, History, ScanSearch, type LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { HistoryCounts } from "@/lib/types";

interface StatCardsProps {
  counts: HistoryCounts;
  searches: number | string | null;
}

/** The row of numbers at the top of the dashboard. */
export function StatCards({ counts, searches }: StatCardsProps) {
  const stats: { label: string; value: number | string; hint: string; icon: LucideIcon }[] = [
    { label: "Applied", value: counts.applied, hint: "Jobs you marked as applied", icon: CircleCheckBig },
    { label: "Seen", value: counts.seen, hint: "Jobs shown in your searches", icon: ScanSearch },
    { label: "Hidden", value: counts.hidden, hint: "Jobs you never want to see", icon: EyeOff },
    { label: "Searches", value: searches ?? "–", hint: "Manual and daily runs", icon: History },
  ];
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {stats.map(({ label, value, hint, icon: Icon }) => (
        <Card key={label} className="gap-0 py-0">
          <CardContent className="flex items-start justify-between gap-3 p-5">
            <div>
              <p className="text-sm font-medium text-muted-foreground">{label}</p>
              <p className="mt-1 text-3xl font-bold tabular-nums">{value}</p>
              <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
            </div>
            <span className="grid grid-cols-1 size-9 place-items-center rounded-lg bg-accent text-accent-foreground">
              <Icon className="size-4" aria-hidden="true" />
            </span>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
