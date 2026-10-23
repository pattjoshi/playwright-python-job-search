"use client";

import { DndContext, type DragEndEvent, KeyboardSensor, PointerSensor, useDroppable, useSensor, useSensors } from "@dnd-kit/core";

import type { Application, ApplicationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

import { ApplicationCard } from "./ApplicationCard";
import { type StatusInfo, STATUSES } from "./statuses";

interface ApplicationBoardProps {
  applications: Application[];
  onMove: (application: Application, status: ApplicationStatus) => void;
  onOpen: (application: Application) => void;
}

/** One column per status; drag a card (mouse, touch or keyboard: Space, arrows, Space) to move it. */
export function ApplicationBoard({ applications, onMove, onOpen }: ApplicationBoardProps) {
  // A small move before dragging starts, so a click still opens the card.
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor));
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    const app = applications.find((item) => item.id === active.id);
    const status = over?.id as ApplicationStatus | undefined;
    if (app && status && status !== app.status) onMove(app, status);
  };
  return (
    <DndContext sensors={sensors} onDragEnd={onDragEnd}>
      <div className="-mx-4 flex gap-3 overflow-x-auto px-4 pb-3 md:-mx-6 md:px-6">
        {STATUSES.map((status) => (
          <Column key={status.id} status={status} items={applications.filter((app) => app.status === status.id)} onOpen={onOpen} />
        ))}
      </div>
    </DndContext>
  );
}

function Column({ status, items, onOpen }: { status: StatusInfo; items: Application[]; onOpen: (app: Application) => void }) {
  const { setNodeRef, isOver } = useDroppable({ id: status.id });
  return (
    <section
      ref={setNodeRef} aria-label={`${status.label} (${items.length})`}
      className={cn("flex w-64 shrink-0 flex-col rounded-xl border bg-muted/40 transition-colors", isOver && "border-primary bg-accent/60")}
    >
      <h3 className="flex items-center gap-2 px-3 pt-3 pb-2 text-sm font-semibold">
        <span className={cn("size-2 rounded-full", status.dot)} />
        {status.label}
        <span className="ml-auto rounded-full bg-background px-2 text-xs text-muted-foreground tabular-nums">{items.length}</span>
      </h3>
      <div className="flex min-h-24 flex-col gap-2 px-2 pb-2">
        {items.map((app) => <ApplicationCard key={app.id} application={app} onOpen={onOpen} />)}
        {!items.length ? <p className="px-1 py-4 text-center text-xs text-muted-foreground">Drop here</p> : null}
      </div>
    </section>
  );
}
