import { cn } from "@/lib/utils";
import type { ApplicationStatus } from "@/lib/types";

import { STATUS_BY_ID } from "./statuses";

export function StatusBadge({ status, className }: { status: ApplicationStatus; className?: string }) {
  const info = STATUS_BY_ID[status];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium", info.badge, className)}>
      <span className={cn("size-1.5 rounded-full", info.dot)} />
      {info.label}
    </span>
  );
}
