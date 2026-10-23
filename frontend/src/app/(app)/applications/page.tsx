import type { Metadata } from "next";

import { ApplicationsPage } from "@/components/applications/ApplicationsPage";

export const metadata: Metadata = { title: "Applications" };

export default function Page() {
  return <ApplicationsPage />;
}
