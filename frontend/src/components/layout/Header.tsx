import { Button } from "@/components/ui/Button";
import type { HistoryCounts } from "@/lib/types";

import styles from "./Header.module.css";

export type PillKind = "" | "running" | "done" | "error";

interface HeaderProps {
  pill: { kind: PillKind; text: string };
  history: HistoryCounts;
  showClear: boolean;
  clearDisabled: boolean;
  onClear: () => void;
  onOpenMyJobs: () => void;
}

export function Header({ pill, history, showClear, clearDisabled, onClear, onOpenMyJobs }: HeaderProps) {
  const counts = [history.applied ? `${history.applied} applied` : "", history.hidden ? `${history.hidden} hidden` : ""]
    .filter(Boolean)
    .join(" · ");
  return (
    <header className={styles.topbar}>
      <div className={styles.inner}>
        <div className={styles.brand}><span className={styles.mark} aria-hidden="true">J</span>Job Search</div>
        <span className={[styles.pill, pill.kind ? styles[pill.kind] : ""].join(" ")} aria-live="polite">
          <span className={styles.dot} />{pill.text}
        </span>
        <span className={styles.spacer} />
        {showClear ? (
          <Button disabled={clearDisabled} onClick={onClear} title="Remove the resume, keywords and results from this page">
            Clear
          </Button>
        ) : null}
        <Button aria-haspopup="dialog" onClick={onOpenMyJobs}>
          My jobs {counts ? <span className={styles.counts}>· {counts}</span> : null}
        </Button>
      </div>
    </header>
  );
}
