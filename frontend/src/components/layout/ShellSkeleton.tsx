import { Skeleton } from "@/components/ui/skeleton";

/** Shown for a moment while the app loads its settings. */
export function ShellSkeleton() {
  return (
    <div className="flex min-h-svh" aria-busy="true" aria-label="Loading">
      <div className="hidden w-60 shrink-0 flex-col gap-2 border-r bg-sidebar p-3 md:flex">
        <Skeleton className="mb-4 h-8 w-32" />
        {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-9 w-full" />)}
      </div>
      <div className="flex-1 p-6">
        <Skeleton className="mb-6 h-8 w-48" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <Skeleton className="mt-4 h-64" />
      </div>
    </div>
  );
}
