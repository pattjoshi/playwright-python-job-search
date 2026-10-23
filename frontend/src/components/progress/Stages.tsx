import { STAGES } from "@/lib/constants";
import type { SearchJob } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Five bars: Resume → Search → Details → Scoring → Done, the current one filling up. */
export function Stages({ job }: { job: SearchJob | null }) {
  const current = job ? STAGES.findIndex((stage) => stage.id === job.stage) : -1;
  const progress = job?.progress;
  const pct = Math.max(8, progress?.total ? Math.round((100 * progress.done) / progress.total) : 40);
  return (
    <ol className="mt-4 mb-1 grid list-none grid-cols-5 gap-1.5 p-0">
      {STAGES.map((stage, index) => {
        const done = !!job && (index < current || job.status === "done");
        const active = !done && index === current;
        return (
          <li key={stage.id} className={cn("text-xs font-semibold text-muted-foreground max-sm:text-[11px]", done && "text-success", active && "text-primary")}>
            <span className="mb-1.5 block h-1 overflow-hidden rounded-full bg-border">
              <span
                className={cn("block h-full rounded-full", done ? "w-full bg-success" : active ? "bg-primary" : "w-0")}
                style={active ? { width: `${pct}%` } : undefined}
              />
            </span>
            {stage.label}
          </li>
        );
      })}
    </ol>
  );
}
