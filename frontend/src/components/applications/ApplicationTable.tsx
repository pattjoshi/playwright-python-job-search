"use client";

import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useState } from "react";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Application } from "@/lib/types";
import { cn } from "@/lib/utils";

import { StatusBadge } from "./StatusBadge";
import { isOverdue, shortDate, STATUSES } from "./statuses";

type SortKey = "company" | "title" | "status" | "applied_on" | "follow_up_on" | "updated_at";

const COLUMNS: { key: SortKey; label: string; className?: string }[] = [
  { key: "company", label: "Company" },
  { key: "title", label: "Role" },
  { key: "status", label: "Status" },
  { key: "applied_on", label: "Applied", className: "max-md:hidden" },
  { key: "follow_up_on", label: "Follow-up", className: "max-md:hidden" },
  { key: "updated_at", label: "Updated", className: "max-lg:hidden" },
];
const STATUS_ORDER = Object.fromEntries(STATUSES.map((status, index) => [status.id, index]));

function compare(a: Application, b: Application, key: SortKey): number {
  if (key === "status") return STATUS_ORDER[a.status] - STATUS_ORDER[b.status];
  return (a[key] ?? "").localeCompare(b[key] ?? "");  // empty dates sort first
}

/** All applications as a sortable table (click a column heading to sort, a row to open it). */
export function ApplicationTable({ applications, onOpen }: { applications: Application[]; onOpen: (app: Application) => void }) {
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: "updated_at", desc: true });
  const rows = [...applications].sort((a, b) => compare(a, b, sort.key) * (sort.desc ? -1 : 1));
  const toggle = (key: SortKey) => setSort((current) => ({ key, desc: current.key === key ? !current.desc : key.endsWith("_at") }));

  return (
    <div className="rounded-xl border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            {COLUMNS.map((column) => {
              const active = sort.key === column.key;
              const Icon = !active ? ArrowUpDown : sort.desc ? ArrowDown : ArrowUp;
              return (
                <TableHead key={column.key} className={column.className} aria-sort={active ? (sort.desc ? "descending" : "ascending") : "none"}>
                  <button type="button" onClick={() => toggle(column.key)} className="inline-flex items-center gap-1 hover:text-foreground">
                    {column.label}<Icon className={cn("size-3.5", !active && "opacity-40")} />
                  </button>
                </TableHead>
              );
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((app) => (
            <TableRow key={app.id} className="cursor-pointer" onClick={() => onOpen(app)}>
              <TableCell className="max-w-48 truncate font-medium">
                <button type="button" className="truncate text-left hover:underline" onClick={(e) => { e.stopPropagation(); onOpen(app); }}>
                  {app.company}
                </button>
              </TableCell>
              <TableCell className="max-w-64 truncate">{app.title}</TableCell>
              <TableCell><StatusBadge status={app.status} /></TableCell>
              <TableCell className="max-md:hidden">{shortDate(app.applied_on) || "–"}</TableCell>
              <TableCell className={cn("max-md:hidden", isOverdue(app.follow_up_on) && "font-semibold text-destructive")}>
                {shortDate(app.follow_up_on) || "–"}
              </TableCell>
              <TableCell className="text-muted-foreground max-lg:hidden">{shortDate(app.updated_at.slice(0, 10))}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
