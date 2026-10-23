import type { Answer } from "@/lib/types";

import { AnswerRow } from "./AnswerRow";

interface AnswerGroupProps {
  label: string;
  items: Answer[];
  onSave: (item: Answer, answer: string) => Promise<void>;
  onApprove: (item: Answer) => Promise<void>;
  onEdit: (item: Answer) => void;
  onDelete: (item: Answer) => void;
}

/** The questions of one category. */
export function AnswerGroup({ label, items, ...actions }: AnswerGroupProps) {
  return (
    <section aria-label={label} className="grid grid-cols-1 gap-2">
      <h3 className="text-sm font-semibold text-muted-foreground">{label} <span className="font-normal">· {items.length}</span></h3>
      <ul className="grid grid-cols-1 gap-2">
        {/* The key changes when the saved answer does, so the box shows what was saved. */}
        {items.map((item) => <AnswerRow key={`${item.id}-${item.updated_at}-${item.status}`} item={item} {...actions} />)}
      </ul>
    </section>
  );
}
