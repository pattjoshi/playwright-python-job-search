"use client";

import { CalendarClock } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { capitalize, formatDays, formatTime, formatWhen } from "@/lib/format";
import { useSearchSession } from "@/providers/SearchSessionProvider";

/** Whether the daily search is on, when it runs next and how the last run went. */
export function DailySummaryCard() {
  const { status } = useSearchSession().daily;
  const schedule = status?.schedule;
  const last = status?.last_run;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><CalendarClock className="size-4" /> Daily search</CardTitle>
        <CardDescription>
          {schedule ? `Runs ${formatDays(schedule.days)} at ${formatTime(schedule.time)}` : "Not set up yet"}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-2 text-sm">
        {schedule ? <p>Next run: <b>{formatWhen(schedule.next_run)}</b></p> : (
          <p className="text-muted-foreground">Let the search run by itself every morning, even when this page is closed.</p>
        )}
        {last ? (
          <p className={last.status === "done" ? "text-muted-foreground" : "text-destructive"}>
            Last run {capitalize(formatWhen(last.last_run))}:{" "}
            {last.status === "done" ? `${last.jobs} jobs (${last.new} new)` : `failed (${last.error || "unknown error"})`}
          </p>
        ) : null}
        <Button asChild variant="outline" size="sm" className="mt-1 w-fit">
          <Link href="/search#daily-search">{schedule ? "Change" : "Set up"}</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
