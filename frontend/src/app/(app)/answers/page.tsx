import type { Metadata } from "next";

import { AnswerBankPage } from "@/components/answers/AnswerBankPage";

export const metadata: Metadata = { title: "Answer Bank" };

export default function Page() {
  return <AnswerBankPage />;
}
