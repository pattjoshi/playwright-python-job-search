import { STAGES } from "@/lib/constants";
import type { SearchJob } from "@/lib/types";

import styles from "./Stages.module.css";

/** Five bars: Resume → Search → Details → Scoring → Done, the current one filling up. */
export function Stages({ job }: { job: SearchJob | null }) {
  const current = job ? STAGES.findIndex((stage) => stage.id === job.stage) : -1;
  const progress = job?.progress;
  const pct = progress?.total ? Math.round((100 * progress.done) / progress.total) : 40;
  return (
    <ol className={styles.stages}>
      {STAGES.map((stage, index) => {
        const state = job && (index < current || job.status === "done") ? styles.done : index === current ? styles.current : "";
        return (
          <li key={stage.id} className={state} style={{ "--pct": `${Math.max(8, pct)}%` } as React.CSSProperties}>
            {stage.label}
          </li>
        );
      })}
    </ol>
  );
}
