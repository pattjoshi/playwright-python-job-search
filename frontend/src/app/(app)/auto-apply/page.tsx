import type { Metadata } from "next";

import { AutoApplyPage } from "@/components/auto-apply/AutoApplyPage";

export const metadata: Metadata = { title: "Auto-apply" };

export default function Page() {
  return <AutoApplyPage />;
}
