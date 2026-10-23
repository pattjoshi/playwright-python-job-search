import { BookOpenText, ListPlus, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";

interface AnswersEmptyProps {
  busy: boolean;
  canFill: boolean;
  onStarters: () => void;
  onAdd: () => void;
}

/** A new, empty bank: one click adds the common questions (and fills what the resume answers). */
export function AnswersEmpty({ busy, canFill, onStarters, onAdd }: AnswersEmptyProps) {
  return (
    <Empty className="border">
      <EmptyHeader>
        <EmptyMedia variant="icon"><BookOpenText /></EmptyMedia>
        <EmptyTitle>Your Answer Bank is empty</EmptyTitle>
        <EmptyDescription>
          Start with about 25 questions forms ask most (notice period, expected CTC, relocation…).
          {canFill
            ? " The AI fills in what your resume says; you write the rest."
            : " Upload your resume on the Search jobs page and the AI can fill in what it says."}
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent className="flex-row flex-wrap justify-center">
        <Button onClick={onStarters} disabled={busy}><ListPlus /> Add common questions</Button>
        <Button variant="outline" onClick={onAdd}><Plus /> Add your own</Button>
      </EmptyContent>
    </Empty>
  );
}
