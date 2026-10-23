"use client";

import { BriefcaseBusiness, Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { applicationsApi } from "@/lib/api/endpoints";
import type { Job } from "@/lib/types";

/** Adds the job to the application tracker as "Saved" (once; pressing again just points to it). */
export function TrackButton({ job }: { job: Job }) {
  const router = useRouter();
  const [tracked, setTracked] = useState(false);
  const [busy, setBusy] = useState(false);

  const track = async () => {
    setBusy(true);
    try {
      const { created } = await applicationsApi.track({
        source: job.source, job_id: job.job_id, title: job.title, company: job.company, url: job.url, location: job.location,
      });
      setTracked(true);
      toast.success(created ? `Tracking “${job.title}”` : "Already in Applications", {
        action: { label: "View", onClick: () => router.push("/applications") },
      });
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Button variant="outline" size="sm" onClick={track} disabled={busy || tracked}>
      {tracked ? <Check /> : <BriefcaseBusiness />} {tracked ? "Tracked" : "Track"}
    </Button>
  );
}
