"use client";

import { Check, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Answer } from "@/lib/types";

import { AnswerValueInput } from "./AnswerValueInput";
import { SOURCE_LABEL, STATUS_BADGE } from "./meta";

interface AnswerRowProps {
  item: Answer;
  onSave: (item: Answer, answer: string) => Promise<void>;
  onApprove: (item: Answer) => Promise<void>;
  onEdit: (item: Answer) => void;
  onDelete: (item: Answer) => void;
}

/** One question: write or change the answer right here, approve an AI draft, edit or delete. */
export function AnswerRow({ item, onSave, onApprove, onEdit, onDelete }: AnswerRowProps) {
  const [value, setValue] = useState(item.answer);
  const [busy, setBusy] = useState(false);
  const dirty = value.trim() !== item.answer;
  const badge = STATUS_BADGE[item.status];
  const meta = [
    SOURCE_LABEL[item.source] ?? item.source,
    item.asked_by ? `first asked by ${item.asked_by}` : null,
    item.use_count ? `used ${item.use_count} time${item.use_count === 1 ? "" : "s"}` : null,
  ].filter(Boolean).join(" · ");

  const act = async (action: () => Promise<void>) => {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="grid grid-cols-1 gap-2.5 rounded-lg border bg-card p-4" aria-label={item.question}>
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium break-words">{item.question}</p>
            <Badge variant="secondary" className={badge.className}>{badge.label}</Badge>
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">{meta}</p>
          {item.wordings.length ? (
            <p className="mt-0.5 truncate text-xs text-muted-foreground" title={item.wordings.join("\n")}>
              Also asked as: {item.wordings.map((w) => `“${w}”`).join(", ")}
            </p>
          ) : null}
        </div>
        <Button variant="ghost" size="icon-sm" aria-label={`Edit “${item.question}”`} onClick={() => onEdit(item)}><Pencil /></Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label={`Delete “${item.question}”`} className="text-muted-foreground hover:text-destructive">
              <Trash2 />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this question?</AlertDialogTitle>
              <AlertDialogDescription>
                “{item.question}” and its answer will be removed. If a form asks it again, it comes back as a new question.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => onDelete(item)}>Delete</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
      <AnswerValueInput
        id={`answer-${item.id}`} label={`Answer to “${item.question}”`} kind={item.kind} options={item.options}
        value={value} onChange={setValue}
      />
      {dirty || item.status === "needs_review" ? (
        <div className="flex flex-wrap gap-2">
          {dirty ? (
            <>
              <Button size="sm" disabled={busy} onClick={() => act(() => onSave(item, value.trim()))}>Save answer</Button>
              <Button size="sm" variant="ghost" disabled={busy} onClick={() => setValue(item.answer)}>Cancel</Button>
            </>
          ) : (
            <Button size="sm" disabled={busy} onClick={() => act(() => onApprove(item))}><Check /> Approve</Button>
          )}
        </div>
      ) : null}
    </li>
  );
}
