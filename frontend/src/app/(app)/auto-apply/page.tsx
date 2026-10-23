import { Bot } from "lucide-react";
import type { Metadata } from "next";

import { ComingSoon } from "@/components/coming-soon/ComingSoon";

export const metadata: Metadata = { title: "Auto-apply" };

export default function AutoApplyPage() {
  return (
    <ComingSoon
      title="Auto-apply" phase={4} icon={Bot}
      description="Apply to your best matches automatically, with safety limits."
      features={[
        "Company career pages first (Greenhouse, Lever, Ashby)",
        "Then Naukri, LinkedIn Easy Apply and Indeed",
        "Practice mode, daily limits and a Pause button",
        "Proof screenshot and log for every application",
      ]}
    />
  );
}
