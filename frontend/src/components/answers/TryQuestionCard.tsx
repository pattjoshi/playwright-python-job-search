"use client";

import { Search } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { answersApi } from "@/lib/api/endpoints";
import type { TryResult } from "@/lib/types";
import { cn } from "@/lib/utils";

type Outcome = TryResult["how"] | "unanswered";

const OUTCOMES: Record<Outcome, { title: (q: string) => string; note: string; className: string }> = {
  saved: { title: (q) => `Saved answer to “${q}”`, note: "This wording is already in your bank.", className: "bg-success-soft" },
  matched: {
    title: (q) => `Recognised as “${q}”`,
    note: "The AI matched the wording. It's saved now, so the AI isn't asked about it again.",
    className: "bg-success-soft",
  },
  drafted: {
    title: () => "AI draft from your resume",
    note: "Used for the form, and added to Needs review so you can check it.",
    className: "bg-warning-soft",
  },
  unanswered: {
    title: (q) => `“${q}” is in your bank, but not answered yet`,
    note: "Write its answer under Needs answer.",
    className: "bg-warning-soft",
  },
  new: {
    title: () => "Not in your resume or Answer Bank",
    note: "Added to Needs answer. Write the answer once and it's used from then on.",
    className: "bg-destructive/10",
  },
};

/** Ask a question the way a form would, and see exactly how auto-apply will answer it. */
export function TryQuestionCard({ onDone }: { onDone: () => void }) {
  const [question, setQuestion] = useState("");
  const [options, setOptions] = useState("");
  const [result, setResult] = useState<TryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const list = options.split(",").map((option) => option.trim()).filter(Boolean);
      setResult(await answersApi.tryQuestion(question, list));
      onDone();
    } catch (err) {
      setError((err as Error).message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  const outcome = result ? OUTCOMES[result.how !== "new" && !result.answer ? "unanswered" : result.how] : null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Test a question</CardTitle>
        <CardDescription>Type a question the way a form asks it. Auto-apply answers forms exactly like this.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid grid-cols-1 gap-2" onSubmit={submit}>
          <Input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="e.g. How soon can you join?" aria-label="Question to test" />
          <Input value={options} onChange={(e) => setOptions(e.target.value)} placeholder="Options, if any (Yes, No)" aria-label="Options (comma separated)" />
          <Button type="submit" variant="outline" disabled={busy || !question.trim()}><Search /> Find the answer</Button>
        </form>
        {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
        {result && outcome ? (
          <div className={cn("mt-3 grid grid-cols-1 gap-1 rounded-lg p-3 text-sm", outcome.className)} role="status">
            <p className="font-medium break-words">{outcome.title(result.entry.question)}</p>
            {result.answer ? <p className="break-words">Answer: <b>{result.answer}</b></p> : null}
            <p className="text-xs text-muted-foreground">{outcome.note}</p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
