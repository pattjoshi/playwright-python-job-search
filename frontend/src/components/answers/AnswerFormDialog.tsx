"use client";

import { useState } from "react";

import { TextField } from "@/components/applications/TextField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { Answer, AnswerCategory, AnswerInput, AnswerKind } from "@/lib/types";

import { AnswerValueInput } from "./AnswerValueInput";
import { CATEGORIES, KINDS } from "./meta";

interface AnswerFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Editing this question, or adding a new one when missing. */
  item?: Answer | null;
  onSave: (input: AnswerInput) => Promise<unknown>;
}

export function AnswerFormDialog({ open, onOpenChange, item, onSave }: AnswerFormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{item ? "Edit question" : "Add question"}</DialogTitle>
          <DialogDescription>
            Add the other ways forms ask it, so it is recognised without asking the AI.
          </DialogDescription>
        </DialogHeader>
        {open ? <AnswerForm key={item?.id ?? "new"} item={item} onSave={onSave} onDone={() => onOpenChange(false)} /> : null}
      </DialogContent>
    </Dialog>
  );
}

const lines = (text: string) => text.split("\n").map((line) => line.trim()).filter(Boolean);

function AnswerForm({ item, onSave, onDone }: {
  item?: Answer | null; onSave: (input: AnswerInput) => Promise<unknown>; onDone: () => void;
}) {
  const [question, setQuestion] = useState(item?.question ?? "");
  const [category, setCategory] = useState<AnswerCategory>(item?.category ?? "other");
  const [kind, setKind] = useState<AnswerKind>(item?.kind ?? "text");
  const [options, setOptions] = useState((item?.options ?? []).join("\n"));
  const [wordings, setWordings] = useState((item?.wordings ?? []).join("\n"));
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const input: AnswerInput = { question, category, kind, options: kind === "choice" ? lines(options) : [], wordings: lines(wordings) };
    if (!item) input.answer = answer.trim();
    try {
      await onSave(input);
      onDone();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={submit}>
      <TextField id="answer-question" label="Question" required value={question} onChange={setQuestion} className="sm:col-span-2" />
      <div className="grid grid-cols-1 gap-1.5">
        <span className="text-sm font-medium" id="answer-category-label">Category</span>
        <Select value={category} onValueChange={(value) => setCategory(value as AnswerCategory)}>
          <SelectTrigger aria-labelledby="answer-category-label" className="w-full"><SelectValue /></SelectTrigger>
          <SelectContent>{CATEGORIES.map((c) => <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div className="grid grid-cols-1 gap-1.5">
        <span className="text-sm font-medium" id="answer-kind-label">Answer type</span>
        <Select value={kind} onValueChange={(value) => setKind(value as AnswerKind)}>
          <SelectTrigger aria-labelledby="answer-kind-label" className="w-full"><SelectValue /></SelectTrigger>
          <SelectContent>{KINDS.map((k) => <SelectItem key={k.id} value={k.id}>{k.label}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      {kind === "choice" ? (
        <div className="grid grid-cols-1 gap-1.5 sm:col-span-2">
          <label htmlFor="answer-options" className="text-sm font-medium">Options (one per line)</label>
          <Textarea id="answer-options" rows={3} value={options} onChange={(e) => setOptions(e.target.value)} />
        </div>
      ) : null}
      <div className="grid grid-cols-1 gap-1.5 sm:col-span-2">
        <label htmlFor="answer-wordings" className="text-sm font-medium">Other wordings (one per line)</label>
        <Textarea
          id="answer-wordings" rows={3} value={wordings} onChange={(e) => setWordings(e.target.value)}
          placeholder={"How soon can you join?\nWhat is your notice period?"}
        />
      </div>
      {!item ? (
        <div className="grid grid-cols-1 gap-1.5 sm:col-span-2">
          <span className="text-sm font-medium">Answer</span>
          <AnswerValueInput id="answer-new" label="Answer" kind={kind} options={lines(options)} value={answer} onChange={setAnswer} />
        </div>
      ) : null}
      {error ? <Alert variant="destructive" className="sm:col-span-2"><AlertDescription>{error}</AlertDescription></Alert> : null}
      <DialogFooter className="sm:col-span-2">
        <Button variant="outline" onClick={onDone}>Cancel</Button>
        <Button type="submit" disabled={saving}>{item ? "Save changes" : "Add question"}</Button>
      </DialogFooter>
    </form>
  );
}
