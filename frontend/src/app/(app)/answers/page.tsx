import { BookOpenText } from "lucide-react";
import type { Metadata } from "next";

import { ComingSoon } from "@/components/coming-soon/ComingSoon";

export const metadata: Metadata = { title: "Answer Bank" };

export default function AnswersPage() {
  return (
    <ComingSoon
      title="Answer Bank" phase={3} icon={BookOpenText}
      description="Your answers to application questions that a resume doesn't cover."
      features={[
        "One-time form: notice period, CTC, relocation…",
        "Matches questions asked in different words",
        "New questions wait in an inbox until you answer once",
        "Never guesses: no answer, no application",
      ]}
    />
  );
}
