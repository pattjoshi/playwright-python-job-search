import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

interface StepTitleProps {
  step: number;
  done?: boolean;
  aside?: React.ReactNode;
  children: React.ReactNode;
}

/** "1  Resume" card heading with a numbered step that turns into a check mark when done. */
export function StepTitle({ step, done, aside, children }: StepTitleProps) {
  return (
    <h3 className="flex items-center gap-2.5 text-sm font-semibold">
      <span className={cn("grid size-6 shrink-0 place-items-center rounded-full text-xs font-bold",
        done ? "bg-success-soft text-success" : "bg-accent text-accent-foreground")}
      >
        {done ? <Check className="size-3.5" aria-label="Done" /> : step}
      </span>
      {children}
      {aside ? <span className="ml-auto text-xs font-normal text-muted-foreground">{aside}</span> : null}
    </h3>
  );
}
