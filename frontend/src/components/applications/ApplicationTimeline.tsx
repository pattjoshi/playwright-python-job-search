"use client";

import { useEffect, useState } from "react";

import { applicationsApi } from "@/lib/api/endpoints";
import { formatDateTime } from "@/lib/format";
import type { Application, ApplicationEvent } from "@/lib/types";

import { STATUS_BY_ID } from "./statuses";

/** When the application was added and every status change, newest first. Reloads when it changes. */
export function ApplicationTimeline({ application }: { application: Application }) {
  const [events, setEvents] = useState<ApplicationEvent[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    applicationsApi.get(application.id).then((body) => !cancelled && setEvents(body.events)).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [application.id, application.updated_at]);

  if (!events?.length) return null;
  return (
    <div>
      <h4 className="mb-2 text-xs text-muted-foreground">Timeline</h4>
      <ol className="relative grid grid-cols-1 gap-3 border-l pl-4">
        {events.map((event, index) => (
          <li key={`${event.at}-${index}`} className="relative text-sm">
            <span className="absolute top-1.5 -left-[21px] size-2.5 rounded-full border-2 border-background bg-primary" />
            {event.kind === "created"
              ? <>Added as <b>{STATUS_BY_ID[event.to_status ?? "saved"].label}</b></>
              : <>Moved to <b>{STATUS_BY_ID[event.to_status ?? "saved"].label}</b></>}
            <span className="block text-xs text-muted-foreground">{formatDateTime(event.at)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
