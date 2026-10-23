"use client";

import { useCallback, useEffect, useState } from "react";

import { notesApi } from "@/lib/api/endpoints";
import { loadLastNote, saveLastNote } from "@/lib/storage";
import type { NoteSummary } from "@/lib/types";

/** The notes page tree, which page is open, and adding, moving and deleting pages. */
export function useNotes() {
  const [pages, setPages] = useState<NoteSummary[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    notesApi.tree()
      .then(({ pages: loaded }) => {
        if (cancelled) return;
        setPages(loaded);
        const last = loadLastNote();
        setSelected(loaded.some((p) => p.id === last) ? last : (loaded.find((p) => p.parent_id === null)?.id ?? null));
      })
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, []);

  const select = useCallback((id: number | null) => {
    setSelected(id);
    saveLastNote(id);
  }, []);

  const create = useCallback(async (parentId: number | null = null) => {
    const { page } = await notesApi.create({ parent_id: parentId });
    setPages((current) => [...(current ?? []), page]);
    select(page.id);
    return page;
  }, [select]);

  const rename = useCallback((id: number, patch: { title?: string; icon?: string }) => {
    setPages((current) => (current ?? []).map((p) => (p.id === id ? { ...p, ...patch } : p)));
  }, []);

  const move = useCallback(async (id: number, parentId: number | null) => {
    const position = (pages ?? []).filter((p) => p.parent_id === parentId && p.id !== id).length;
    setPages((await notesApi.move(id, parentId, position)).pages);
  }, [pages]);

  const remove = useCallback(async (id: number) => {
    await notesApi.remove(id);
    const { pages: left } = await notesApi.tree();
    setPages(left);
    if (!left.some((p) => p.id === selected)) select(left.find((p) => p.parent_id === null)?.id ?? null);
  }, [select, selected]);

  return { pages, selected, error, select, create, rename, move, remove };
}

export type NotesApi = ReturnType<typeof useNotes>;
