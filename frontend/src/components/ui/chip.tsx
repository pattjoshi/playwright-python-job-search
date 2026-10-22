import { cn } from "@/lib/utils";

export type ChipKind = "key" | "skill" | "have" | "miss";

const KINDS: Record<ChipKind, string> = {
  key: "bg-accent font-semibold text-accent-foreground",
  skill: "bg-muted text-muted-foreground",
  have: "bg-success-soft text-success",
  miss: "border border-input text-muted-foreground",
};

export function Chip({ kind, children }: { kind: ChipKind; children: React.ReactNode }) {
  return <span className={cn("rounded-full px-2.5 py-0.5 text-xs", KINDS[kind])}>{children}</span>;
}

export function ChipLabel({ children }: { children: React.ReactNode }) {
  return <span className="mr-1 text-[11px] font-bold tracking-wider text-muted-foreground uppercase">{children}</span>;
}

export function Chips({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("my-1.5 flex flex-wrap items-center gap-1.5", className)}>{children}</div>;
}

/** "MATCHING  Python  FastAPI": a label followed by chips. Hidden when empty. */
export function ChipRow({ label, items, kind }: { label: string; items: string[]; kind: ChipKind }) {
  if (!items.length) return null;
  return (
    <Chips>
      <ChipLabel>{label}</ChipLabel>
      {items.map((item) => <Chip key={item} kind={kind}>{item}</Chip>)}
    </Chips>
  );
}
