import { Fragment } from "react";

import { funnelHint } from "@/lib/funnel";
import type { FunnelStep } from "@/lib/types";

import styles from "./Funnel.module.css";

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
      <div className={styles.funnel} aria-label="Jobs kept after each filter">
        {steps.map(([label, count], index) => (
          <Fragment key={label}>
            {index ? <span className={styles.arrow} aria-hidden="true">→</span> : null}
            <span className={styles.step}><b>{count}</b> {label}</span>
          </Fragment>
        ))}
      </div>
      {hint ? <div className={styles.hint}>{hint}</div> : null}
    </>
  );
}
