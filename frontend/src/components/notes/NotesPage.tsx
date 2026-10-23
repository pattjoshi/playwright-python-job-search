"use client";

import { NotebookPen, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { useNotes } from "@/hooks/useNotes";
import { notesApi } from "@/lib/api/endpoints";
import type { NotePage } from "@/lib/types";

import { NoteEditor } from "./NoteEditor";
import { NoteTree } from "./NoteTree";
import { PageBar } from "./PageBar";

/** Notion-style notes: a page tree on the left, the open page on the right. */
export function NotesPage() {
  const { pages, selected, error, select, create, rename, move, remove } = useNotes();
  const [page, setPage] = useState<NotePage | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (selected === null) return;
    let cancelled = false;
    notesApi.get(selected)
      .then(({ page: loaded }) => { if (!cancelled) { setPage(loaded); setLoadError(null); } })
      .catch((err: Error) => !cancelled && setLoadError(err.message));
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const run = (action: () => Promise<unknown>) => action().catch((err: Error) => toast.error(err.message));
  const summary = pages?.find((p) => p.id === selected);

  if (error) return <p className="text-sm text-destructive">{error}</p>;
  if (!pages) return <Skeleton className="h-96" />;
  if (!pages.length) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon"><NotebookPen /></EmptyMedia>
          <EmptyTitle>No notes yet</EmptyTitle>
          <EmptyDescription>Keep company research, interview questions and plans here. Type “/” in a page for headings, to-dos and lists.</EmptyDescription>
        </EmptyHeader>
        <EmptyContent><Button onClick={() => run(() => create(null))}><Plus /> New page</Button></EmptyContent>
      </Empty>
    );
  }
  return (
    <div className="grid grid-cols-1 items-start gap-6 md:grid-cols-[15rem_minmax(0,1fr)]">
      <aside className="rounded-lg border bg-card p-2 md:sticky md:top-20 md:max-h-[calc(100svh-6rem)] md:overflow-y-auto">
        <NoteTree pages={pages} selected={selected} onSelect={select} onAdd={(parent) => run(() => create(parent))} />
      </aside>
      <section className="min-w-0">
        {loadError ? <p className="text-sm text-destructive">{loadError}</p> : null}
        {page && summary && page.id === selected ? (
          <NoteEditor
            key={page.id} page={page} onRenamed={(patch) => rename(page.id, patch)}
            header={
              <PageBar
                pages={pages} page={summary} onOpen={select}
                onMove={(parent) => run(() => move(page.id, parent))}
                onDelete={() => run(async () => { await remove(page.id); toast("Page deleted"); })}
              />
            }
          />
        ) : selected === null ? <p className="text-sm text-muted-foreground">Pick a page on the left.</p> : <Skeleton className="h-64" />}
      </section>
    </div>
  );
}
