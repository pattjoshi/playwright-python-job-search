"use client";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHead } from "@/components/ui/Card";
import { Switch } from "@/components/ui/Switch";
import type { SearchFormApi } from "@/hooks/useSearchForm";

import styles from "./OptionsCard.module.css";

interface OptionsCardProps {
  form: SearchFormApi;
  seenCount: number;
  onForgetSeen: () => void;
}

/** Step 4: only new jobs, show browser, and the advanced numbers. */
export function OptionsCard({ form: api, seenCount, onForgetSeen }: OptionsCardProps) {
  const { form, update } = api;
  return (
    <Card>
      <CardBody>
        <CardHead step={4}>Options</CardHead>
        <div className={styles.row}>
          <div className={styles.text}>
            <div className={styles.title}>Only new jobs</div>
            <div className={styles.desc}>Skip jobs shown in earlier searches</div>
          </div>
          <Switch checked={form.onlyNew} label="Only new jobs" onChange={(onlyNew) => update({ onlyNew })} />
        </div>
        <div className={styles.row}>
          <div className={styles.text}>
            <div className={styles.title}>Show browser</div>
            <div className={styles.desc}>Watch it work, and solve &quot;verify you&apos;re human&quot; checks on Naukri or Indeed</div>
          </div>
          <Switch checked={form.showBrowser} label="Show browser" onChange={(showBrowser) => update({ showBrowser })} />
        </div>
        <details className={styles.advanced}>
          <summary>Advanced</summary>
          <div className={styles.grid}>
            <div>
              <label className={styles.label} htmlFor="max-pages">Pages per search</label>
              <input
                className="input" id="max-pages" type="number" min={1} max={10} value={form.maxPages}
                onChange={(e) => update({ maxPages: e.target.value })}
              />
            </div>
            <div>
              <label className={styles.label} htmlFor="top">Jobs to score per site</label>
              <input
                className="input" id="top" type="number" min={5} max={200} value={form.top}
                onChange={(e) => update({ top: e.target.value })}
              />
            </div>
          </div>
          <div className="help" style={{ marginTop: 12 }}>
            {seenCount ? `${seenCount} jobs marked as seen. ` : "No seen jobs yet. "}
            <Button variant="link" disabled={!seenCount} onClick={onForgetSeen}>Forget seen jobs</Button>
          </div>
        </details>
      </CardBody>
    </Card>
  );
}
