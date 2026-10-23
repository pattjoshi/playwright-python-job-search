"use client";

import { ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StepTitle } from "@/components/ui/step-title";
import { Switch } from "@/components/ui/switch";
import type { SearchFormApi } from "@/hooks/useSearchForm";

interface OptionsCardProps {
  form: SearchFormApi;
  seenCount: number;
  onForgetSeen: () => void;
}

function OptionRow({ title, description, checked, onChange }: {
  title: string; description: string; checked: boolean; onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-start gap-3 py-2.5">
      <div className="flex-1">
        <div className="text-sm font-semibold">{title}</div>
        <div className="text-xs text-muted-foreground">{description}</div>
      </div>
      <Switch checked={checked} aria-label={title} onCheckedChange={onChange} />
    </div>
  );
}

/** Step 4: only new jobs, show browser, and the advanced numbers. */
export function OptionsCard({ form: api, seenCount, onForgetSeen }: OptionsCardProps) {
  const { form, update } = api;
  return (
    <Card className="gap-3 py-5">
      <CardContent className="grid grid-cols-1 px-5">
        <StepTitle step={4}>Options</StepTitle>
        <div className="mt-2 divide-y">
          <OptionRow
            title="Only new jobs" description="Skip jobs shown in earlier searches"
            checked={form.onlyNew} onChange={(onlyNew) => update({ onlyNew })}
          />
          <OptionRow
            title="Show browser" description={'Watch it work, and solve "verify you\'re human" checks on Naukri or Indeed'}
            checked={form.showBrowser} onChange={(showBrowser) => update({ showBrowser })}
          />
        </div>
        <details className="group mt-1">
          <summary className="flex cursor-pointer list-none items-center gap-1 pt-2 text-sm font-semibold text-muted-foreground [&::-webkit-details-marker]:hidden">
            <ChevronRight className="size-4 transition-transform group-open:rotate-90" aria-hidden="true" /> Advanced
          </summary>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="grid grid-cols-1 gap-1.5">
              <Label htmlFor="max-pages">Pages per search</Label>
              <Input id="max-pages" type="number" min={1} max={10} value={form.maxPages} onChange={(e) => update({ maxPages: e.target.value })} />
            </div>
            <div className="grid grid-cols-1 gap-1.5">
              <Label htmlFor="top">Jobs to score per site</Label>
              <Input id="top" type="number" min={5} max={200} value={form.top} onChange={(e) => update({ top: e.target.value })} />
            </div>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            {seenCount ? `${seenCount} jobs marked as seen. ` : "No seen jobs yet. "}
            <Button variant="link" size="xs" className="h-auto p-0" disabled={!seenCount} onClick={onForgetSeen}>Forget seen jobs</Button>
          </p>
        </details>
      </CardContent>
    </Card>
  );
}
