import { ChevronDown } from "lucide-react";

const QUESTIONS = [
  { q: "Is it free?", a: "Yes, the app is free and open source. You only pay OpenAI for the AI it uses, usually a few paise per search." },
  { q: "Where is my data?", a: "In the project folder on your computer, behind your own login. Resume text and job descriptions are sent to OpenAI to read and score them; nothing else leaves your computer." },
  { q: "Which job sites does it search?", a: "LinkedIn, Naukri and Indeed, with Indian tech cities and Remote built in." },
  { q: "Do I need an OpenAI key?", a: "Yes. Create one at platform.openai.com, put it in the .env file, and restart the app." },
  { q: "Is it allowed by the job sites?", a: "It searches politely and slowly, for personal use. Job sites restrict automated access, so keep it low-volume." },
];

export function Faq() {
  return (
    <section id="faq" className="mx-auto max-w-3xl scroll-mt-20 px-4 py-20">
      <h2 className="text-center text-3xl font-bold tracking-tight">Questions</h2>
      <div className="mt-10 divide-y rounded-xl border bg-card">
        {QUESTIONS.map(({ q, a }) => (
          <details key={q} className="group px-5 py-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium [&::-webkit-details-marker]:hidden">
              {q}
              <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" aria-hidden="true" />
            </summary>
            <p className="mt-2 text-sm text-muted-foreground">{a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
