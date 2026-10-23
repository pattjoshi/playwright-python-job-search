import { NotebookPen } from "lucide-react";
import type { Metadata } from "next";

import { ComingSoon } from "@/components/coming-soon/ComingSoon";

export const metadata: Metadata = { title: "Notes" };

export default function NotesPage() {
  return (
    <ComingSoon
      title="Notes" phase={6} icon={NotebookPen}
      description="Notion-style notes for interview prep and company research."
      features={[
        "Pages and sub-pages with a slash (/) menu",
        "Checklists, headings, tables, code and images",
        "Templates for interview prep and research",
        "Link a note to an application",
      ]}
    />
  );
}
