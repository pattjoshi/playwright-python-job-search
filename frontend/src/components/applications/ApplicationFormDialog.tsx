"use client";

import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { Application, ApplicationInput, ApplicationStatus } from "@/lib/types";

import { TextField } from "./TextField";
import { STATUSES } from "./statuses";

interface ApplicationFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Editing this application, or adding a new one when missing. */
  application?: Application | null;
  onSave: (input: ApplicationInput) => Promise<unknown>;
}

const EMPTY: ApplicationInput = {
  company: "", title: "", url: "", location: "", salary: "", status: "saved",
  applied_on: "", follow_up_on: "", contact: "", notes: "",
};

function initial(application?: Application | null): ApplicationInput {
  if (!application) return EMPTY;
  const { company, title, url, location, salary, status, applied_on, follow_up_on, contact, notes } = application;
  return { company, title, url, location, salary, status, applied_on: applied_on ?? "", follow_up_on: follow_up_on ?? "", contact, notes };
}

export function ApplicationFormDialog({ open, onOpenChange, application, onSave }: ApplicationFormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{application ? "Edit application" : "Add application"}</DialogTitle>
          <DialogDescription>Only company and role are needed; fill in the rest any time.</DialogDescription>
        </DialogHeader>
        {/* Re-created on every open, so the form starts from the application's current values. */}
        {open ? <ApplicationForm key={application?.id ?? "new"} application={application} onSave={onSave} onDone={() => onOpenChange(false)} /> : null}
      </DialogContent>
    </Dialog>
  );
}

function ApplicationForm({ application, onSave, onDone }: {
  application?: Application | null; onSave: (input: ApplicationInput) => Promise<unknown>; onDone: () => void;
}) {
  const [values, setValues] = useState<ApplicationInput>(() => initial(application));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (patch: ApplicationInput) => setValues((current) => ({ ...current, ...patch }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(values);
      onDone();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={submit}>
      <TextField id="app-company" label="Company" required value={values.company} onChange={(company) => set({ company })} />
      <TextField id="app-title" label="Role" required value={values.title} onChange={(title) => set({ title })} />
      <TextField id="app-url" label="Job link" type="url" value={values.url} onChange={(url) => set({ url })} className="sm:col-span-2" />
      <TextField id="app-location" label="Location" value={values.location} onChange={(location) => set({ location })} />
      <TextField id="app-salary" label="Salary / CTC" value={values.salary} onChange={(salary) => set({ salary })} />
      <div className="grid grid-cols-1 gap-1.5">
        <span className="text-sm font-medium" id="app-status-label">Status</span>
        <Select value={values.status} onValueChange={(status) => set({ status: status as ApplicationStatus })}>
          <SelectTrigger aria-labelledby="app-status-label" className="w-full"><SelectValue /></SelectTrigger>
          <SelectContent>
            {STATUSES.map((status) => <SelectItem key={status.id} value={status.id}>{status.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <TextField id="app-contact" label="Contact" value={values.contact} onChange={(contact) => set({ contact })} placeholder="e.g. Priya (HR)" />
      <TextField id="app-applied" label="Applied on" type="date" value={values.applied_on ?? ""} onChange={(applied_on) => set({ applied_on })} />
      <TextField id="app-follow-up" label="Follow up on" type="date" value={values.follow_up_on ?? ""} onChange={(follow_up_on) => set({ follow_up_on })} />
      <div className="grid grid-cols-1 gap-1.5 sm:col-span-2">
        <label htmlFor="app-notes" className="text-sm font-medium">Notes</label>
        <Textarea id="app-notes" rows={4} value={values.notes} onChange={(e) => set({ notes: e.target.value })} />
      </div>
      {error ? <Alert variant="destructive" className="sm:col-span-2"><AlertDescription>{error}</AlertDescription></Alert> : null}
      <DialogFooter className="sm:col-span-2">
        <Button variant="outline" onClick={onDone}>Cancel</Button>
        <Button type="submit" disabled={saving}>{application ? "Save changes" : "Add application"}</Button>
      </DialogFooter>
    </form>
  );
}
