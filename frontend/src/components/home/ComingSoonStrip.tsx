import { NAV_ITEMS } from "@/components/layout/nav";
import { Badge } from "@/components/ui/badge";

/** The roadmap: features arriving next. */
export function ComingSoonStrip() {
  const soon = NAV_ITEMS.filter((item) => item.soon);
  return (
    <section className="border-t bg-muted/30">
      <div className="mx-auto max-w-6xl px-4 py-20">
        <h2 className="text-center text-3xl font-bold tracking-tight">Coming next</h2>
        <p className="mx-auto mt-3 max-w-xl text-center text-muted-foreground">Built in the open, one phase at a time.</p>
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {soon.map(({ href, label, description, icon: Icon }) => (
            <div key={href} className="rounded-xl border bg-card p-5">
              <div className="flex items-center justify-between">
                <Icon className="size-5 text-primary" aria-hidden="true" />
                <Badge variant="secondary">Soon</Badge>
              </div>
              <h3 className="mt-3 font-semibold">{label}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
