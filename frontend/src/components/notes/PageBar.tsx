"use client";

import { Trash2 } from "lucide-react";

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { NoteSummary } from "@/lib/types";

import { pathTo, withDescendants } from "./blocks";

interface PageBarProps {
  pages: NoteSummary[];
  page: NoteSummary;
  onOpen: (id: number) => void;
  onMove: (parentId: number | null) => void;
  onDelete: () => void;
}

/** Above a page: where it sits (breadcrumbs), "Move to", and delete. */
export function PageBar({ pages, page, onOpen, onMove, onDelete }: PageBarProps) {
  const blocked = withDescendants(pages, page.id);
  const inside = pages.filter((p) => p.parent_id === page.id).length;
  const path = pathTo(pages, page.id);
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <nav aria-label="Breadcrumb" className="flex min-w-0 flex-1 flex-wrap items-center gap-1 text-muted-foreground">
        {path.map((p, i) => (
          <span key={p.id} className="flex min-w-0 items-center gap-1">
            {i ? <span aria-hidden="true">/</span> : null}
            <button type="button" onClick={() => onOpen(p.id)} className="truncate hover:text-foreground">{p.icon} {p.title || "Untitled"}</button>
          </span>
        ))}
      </nav>
      <Select value={page.parent_id === null ? "top" : String(page.parent_id)} onValueChange={(v) => onMove(v === "top" ? null : Number(v))}>
        <SelectTrigger size="sm" aria-label="Move to" className="w-44"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="top">Top level</SelectItem>
          {pages.filter((p) => !blocked.has(p.id)).map((p) => (
            <SelectItem key={p.id} value={String(p.id)}>Inside {p.icon} {p.title || "Untitled"}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-destructive" aria-label="Delete page"><Trash2 /></Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this page?</AlertDialogTitle>
            <AlertDialogDescription>
              “{page.title || "Untitled"}”{inside ? " and the pages inside it" : ""} will be deleted. This can&apos;t be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={onDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
