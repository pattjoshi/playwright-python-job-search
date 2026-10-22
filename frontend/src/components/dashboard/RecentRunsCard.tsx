import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime, formatDuration } from "@/lib/format";
import type { Run } from "@/lib/types";

const ORIGINS: Record<string, string> = { daily: "Daily", web: "Manual", cli: "Command line" };
const STATUS_STYLES: Record<string, string> = {
  done: "bg-success-soft text-success",
  error: "bg-destructive/10 text-destructive",
};

/** The last few searches (manual and daily). */
export function RecentRunsCard({ runs, error }: { runs: Run[] | null; error: string | null }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent searches</CardTitle>
        <CardDescription>Every search from this page, the daily search or the command line.</CardDescription>
        <CardAction>
          <Button asChild variant="outline" size="sm"><Link href="/search">New search</Link></Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        {!runs && !error ? <div className="grid grid-cols-1 gap-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-9" />)}</div> : null}
        {runs && !runs.length ? <p className="py-6 text-center text-sm text-muted-foreground">No searches yet.</p> : null}
        {runs?.length ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>When</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Shown</TableHead>
                <TableHead className="text-right">Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.slice(0, 5).map((run) => (
                <TableRow key={run.id}>
                  <TableCell className="font-medium">{formatDateTime(run.started_at)}</TableCell>
                  <TableCell>{ORIGINS[run.origin] ?? run.origin}</TableCell>
                  <TableCell><Badge variant="secondary" className={STATUS_STYLES[run.status]}>{run.status}</Badge></TableCell>
                  <TableCell className="text-right tabular-nums">{run.status === "done" ? `${run.shown} (${run.new} new)` : "–"}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatDuration(run.duration_s)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : null}
      </CardContent>
    </Card>
  );
}
