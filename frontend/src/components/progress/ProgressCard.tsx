import { Alert } from "@/components/ui/Alert";
import { Card, CardBody } from "@/components/ui/Card";
import { Chip, ChipLabel, Chips } from "@/components/ui/Chips";
import { Spinner } from "@/components/ui/Spinner";
import type { RunView } from "@/hooks/useSearchJob";
import { STAGES } from "@/lib/constants";
import { formatClock, formatDateTime, formatDuration } from "@/lib/format";
import type { SearchJob, SiteConfig } from "@/lib/types";

import { Funnel } from "./Funnel";
import { LogView } from "./LogView";
import styles from "./ProgressCard.module.css";
import { SiteStatus } from "./SiteStatus";
import { Stages } from "./Stages";

interface ProgressCardProps {
  job: SearchJob | null;
  view: RunView;
  restored: boolean;
  elapsed: number;
  error: string | null;
  sites: SiteConfig[];
}

const ENDED_TEXT: Record<string, string> = {
  done: "Search complete",
  stopped: "Search stopped",
  error: "The search stopped with an error",
};

function headline(job: SearchJob | null, view: RunView, restored: boolean): string {
  if (view === "finished" && job) {
    const text = ENDED_TEXT[job.status] ?? ENDED_TEXT.error;
    return restored && job.finished_at ? `${text} · ${formatDateTime(job.finished_at)}` : text;
  }
  if (!job) return "Starting…";
  if (job.status === "stopping") return "Stopping after the current step…";
  const botCheck = [...job.logs].reverse().find((line) => /bot check/i.test(line));
  if (botCheck && job.stage === "search") return "A site is asking to verify you're human — solve it in the browser window";
  let text = STAGES.find((stage) => stage.id === job.stage)?.text ?? "Working…";
  if (job.progress?.total && job.status === "running") text += ` ${job.progress.done} of ${job.progress.total}`;
  return text;
}

function elapsedText(job: SearchJob | null, restored: boolean, elapsed: number): string {
  if (!restored) return formatClock(elapsed);
  if (!job?.started_at || !job.finished_at) return "";
  return formatDuration((Date.parse(job.finished_at) - Date.parse(job.started_at)) / 1000);
}

/** The live progress of a search (or how the last one ended): stages, sites, filters and the log. */
export function ProgressCard({ job, view, restored, elapsed, error, sites }: ProgressCardProps) {
  const running = view === "running";
  return (
    <Card>
      <CardBody>
        <div className={styles.head} aria-live="polite">
          {running ? <Spinner /> : null}
          <span>{headline(job, view, restored)}</span>
          <span className={styles.elapsed}>{elapsedText(job, restored, elapsed)}</span>
        </div>
        <Stages job={job} />
        {job ? <SiteStatus sites={sites} progress={job.sites} /> : null}
        {job ? <Funnel steps={job.funnel ?? []} requested={job.requested} done={job.status === "done"} /> : null}
        {job?.profile ? (
          <div className={styles.found}>
            <Chips>
              <ChipLabel>Searching for</ChipLabel>
              {job.profile.keywords.map((keyword) => <Chip key={`k-${keyword}`} kind="key">{keyword}</Chip>)}
              <ChipLabel>in</ChipLabel>
              {job.profile.locations.map((location) => <Chip key={`l-${location}`} kind="key">{location}</Chip>)}
            </Chips>
            <Chips>
              <ChipLabel>Your skills</ChipLabel>
              {job.profile.skills.slice(0, 14).map((skill) => <Chip key={skill} kind="skill">{skill}</Chip>)}
            </Chips>
          </div>
        ) : null}
        <Alert message={error ?? (view === "finished" ? job?.error : null)} className={styles.error} />
        <LogView lines={job?.logs ?? []} />
      </CardBody>
    </Card>
  );
}
