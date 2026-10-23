"use client";

import { closestCenter, DndContext, type DragEndEvent, KeyboardSensor, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { notesApi } from "@/lib/api/endpoints";
import type { Block, NotePage } from "@/lib/types";

import { listNumber, newBlock, nextType } from "./blocks";
import { type BlockActions, NoteBlock } from "./NoteBlock";
import { NoteHeader } from "./NoteHeader";

const SAVE_AFTER_MS = 700;

interface NoteEditorProps {
  page: NotePage;
  /** The title or icon changed (the sidebar shows it). */
  onRenamed: (patch: { title?: string; icon?: string }) => void;
  header: React.ReactNode;
}

/** A page: icon, title and blocks. Everything saves by itself a moment after you stop typing. */
export function NoteEditor({ page, onRenamed, header }: NoteEditorProps) {
  const [blocks, setBlocks] = useState<Block[]>(() => (page.content.length ? page.content : [newBlock()]));
  const [title, setTitle] = useState(page.title);
  const [icon, setIcon] = useState(page.icon);
  const [saved, setSaved] = useState<"saved" | "saving" | "error">("saved");
  const elements = useRef(new Map<string, HTMLTextAreaElement>());
  const focusNext = useRef<{ id: string; caret: number } | null>(null);
  const pending = useRef<{ title?: string; icon?: string; content?: Block[] }>({});
  const timer = useRef<number | undefined>(undefined);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }));

  const flush = useCallback(async () => {
    const body = pending.current;
    pending.current = {};
    if (!Object.keys(body).length) return;
    setSaved("saving");
    try {
      await notesApi.update(page.id, body);
      setSaved("saved");
    } catch {
      pending.current = { ...body, ...pending.current };  // try again with the next change
      setSaved("error");
    }
  }, [page.id]);

  const save = useCallback((patch: typeof pending.current) => {
    pending.current = { ...pending.current, ...patch };
    setSaved("saving");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void flush(), SAVE_AFTER_MS);
  }, [flush]);

  useEffect(() => () => {  // leaving the page saves what's left
    window.clearTimeout(timer.current);
    void flush();
  }, [flush]);

  useLayoutEffect(() => {  // put the cursor where an edit left it
    const target = focusNext.current;
    const el = target && elements.current.get(target.id);
    if (target && el) {
      el.focus();
      if ("setSelectionRange" in el) el.setSelectionRange(target.caret, target.caret);
      focusNext.current = null;
    }
  });

  const update = (next: Block[]) => {
    setBlocks(next);
    save({ content: next });
  };

  const actions: BlockActions = {
    change: (id, patch) => update(blocks.map((b) => (b.id === id ? { ...b, ...patch } : b))),
    split: (id, before, after) => {
      const index = blocks.findIndex((b) => b.id === id);
      const current = blocks[index];
      if (!before && !after && ["bullet", "numbered", "todo"].includes(current.type)) {  // Enter on an empty item ends the list
        actions.change(id, { type: "paragraph" });
        return;
      }
      const added = newBlock(current.type === "divider" ? "paragraph" : nextType(current.type), after);
      focusNext.current = { id: added.id, caret: 0 };
      update([...blocks.slice(0, index), { ...current, text: before }, added, ...blocks.slice(index + 1)]);
    },
    merge: (id) => {
      const index = blocks.findIndex((b) => b.id === id);
      if (index <= 0) return;
      const above = blocks[index - 1];
      const rest = blocks.filter((b) => b.id !== id);
      if (above.type === "divider") {
        update(rest);
        focusNext.current = { id: blocks[index].id, caret: 0 };
        return;
      }
      focusNext.current = { id: above.id, caret: above.text.length };
      update(rest.map((b) => (b.id === above.id ? { ...b, text: b.text + blocks[index].text } : b)));
    },
    focusSibling: (id, direction) => {
      const sibling = blocks[blocks.findIndex((b) => b.id === id) + direction];
      if (sibling) elements.current.get(sibling.id)?.focus();
    },
    register: (id, element) => {
      if (element) elements.current.set(id, element);
      else elements.current.delete(id);
    },
  };

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const from = blocks.findIndex((b) => b.id === active.id);
    const to = blocks.findIndex((b) => b.id === over.id);
    update(arrayMove(blocks, from, to));
  };

  return (
    <article className="mx-auto grid w-full max-w-3xl grid-cols-1 gap-4">
      {header}
      <NoteHeader
        title={title} icon={icon} saved={saved}
        onTitle={(value) => { setTitle(value); save({ title: value }); onRenamed({ title: value }); }}
        onIcon={(value) => { setIcon(value); save({ icon: value }); onRenamed({ icon: value }); }}
        onEnter={() => elements.current.get(blocks[0]?.id)?.focus()}
      />
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
        <SortableContext items={blocks.map((b) => b.id)} strategy={verticalListSortingStrategy}>
          <div className="-ml-5 grid grid-cols-1 gap-0.5 pb-24" aria-label="Page content">
            {blocks.map((block, index) => (
              <NoteBlock key={block.id} block={block} number={listNumber(blocks, index)} actions={actions} />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </article>
  );
}
