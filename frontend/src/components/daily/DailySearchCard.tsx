"use client";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHead } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { InlineCheck } from "@/components/ui/InlineCheck";
import type { DailySearchApi } from "@/hooks/useDailySearch";
import type { SiteConfig } from "@/lib/types";

import { DailyStatusBox } from "./DailyStatusBox";
import { DaysPicker } from "./DaysPicker";
import styles from "./DailySearchCard.module.css";

interface DailySearchCardProps {
  daily: DailySearchApi;
  sites: SiteConfig[];
  canSave: boolean;
  onSave: () => void;
}

const NOTES: Record<string, string> = {
  windows:
    "Uses Windows Task Scheduler, so it runs even when this page is closed. " +
    "If your laptop is off or asleep at that time, it runs as soon as it's back on.",
  default: "Your computer needs to be on at that time. It runs even when this page is closed.",
};

/** Step 5: run the search above automatically every day at a set time. */
export function DailySearchCard({ daily, sites, canSave, onSave }: DailySearchCardProps) {
  const { status } = daily;
  if (status && !status.supported) return null;
  return (
    <Card>
      <CardBody>
        <CardHead step={5}>Daily search</CardHead>
        {status ? <DailyStatusBox status={status} sites={sites} onTurnOff={daily.turnOff} /> : null}
        <p className="help" style={{ margin: "-4px 0 12px" }}>
          Run the search above automatically and open the report when it&apos;s ready.
        </p>
        <Field label={<label htmlFor="daily-time">Time</label>}>
          <div className={styles.timeRow}>
            <input
              className="input" id="daily-time" type="time" required value={daily.time}
              onChange={(e) => daily.setTime(e.target.value)}
            />
            <InlineCheck checked={daily.openReport} onChange={daily.setOpenReport}>Open report when ready</InlineCheck>
          </div>
        </Field>
        <Field label={<span id="days-label">Days</span>}>
          <DaysPicker days={daily.days} onChange={daily.setDays} labelledBy="days-label" />
        </Field>
        <Alert message={daily.error} className={styles.error} />
        <Button block disabled={!canSave || daily.saving} onClick={onSave}>
          {status?.schedule ? "Update daily search" : "Save daily search"}
        </Button>
        {status ? <p className="help">{NOTES[status.kind] ?? NOTES.default}</p> : null}
      </CardBody>
    </Card>
  );
}
