import { Play, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import type { AutoApplyOverview } from "@/lib/types";

interface RunCardProps {
  data: AutoApplyOverview;
  waiting: number;
  busy: boolean;
  onRun: () => void;
  onStop: () => void;
}

/** Start / stop, today's count against the limit, and the live log. */
export function RunCard({ data, waiting, busy, onRun, onStop }: RunCardProps) {
  const { run, settings, today, remaining } = data;
  const active = run.status === "running" || run.status === "stopping";
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">{active ? <Spinner /> : null} {active ? "Applying…" : "Run"}</CardTitle>
        <CardDescription>
          {today} of {settings.daily_limit} today · {waiting} waiting{remaining ? "" : " · today's limit is reached"}
        </CardDescription>
        <CardAction>
          {active ? (
            <Button variant="outline" onClick={onStop} disabled={run.status === "stopping"}><Square /> Stop</Button>
          ) : (
            <Button onClick={onRun} disabled={busy || !waiting || !remaining}><Play /> Run now</Button>
          )}
        </CardAction>
      </CardHeader>
      {run.logs.length || run.error ? (
        <CardContent>
          {run.error ? <p className="mb-2 text-sm text-destructive">{run.error}</p> : null}
          {run.logs.length ? (
            <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap" aria-label="Auto-apply log">
              {run.logs.join("\n")}
            </pre>
          ) : null}
        </CardContent>
      ) : null}
    </Card>
  );
}
