import { Square } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import type { Estimate } from "@/lib/estimate";

interface ActionsCardProps {
  estimate: Estimate;
  error: string | null;
  running: boolean;
  stopping: boolean;
  starting: boolean;
  canStart: boolean;
  hasResume: boolean;
  onStop: () => void;
}

/** The sticky footer with the estimate and the Start / Stop button (Start submits the form). */
export function ActionsCard({ estimate, error, running, stopping, starting, canStart, hasResume, onStop }: ActionsCardProps) {
  return (
    <Card className="sticky bottom-3 z-10 gap-0 py-0 shadow-lg max-lg:static">
      <CardContent className="grid grid-cols-1 gap-2.5 p-4">
        <p className="text-xs text-muted-foreground">
          {estimate.text}
          {estimate.tip ? <span className="block text-warning">Tip: fewer keywords or cities makes it faster</span> : null}
        </p>
        {error ? <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert> : null}
        {running ? (
          <Button variant="outline" size="lg" className="w-full border-destructive text-destructive hover:bg-destructive/10 hover:text-destructive" disabled={stopping} onClick={onStop}>
            {stopping ? <><Spinner aria-hidden="true" /> Stopping…</> : <><Square className="fill-current" /> Stop search</>}
          </Button>
        ) : (
          <Button type="submit" size="lg" className="w-full text-base" disabled={!canStart}>
            {starting ? <Spinner aria-hidden="true" /> : null}
            {hasResume ? "Start search" : "Upload your resume to start"}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
