import { BriefcaseBusiness } from "lucide-react";
import type { Metadata } from "next";

import { ComingSoon } from "@/components/coming-soon/ComingSoon";

export const metadata: Metadata = { title: "Applications" };

export default function ApplicationsPage() {
  return (
    <ComingSoon
      title="Applications" phase={2} icon={BriefcaseBusiness}
      description="Track every job you apply to, from saved to offer."
      features={[
        "Board view: drag jobs from Applied to Interview to Offer",
        "Table view with search, filters and sorting",
        "Follow-up dates, contacts and notes per job",
        "“Track” button on every search result",
      ]}
    />
  );
}
