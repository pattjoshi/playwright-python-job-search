import { BellRing, Bot, FileText, Gauge, Layers, Lock, type LucideIcon } from "lucide-react";

const FEATURES: { icon: LucideIcon; title: string; text: string }[] = [
  { icon: FileText, title: "Reads your resume", text: "Keywords, skills, city and experience are filled in for you, no forms to type." },
  { icon: Layers, title: "Three job sites at once", text: "LinkedIn, Naukri and Indeed are searched side by side, only recent posts." },
  { icon: Gauge, title: "AI match score", text: "Every job gets a 0–100 score with matching and missing skills and the reason why." },
  { icon: BellRing, title: "Daily search", text: "Runs every morning by itself, even when the page is closed, and opens the report." },
  { icon: Bot, title: "Only what's new", text: "Remembers jobs you've seen, applied to or hidden, so you never read the same post twice." },
  { icon: Lock, title: "Private by design", text: "Everything stays on your computer behind your own login. Only resume text goes to OpenAI." },
];

export function Features() {
  return (
    <section id="features" className="scroll-mt-20 border-t bg-muted/30">
      <div className="mx-auto max-w-6xl px-4 py-20">
        <h2 className="text-center text-3xl font-bold tracking-tight">Everything a job search needs</h2>
        <p className="mx-auto mt-3 max-w-xl text-center text-muted-foreground">Less scrolling through job boards, more applying to jobs that fit.</p>
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="rounded-xl border bg-card p-6">
              <span className="grid size-10 place-items-center rounded-lg bg-accent text-accent-foreground"><Icon className="size-5" /></span>
              <h3 className="mt-4 font-semibold">{title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
