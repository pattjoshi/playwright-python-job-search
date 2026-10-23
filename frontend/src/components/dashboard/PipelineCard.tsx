import Link from "next/link";

import { shortDate, STATUSES } from "@/components/applications/statuses";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ApplicationStats } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Applications per status, and how many you applied to each day for the last two weeks. */
export function PipelineCard({ stats, error }: { stats: ApplicationStats | null; error: string | null }) {
  const days = stats?.per_day ?? [];
  const most = Math.max(1, ...days.map((day) => day.count));
  const applied = days.reduce((sum, day) => sum + day.count, 0);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Applications</CardTitle>
        <CardDescription>{stats ? `${stats.total} tracked · ${applied} applied in the last 14 days` : "Your pipeline"}</CardDescription>
        <CardAction>
          <Button asChild variant="outline" size="sm"><Link href="/applications">Open tracker</Link></Button>
        </CardAction>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-5">
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        {!stats && !error ? <Skeleton className="h-32" /> : null}
        {stats ? (
          <>
            <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-7">
              {STATUSES.map((status) => (
                <li key={status.id} className="rounded-lg border p-2.5">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span className={cn("size-2 rounded-full", status.dot)} aria-hidden="true" />
                    {status.label}
                  </div>
                  <div className="mt-1 text-xl font-bold tabular-nums">{stats.by_status[status.id] ?? 0}</div>
                </li>
              ))}
            </ul>
            <div>
              <p className="mb-2 text-xs text-muted-foreground">Applied per day</p>
              <div className="flex h-24 items-end gap-1" role="img" aria-label={`${applied} applications in the last 14 days`}>
                {days.map((day) => (
                  <div key={day.date} className="flex h-full min-w-0 flex-1 flex-col justify-end" title={`${shortDate(day.date)}: ${day.count}`}>
                    <div
                      className={cn("rounded-t-sm", day.count ? "bg-primary" : "bg-muted")}
                      style={{ height: day.count ? `${(day.count / most) * 100}%` : "4px" }}
                    />
                  </div>
                ))}
              </div>
              {days.length ? (
                <div className="mt-1 flex justify-between text-[11px] text-muted-foreground">
                  <span>{shortDate(days[0].date)}</span>
                  <span>{shortDate(days[days.length - 1].date)}</span>
                </div>
              ) : null}
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
