import { Button } from "@/components/ui/Button";
import { capitalize, formatDays, formatTime, formatWhen } from "@/lib/format";
import type { DailyStatus, SiteConfig } from "@/lib/types";

import styles from "./DailyStatusBox.module.css";

interface DailyStatusBoxProps {
  status: DailyStatus;
  sites: SiteConfig[];
  onTurnOff: () => void;
}

/** "✓ Runs every day at 9:00 AM · Next run tomorrow" and how the last run went. */
export function DailyStatusBox({ status, sites, onTurnOff }: DailyStatusBoxProps) {
  const { schedule, last_run: last } = status;
  if (!schedule && !last) return null;
  const siteText = schedule
    ? sites.filter((s) => schedule.sites[s.id]).map((s) => `${s.name} ${schedule.sites[s.id]}`).join(" · ")
    : "";
  const when = last ? capitalize(formatWhen(last.last_run)) : "";

  return (
    <div className={styles.box} aria-live="polite">
      {schedule ? (
        <div className={styles.row}>
          <div>
            <b>✓ Runs {formatDays(schedule.days)} at {formatTime(schedule.time)}</b>
            Next run {formatWhen(schedule.next_run)} · {siteText}
          </div>
          <Button onClick={onTurnOff}>Turn off</Button>
        </div>
      ) : null}
      {last && last.status === "done" ? (
        <div className={styles.last}>
          Last run {when} · {last.jobs} jobs ({last.new} new)
          {last.report_url ? (
            <> · <a href={last.report_url} target="_blank" rel="noopener noreferrer">Open report</a></>
          ) : null}
        </div>
      ) : null}
      {last && last.status !== "done" ? (
        <div className={`${styles.last} ${styles.failed}`}>Last run {when} failed: {last.error || "unknown error"}</div>
      ) : null}
    </div>
  );
}
