"use client";

import { ChevronRight, FileText, Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { NoteSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

interface NoteTreeProps {
  pages: NoteSummary[];
  selected: number | null;
  onSelect: (id: number) => void;
  onAdd: (parentId: number | null) => void;
}

/** The sidebar: pages inside pages, like Notion. */
export function NoteTree({ pages, selected, onSelect, onAdd }: NoteTreeProps) {
  const [closed, setClosed] = useState<Set<number>>(new Set());
  const children = (parent: number | null) => pages.filter((p) => p.parent_id === parent);
  const toggle = (id: number) =>
    setClosed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const branch = (parent: number | null, depth: number): React.ReactNode => (
    <ul className="grid grid-cols-1" role={depth ? "group" : "tree"} aria-label={depth ? undefined : "Pages"}>
      {children(parent).map((page) => {
        const kids = children(page.id);
        const open = !closed.has(page.id);
        return (
          <li key={page.id} role="treeitem" aria-expanded={kids.length ? open : undefined} aria-selected={page.id === selected}>
            <div
              className={cn("group flex items-center gap-1 rounded-md pr-1 text-sm hover:bg-accent/60", page.id === selected && "bg-accent font-medium")}
              style={{ paddingLeft: depth * 12 }}
            >
              <button
                type="button" onClick={() => toggle(page.id)} aria-label={open ? "Collapse" : "Expand"}
                className={cn("grid size-6 shrink-0 place-items-center rounded text-muted-foreground hover:bg-accent", !kids.length && "invisible")}
              >
                <ChevronRight className={cn("size-3.5 transition-transform", open && "rotate-90")} />
              </button>
              <button type="button" onClick={() => onSelect(page.id)} className="flex min-w-0 flex-1 items-center gap-1.5 py-1.5 text-left">
                {page.icon ? <span aria-hidden="true">{page.icon}</span> : <FileText className="size-4 shrink-0 text-muted-foreground" />}
                <span className="truncate">{page.title || "Untitled"}</span>
              </button>
              <button
                type="button" onClick={() => onAdd(page.id)} aria-label={`Add a page inside ${page.title || "Untitled"}`}
                className="grid size-6 place-items-center rounded text-muted-foreground opacity-0 group-hover:opacity-100 hover:bg-accent focus-visible:opacity-100"
              >
                <Plus className="size-3.5" />
              </button>
            </div>
            {kids.length && open ? branch(page.id, depth + 1) : null}
          </li>
        );
      })}
    </ul>
  );

  return (
    <nav className="grid grid-cols-1 gap-2" aria-label="Notes">
      {branch(null, 0)}
      <Button variant="ghost" size="sm" className="justify-start text-muted-foreground" onClick={() => onAdd(null)}>
        <Plus /> New page
      </Button>
    </nav>
  );
}
