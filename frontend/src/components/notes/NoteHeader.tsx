"use client";

import { SmilePlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

const ICONS = ["📝", "🎯", "💼", "🏢", "📚", "💡", "✅", "📅", "🔥", "⭐", "🚀", "🧠", "💰", "🤝", "📈", "🗂️"];
const SAVED_TEXT = { saved: "Saved", saving: "Saving…", error: "Couldn't save, retrying with your next change" };

interface NoteHeaderProps {
  title: string;
  icon: string;
  saved: "saved" | "saving" | "error";
  onTitle: (title: string) => void;
  onIcon: (icon: string) => void;
  onEnter: () => void;
}

/** The page's icon (an emoji) and big title, and whether the latest change is saved. */
export function NoteHeader({ title, icon, saved, onTitle, onIcon, onEnter }: NoteHeaderProps) {
  return (
    <div className="grid grid-cols-1 gap-2">
      <div className="flex items-center gap-2">
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="ghost" size={icon ? "icon" : "sm"} aria-label="Page icon" className={icon ? "text-3xl" : "text-muted-foreground"}>
              {icon || <><SmilePlus /> Add icon</>}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-64">
            <div className="grid grid-cols-8 gap-1">
              {ICONS.map((emoji) => (
                <button key={emoji} type="button" onClick={() => onIcon(emoji)} className="rounded p-1 text-xl hover:bg-accent" aria-label={`Icon ${emoji}`}>
                  {emoji}
                </button>
              ))}
            </div>
            {icon ? <Button variant="ghost" size="sm" className="mt-2 w-full" onClick={() => onIcon("")}>Remove icon</Button> : null}
          </PopoverContent>
        </Popover>
        <span className="ml-auto text-xs text-muted-foreground" role="status">{SAVED_TEXT[saved]}</span>
      </div>
      <input
        value={title} onChange={(e) => onTitle(e.target.value)} placeholder="Untitled" aria-label="Page title"
        onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), onEnter())}
        className="w-full bg-transparent text-4xl font-bold tracking-tight outline-none placeholder:text-muted-foreground/50"
      />
    </div>
  );
}
