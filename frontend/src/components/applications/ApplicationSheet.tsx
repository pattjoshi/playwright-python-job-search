"use client";

import { ExternalLink, Pencil, Trash2 } from "lucide-react";

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { safeUrl } from "@/lib/format";
import type { Application, ApplicationStatus } from "@/lib/types";

import { ApplicationTimeline } from "./ApplicationTimeline";
import { isOverdue, shortDate, SOURCE_LABELS, STATUSES } from "./statuses";

interface ApplicationSheetProps {
  application: Application | null;
  onClose: () => void;
  onMove: (application: Application, status: ApplicationStatus) => void;
  onEdit: (application: Application) => void;
  onDelete: (application: Application) => void;
}

/** Everything about one application, with quick status change, edit and delete. */
export function ApplicationSheet({ application: app, onClose, onMove, onEdit, onDelete }: ApplicationSheetProps) {
  const url = app ? safeUrl(app.url) : null;
  const details: [string, string][] = app ? [
    ["Location", app.location], ["Salary / CTC", app.salary], ["Contact", app.contact],
    ["Applied on", shortDate(app.applied_on)], ["Follow up on", shortDate(app.follow_up_on)],
    ["Source", SOURCE_LABELS[app.source] ?? app.source],
  ] : [];
  return (
    <Sheet open={!!app} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-md">
        {app ? (
          <>
            <SheetHeader className="border-b">
              <SheetTitle className="pr-6">{app.title}</SheetTitle>
              <SheetDescription>{app.company}</SheetDescription>
            </SheetHeader>
            <div className="grid grid-cols-1 gap-5 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Select value={app.status} onValueChange={(status) => onMove(app, status as ApplicationStatus)}>
                  <SelectTrigger aria-label="Status" className="w-40"><SelectValue /></SelectTrigger>
                  <SelectContent>{STATUSES.map((s) => <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>)}</SelectContent>
                </Select>
                {url ? (
                  <Button asChild variant="outline" size="sm"><a href={url} target="_blank" rel="noopener noreferrer">View job <ExternalLink /></a></Button>
                ) : null}
              </div>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                {details.filter(([, value]) => value).map(([label, value]) => (
                  <div key={label} className="min-w-0">
                    <dt className="text-xs text-muted-foreground">{label}</dt>
                    <dd className={label === "Follow up on" && isOverdue(app.follow_up_on) ? "font-semibold text-destructive" : "break-words"}>{value}</dd>
                  </div>
                ))}
              </dl>
              {app.notes ? (
                <div>
                  <h4 className="mb-1 text-xs text-muted-foreground">Notes</h4>
                  <p className="text-sm whitespace-pre-wrap">{app.notes}</p>
                </div>
              ) : null}
              <ApplicationTimeline application={app} />
              <div className="flex gap-2 border-t pt-4">
                <Button variant="outline" onClick={() => onEdit(app)}><Pencil /> Edit</Button>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="ghost" className="text-destructive hover:text-destructive"><Trash2 /> Delete</Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete this application?</AlertDialogTitle>
                      <AlertDialogDescription>{app.title} at {app.company} and its timeline will be removed. This can&apos;t be undone.</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction onClick={() => onDelete(app)}>Delete</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
