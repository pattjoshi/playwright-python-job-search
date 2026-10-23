"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { countByStatus, type StatusCounts } from "@/components/answers/meta";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { answersApi } from "@/lib/api/endpoints";

/** What in the Answer Bank needs you: questions to answer and AI drafts to review. */
export function AnswerBankCard() {
  const [counts, setCounts] = useState<StatusCounts | null>(null);

  useEffect(() => {
    let live = true;
    answersApi.list().then((body) => live && setCounts(countByStatus(body.answers)), () => undefined);
    return () => {
      live = false;
    };
  }, []);

  if (!counts) return null;
  const total = counts.answered + counts.needs_answer + counts.needs_review;
  const rows: [string, number, string][] = [
    ["Need your answer", counts.needs_answer, "text-destructive"],
    ["AI drafts to review", counts.needs_review, "text-warning"],
    ["Answered", counts.answered, "text-success"],
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Answer Bank</CardTitle>
        <CardDescription>{total ? "Answers auto-apply puts in forms." : "Save answers to common form questions."}</CardDescription>
        <CardAction>
          <Button asChild variant="outline" size="sm"><Link href="/answers">{total ? "Open" : "Set up"}</Link></Button>
        </CardAction>
      </CardHeader>
      {total ? (
        <CardContent>
          <ul className="grid grid-cols-1 gap-1.5 text-sm">
            {rows.map(([label, count, color]) => (
              <li key={label} className="flex items-center justify-between">
                <span className="text-muted-foreground">{label}</span>
                <b className={count ? color : "text-muted-foreground"}>{count}</b>
              </li>
            ))}
          </ul>
        </CardContent>
      ) : null}
    </Card>
  );
}
