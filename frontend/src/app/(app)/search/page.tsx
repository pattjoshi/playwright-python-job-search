import type { Metadata } from "next";

import { LocalOnly } from "@/components/layout/LocalOnly";
import { SearchPage } from "@/components/search/SearchPage";

export const metadata: Metadata = { title: "Search jobs" };

export default function Page() {
  return <LocalOnly><SearchPage /></LocalOnly>;
}
