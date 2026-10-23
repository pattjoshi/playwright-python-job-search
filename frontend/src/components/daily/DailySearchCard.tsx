"use client";

import { toast } from "sonner";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { StepTitle } from "@/components/ui/step-title";
import type { DailySearchApi } from "@/hooks/useDailySearch";
import type { SiteConfig } from "@/lib/types";

import { DailyStatusBox } from "./DailyStatusBox";
import { DaysPicker } from "./DaysPicker";

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
  const turnOff = async () => {
    if (await daily.turnOff()) toast("Daily search turned off");
  };
  return (
    <Card id="daily-search" className="scroll-mt-20 gap-3 py-5">
      <CardContent className="grid grid-cols-1 gap-4 px-5">
        <StepTitle step={5}>Daily search</StepTitle>
        {status ? <DailyStatusBox status={status} sites={sites} onTurnOff={turnOff} /> : null}
        <p className="-mt-1 text-xs text-muted-foreground">Run the search above automatically and open the report when it&apos;s ready.</p>
        <FormField label={<label htmlFor="daily-time">Time</label>}>
          <div className="flex flex-wrap items-center gap-3">
            <Input id="daily-time" type="time" required value={daily.time} className="w-36" onChange={(e) => daily.setTime(e.target.value)} />
            <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
              <Checkbox checked={daily.openReport} onCheckedChange={(checked) => daily.setOpenReport(checked === true)} />
              Open report when ready
            </label>
          </div>
        </FormField>
        <FormField label={<span id="days-label">Days</span>}>
          <DaysPicker days={daily.days} onChange={daily.setDays} labelledBy="days-label" />
        </FormField>
        {daily.error ? <Alert variant="destructive"><AlertDescription>{daily.error}</AlertDescription></Alert> : null}
        <Button variant="outline" disabled={!canSave || daily.saving} onClick={onSave}>
          {status?.schedule ? "Update daily search" : "Save daily search"}
        </Button>
        {status ? <p className="text-xs text-muted-foreground">{NOTES[status.kind] ?? NOTES.default}</p> : null}
      </CardContent>
    </Card>
  );
}
