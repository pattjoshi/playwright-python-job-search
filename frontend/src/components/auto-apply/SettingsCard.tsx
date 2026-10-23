"use client";

import { useState } from "react";
import { toast } from "sonner";

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { autoApplyApi } from "@/lib/api/endpoints";
import type { AutoApplySettings } from "@/lib/types";

const SWITCHES: { key: "dry_run" | "show_browser" | "run_after_search"; label: string; hint: string }[] = [
  { key: "dry_run", label: "Dry run", hint: "Fill forms and take a screenshot, but never submit. Turn off to apply for real." },
  { key: "show_browser", label: "Show browser", hint: "Watch it work, and solve a CAPTCHA if one appears." },
  { key: "run_after_search", label: "Apply after each search", hint: "Start automatically when a search (or the daily search) finishes." },
];

/** The safety settings. Turning dry run off asks you to confirm first. */
export function SettingsCard({ settings, onSaved }: { settings: AutoApplySettings; onSaved: (s: AutoApplySettings) => void }) {
  const [form, setForm] = useState(settings);
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const dirty = JSON.stringify(form) !== JSON.stringify(settings);

  const save = async () => {
    setSaving(true);
    try {
      const { settings: saved } = await autoApplyApi.saveSettings(form);
      onSaved(saved);
      toast.success(saved.dry_run ? "Settings saved" : "Settings saved · applications will be submitted for real");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setSaving(false);
    }
  };
  const number = (key: "min_score" | "daily_limit", value: string) => setForm({ ...form, [key]: Number.parseInt(value, 10) || 0 });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Settings</CardTitle>
        <CardDescription>Safety limits for applying on your behalf.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4">
        {SWITCHES.map(({ key, label, hint }) => (
          <label key={key} className="flex items-start gap-3">
            <Switch checked={form[key]} onCheckedChange={(on) => setForm({ ...form, [key]: on })} aria-label={label} className="mt-0.5" />
            <span className="grid gap-0.5">
              <span className="text-sm font-medium">{label}</span>
              <span className="text-xs text-muted-foreground">{hint}</span>
            </span>
          </label>
        ))}
        <div className="grid grid-cols-2 gap-3">
          <label className="grid gap-1.5 text-sm font-medium">
            Minimum match score
            <Input type="number" min={0} max={100} value={form.min_score} onChange={(e) => number("min_score", e.target.value)} />
          </label>
          <label className="grid gap-1.5 text-sm font-medium">
            Applications per day
            <Input type="number" min={1} max={100} value={form.daily_limit} onChange={(e) => number("daily_limit", e.target.value)} />
          </label>
        </div>
        <Button disabled={!dirty || saving} onClick={() => (settings.dry_run && !form.dry_run ? setConfirming(true) : void save())}>
          Save settings
        </Button>
      </CardContent>
      <AlertDialog open={confirming} onOpenChange={setConfirming}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Submit applications for real?</AlertDialogTitle>
            <AlertDialogDescription>
              Auto-apply will submit up to {form.daily_limit} applications a day in your name, to jobs scoring {form.min_score} or more,
              using your Answer Bank and AI-written cover letters. Check a few dry-run screenshots first.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep dry run</AlertDialogCancel>
            <AlertDialogAction onClick={() => void save()}>Yes, submit for real</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
