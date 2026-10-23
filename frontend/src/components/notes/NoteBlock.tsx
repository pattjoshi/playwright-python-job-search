"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";

import { Checkbox } from "@/components/ui/checkbox";
import type { Block, BlockType } from "@/lib/types";
import { cn } from "@/lib/utils";

import { menuMatches, shortcut } from "./blocks";

const STYLES: Record<BlockType, string> = {
  paragraph: "text-[15px]", h1: "text-3xl font-bold", h2: "text-2xl font-semibold", h3: "text-xl font-semibold",
  todo: "text-[15px]", bullet: "text-[15px]", numbered: "text-[15px]", quote: "text-[15px] italic",
  code: "font-mono text-sm", divider: "",
};
const PLACEHOLDERS: Partial<Record<BlockType, string>> = {
  paragraph: "Type '/' for blocks", h1: "Heading 1", h2: "Heading 2", h3: "Heading 3", todo: "To-do", bullet: "List",
  numbered: "List", quote: "Quote", code: "Code",
};

export interface BlockActions {
  change: (id: string, patch: Partial<Block>) => void;
  /** Enter: split at the caret into a new block below. */
  split: (id: string, before: string, after: string) => void;
  /** Backspace at the start: merge into the block above (or remove an empty one). */
  merge: (id: string) => void;
  focusSibling: (id: string, direction: -1 | 1) => void;
  register: (id: string, element: HTMLTextAreaElement | null) => void;
}

interface NoteBlockProps {
  block: Block;
  number: number;
  actions: BlockActions;
}

/** One block: plain text with its type's look, Markdown shortcuts, the "/" menu and keyboard moves. */
export function NoteBlock({ block, number, actions }: NoteBlockProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: block.id });
  const area = useRef<HTMLTextAreaElement | null>(null);
  const [focused, setFocused] = useState(false);
  const [choice, setChoice] = useState(0);
  const menu = focused && block.text.startsWith("/") && !block.text.includes(" ") ? menuMatches(block.text.slice(1)) : [];

  useLayoutEffect(() => {  // grow with the text
    const el = area.current;
    if (el) {
      el.style.height = "0px";
      el.style.height = `${el.scrollHeight}px`;
    }
  }, [block.text, block.type]);

  const pick = (type: BlockType) => {
    actions.change(block.id, { type, text: "" });
    setChoice(0);
    if (type === "divider") actions.split(block.id, "", "");
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const el = e.currentTarget;
    const atStart = el.selectionStart === 0 && el.selectionEnd === 0;
    if (menu.length) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        setChoice((c) => (c + (e.key === "ArrowDown" ? 1 : menu.length - 1)) % menu.length);
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        pick(menu[Math.min(choice, menu.length - 1)].type);
        return;
      }
    }
    if (e.key === "Escape" && menu.length) actions.change(block.id, { text: "" });
    else if (e.key === "Enter" && !e.shiftKey && block.type !== "code") {
      e.preventDefault();
      actions.split(block.id, block.text.slice(0, el.selectionStart), block.text.slice(el.selectionEnd));
    } else if (e.key === "Backspace" && atStart) {
      e.preventDefault();
      if (block.type !== "paragraph") actions.change(block.id, { type: "paragraph" });  // first undo the block type
      else actions.merge(block.id);
    } else if (e.key === "ArrowUp" && atStart) {
      e.preventDefault();
      actions.focusSibling(block.id, -1);
    } else if (e.key === "ArrowDown" && el.selectionStart === block.text.length) {
      e.preventDefault();
      actions.focusSibling(block.id, 1);
    }
  };

  const onChange = (text: string) => {
    const type = block.type === "paragraph" ? shortcut(text) : null;
    if (type) pick(type);
    else actions.change(block.id, { text });
  };

  return (
    <div
      ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn("group relative flex items-start gap-1 rounded-md", isDragging && "z-10 bg-accent/60 opacity-80")}
    >
      <button
        type="button" {...attributes} {...listeners} aria-label="Drag to move this block"
        className="mt-1 cursor-grab text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
      >
        <GripVertical className="size-4" />
      </button>
      {block.type === "todo" ? (
        <Checkbox
          checked={block.checked} onCheckedChange={(on) => actions.change(block.id, { checked: on === true })}
          aria-label="Done" className="mt-1.5"
        />
      ) : null}
      {block.type === "bullet" ? <span className="mt-0.5 select-none text-muted-foreground" aria-hidden="true">•</span> : null}
      {block.type === "numbered" ? <span className="mt-0.5 min-w-5 select-none text-muted-foreground tabular-nums">{number}.</span> : null}
      {block.type === "divider" ? (
        <button
          type="button" ref={(el) => actions.register(block.id, el as unknown as HTMLTextAreaElement)} aria-label="Divider"
          onKeyDown={(e) => (e.key === "Backspace" || e.key === "Delete") && actions.merge(block.id)}
          className="my-3 h-px flex-1 bg-border focus-visible:outline-2 focus-visible:outline-ring"
        />
      ) : (
        <textarea
          ref={(el) => { area.current = el; actions.register(block.id, el); }}
          value={block.text} rows={1} spellCheck aria-label={`${block.type} block`}
          placeholder={focused ? PLACEHOLDERS[block.type] : block.type === "paragraph" ? "" : PLACEHOLDERS[block.type]}
          onChange={(e) => onChange(e.target.value)} onKeyDown={onKeyDown}
          onFocus={() => setFocused(true)} onBlur={() => setTimeout(() => setFocused(false), 150)}
          className={cn(
            "w-full min-w-0 flex-1 resize-none overflow-hidden bg-transparent py-0.5 leading-relaxed outline-none placeholder:text-muted-foreground/60",
            STYLES[block.type],
            block.type === "quote" && "border-l-4 border-border pl-3",
            block.type === "code" && "rounded-md bg-muted px-3 py-2",
            block.type === "todo" && block.checked && "text-muted-foreground line-through",
          )}
        />
      )}
      {menu.length ? (
        <ul role="listbox" aria-label="Block types" className="absolute top-full left-6 z-20 mt-1 w-60 rounded-md border bg-popover p-1 shadow-md">
          {menu.map((item, i) => (
            <li
              key={item.type} role="option" aria-selected={i === choice}
              onMouseDown={(e) => { e.preventDefault(); pick(item.type); }}
              className={cn("flex cursor-pointer justify-between rounded px-2 py-1.5 text-sm", i === choice && "bg-accent")}
            >
              {item.label}<span className="text-xs text-muted-foreground">{item.hint}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
