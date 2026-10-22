import { FileText, ScanSearch, Trophy } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

const STEPS = [
  { icon: FileText, title: "1 · Resume", text: "Keywords, skills and experience are read automatically." },
  { icon: ScanSearch, title: "2 · Search", text: "LinkedIn, Naukri and Indeed, filtered to recent posts." },
  { icon: Trophy, title: "3 · Rank", text: "Every job gets a match score with matching and missing skills." },
];

export function EmptyState() {
  return (
    <Card>
      <CardContent className="px-7 py-10 text-center">
        <h2 className="text-xl font-bold">Your matches will appear here</h2>
        <p className="mx-auto mt-1.5 max-w-md text-sm text-muted-foreground">
          Upload your resume and press Start. Jobs are ranked by how well they fit your skills and experience.
        </p>
        <div className="mt-7 grid grid-cols-1 gap-3 text-left sm:grid-cols-3">
          {STEPS.map(({ icon: Icon, title, text }) => (
            <div key={title} className="rounded-lg border bg-muted/40 p-3.5">
              <Icon className="mb-2 size-4 text-primary" aria-hidden="true" />
              <b className="block text-sm">{title}</b>
              <span className="text-sm text-muted-foreground">{text}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
