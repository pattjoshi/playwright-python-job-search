import Link from "next/link";

import { isOverdue, shortDate } from "@/components/applications/statuses";
import { StatusBadge } from "@/components/applications/StatusBadge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApplicationStats } from "@/lib/types";
import { cn } from "@/lib/utils";

/** The next follow-ups you planned (overdue ones in red). */
export function FollowUpsCard({ stats }: { stats: ApplicationStats | null }) {
  if (!stats) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Follow-ups</CardTitle>
        <CardDescription>Applications with a follow-up date coming up.</CardDescription>
      </CardHeader>
      <CardContent>
        {!stats.follow_ups.length ? (
          <p className="text-sm text-muted-foreground">Nothing planned. Set a follow-up date on an application to see it here.</p>
        ) : (
          <ul className="grid grid-cols-1 gap-2">
            {stats.follow_ups.map((app) => (
              <li key={app.id}>
                <Link href="/applications" className="flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-accent/50">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{app.company}</p>
                    <p className="truncate text-xs text-muted-foreground">{app.title}</p>
                  </div>
                  <StatusBadge status={app.status} />
                  <span className={cn("text-xs tabular-nums", isOverdue(app.follow_up_on) ? "font-semibold text-destructive" : "text-muted-foreground")}>
                    {shortDate(app.follow_up_on)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
