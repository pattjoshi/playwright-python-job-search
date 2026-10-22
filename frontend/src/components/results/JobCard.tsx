import { Badge } from "@/components/ui/Badge";
import { Button, LinkButton } from "@/components/ui/Button";
import { ChipRow } from "@/components/ui/Chips";
import { safeUrl, scoreBand } from "@/lib/format";
import type { Job, JobStatus } from "@/lib/types";

import styles from "./JobCard.module.css";

interface JobCardProps {
  job: Job;
  rank: number;
  applied: boolean;
  siteName?: string;
  onSetStatus: (status: JobStatus) => void;
}

/** One job: match score, title and links, matching/missing skills, the AI's reason, and actions. */
export function JobCard({ job, rank, applied, siteName, onSetStatus }: JobCardProps) {
  const url = safeUrl(job.url) ?? "#";
  return (
    <li className={[styles.job, applied ? styles.applied : ""].join(" ")}>
      <div className={styles.side}>
        <div className={`${styles.score} ${styles[scoreBand(job.score)]}`} title="Match score">{job.score ?? "–"}</div>
        <div className={styles.rank}>#{rank}</div>
      </div>
      <div>
        <div className={styles.title}>
          <a href={url} target="_blank" rel="noopener noreferrer">{job.title}</a>
          {job.is_new ? <Badge kind="new">New</Badge> : null}
          {applied ? <Badge kind="applied">Applied</Badge> : null}
          {siteName ? <Badge kind="site">{siteName}</Badge> : null}
        </div>
        <div className={styles.meta}>
          {[job.company, job.location, job.experience, job.posted_text].filter(Boolean).join(" · ")}
        </div>
        <ChipRow label="Matching" items={job.matched_skills ?? []} kind="have" />
        <ChipRow label="Missing" items={job.missing_skills ?? []} kind="miss" />
        {job.match_reason ? <p className={styles.reason}>{job.match_reason}</p> : null}
        <div className={styles.actions}>
          <LinkButton href={url} external>View job ↗</LinkButton>
          {applied ? (
            <Button onClick={() => onSetStatus("seen")}>Undo applied</Button>
          ) : (
            <>
              <Button onClick={() => onSetStatus("applied")}>✓ Mark applied</Button>
              <Button onClick={() => onSetStatus("hidden")}>Hide</Button>
            </>
          )}
        </div>
      </div>
    </li>
  );
}

export function HiddenJob({ job, onUndo }: { job: Job; onUndo: () => void }) {
  return (
    <li className={styles.hiddenNote}>
      Hidden “{job.title}”
      <Button variant="link" onClick={onUndo}>Undo</Button>
    </li>
  );
}
