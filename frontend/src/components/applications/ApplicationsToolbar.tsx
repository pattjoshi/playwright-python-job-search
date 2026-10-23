"use client";

import { Columns3, Search, Table2 } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

import { STATUSES } from "./statuses";

export type TrackerView = "board" | "table";

interface ApplicationsToolbarProps {
  query: string;
  onQuery: (query: string) => void;
  view: TrackerView;
  onView: (view: TrackerView) => void;
  status: string;
  onStatus: (status: string) => void;
}

/** Search box, Board/Table switch and (in the table) a status filter. */
export function ApplicationsToolbar({ query, onQuery, view, onView, status, onStatus }: ApplicationsToolbarProps) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <div className="relative min-w-0 flex-1 basis-56">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <Input
          type="search" value={query} onChange={(event) => onQuery(event.target.value)}
          placeholder="Search company, title, location or notes" aria-label="Search applications" className="pl-8"
        />
      </div>
      {view === "table" ? (
        <Select value={status || "all"} onValueChange={(value) => onStatus(value === "all" ? "" : value)}>
          <SelectTrigger aria-label="Filter by status" className="w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {STATUSES.map((s) => <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>)}
          </SelectContent>
        </Select>
      ) : null}
      <ToggleGroup
        type="single" variant="outline" value={view} aria-label="View"
        onValueChange={(value) => value && onView(value as TrackerView)}
      >
        <ToggleGroupItem value="board" aria-label="Board view"><Columns3 /> Board</ToggleGroupItem>
        <ToggleGroupItem value="table" aria-label="Table view"><Table2 /> Table</ToggleGroupItem>
      </ToggleGroup>
    </div>
  );
}
