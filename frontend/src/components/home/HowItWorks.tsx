const STEPS = [
  { title: "Upload your resume", text: "PDF, Word or text. The AI reads it once and remembers it." },
  { title: "Pick what you want", text: "Cities or Remote, years of experience, how recent, and how many jobs from each site." },
  { title: "Get ranked matches", text: "The best jobs first, with a score and the skills that match. Open, apply, track." },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20">
      <h2 className="text-center text-3xl font-bold tracking-tight">How it works</h2>
      <ol className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
        {STEPS.map((step, index) => (
          <li key={step.title} className="relative rounded-xl border bg-card p-6">
            <span className="grid size-9 place-items-center rounded-full bg-primary font-bold text-primary-foreground">{index + 1}</span>
            <h3 className="mt-4 font-semibold">{step.title}</h3>
            <p className="mt-1.5 text-sm text-muted-foreground">{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
