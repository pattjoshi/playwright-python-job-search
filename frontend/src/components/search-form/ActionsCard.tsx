import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { Estimate } from "@/lib/estimate";

import styles from "./ActionsCard.module.css";

interface ActionsCardProps {
  estimate: Estimate;
  error: string | null;
  running: boolean;
  stopping: boolean;
  canStart: boolean;
  hasResume: boolean;
  onStop: () => void;
}

/** The sticky footer with the estimate and the Start / Stop button (Start submits the form). */
export function ActionsCard({ estimate, error, running, stopping, canStart, hasResume, onStop }: ActionsCardProps) {
  return (
    <Card className={styles.actions}>
      <div className={styles.body}>
        <div className={styles.estimate}>
          {estimate.text}
          {estimate.tip ? <span className={styles.tip}>Tip: fewer keywords or cities makes it faster</span> : null}
        </div>
        <Alert message={error} />
        {running ? (
          <Button variant="danger" disabled={stopping} onClick={onStop}>{stopping ? "Stopping…" : "Stop search"}</Button>
        ) : (
          <Button variant="primary" type="submit" disabled={!canStart}>
            {hasResume ? "Start search" : "Upload your resume to start"}
          </Button>
        )}
      </div>
    </Card>
  );
}
