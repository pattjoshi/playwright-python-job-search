"use client";

import { useDraggable } from "@dnd-kit/core";
import { CalendarClock, MapPin } from "lucide-react";

import type { Application } from "@/lib/types";
import { cn } from "@/lib/utils";

import { isOverdue, shortDate, SOURCE_LABELS } from "./statuses";

interface ApplicationCardProps {
  application: Application;
  onOpen: (application: Application) => void;
}

/** A card on the board: drag it to another column, or click it to open the details. */
export function ApplicationCard({ application: app, onOpen }: ApplicationCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: app.id });
  const style = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined;
  const overdue = isOverdue(app.follow_up_on);
  return (
    <button
      ref={setNodeRef} style={style} {...listeners} {...attributes} onClick={() => onOpen(app)}
      aria-label={`${app.title} at ${app.company}. Open details, or drag to change status`}
      className={cn(
        "w-full cursor-grab touch-none rounded-lg border bg-card p-3 text-left shadow-xs transition-shadow hover:shadow-md active:cursor-grabbing",
        isDragging && "relative z-50 opacity-90 shadow-lg ring-2 ring-primary",
      )}
    >
      <p className="truncate text-sm font-semibold">{app.title}</p>
      <p className="truncate text-xs text-muted-foreground">{app.company}</p>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        {app.location ? <span className="inline-flex items-center gap-1"><MapPin className="size-3" />{app.location}</span> : null}
        {app.follow_up_on ? (
          <span className={cn("inline-flex items-center gap-1", overdue && "font-semibold text-destructive")}>
            <CalendarClock className="size-3" />Follow up {shortDate(app.follow_up_on)}
          </span>
        ) : null}
        <span>{SOURCE_LABELS[app.source] ?? app.source}</span>
      </div>
    </button>
  );
}
