import { Fragment } from "react";

import { funnelHint } from "@/lib/funnel";
import type { FunnelStep } from "@/lib/types";


interface FunnelProps {
  steps: FunnelStep[];
  requested: Record<string, number>;
  done: boolean;
}

/** "169 found → 120 unique → 40 posted in 24h → …" plus a tip when few jobs made it through. */
export function Funnel({ steps, requested, done }: FunnelProps) {
  if (!steps.length) return null;
  const hint = done ? funnelHint(steps, requested) : null;
  return (
    <>
      <div className="mt-3 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-muted-foreground" aria-label="Jobs kept after each filter">
        {steps.map(([label, count], index) => (
          <Fragment key={label}>
            {index ? <span className="text-muted-foreground/60" aria-hidden="true">→</span> : null}
            <span className="whitespace-nowrap"><b className="text-foreground tabular-nums">{count}</b> {label}</span>
          </Fragment>
        ))}
      </div>
      {hint ? <div className="mt-2.5 rounded-md bg-warning-soft px-3 py-2 text-sm text-warning">{hint}</div> : null}
    </>
  );
}
