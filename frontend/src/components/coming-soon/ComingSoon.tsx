import { CheckCircle2, type LucideIcon } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface ComingSoonProps {
  title: string;
  description: string;
  phase: number;
  icon: LucideIcon;
  features: string[];
}

/** Placeholder for a page that arrives in a later phase: what it will do and when. */
export function ComingSoon({ title, description, phase, icon: Icon, features }: ComingSoonProps) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <Card>
        <CardContent className="flex flex-col items-center px-6 py-10 text-center">
          <span className="mb-4 grid grid-cols-1 size-14 place-items-center rounded-2xl bg-accent text-accent-foreground">
            <Icon className="size-7" aria-hidden="true" />
          </span>
          <Badge variant="secondary">Coming in Phase {phase}</Badge>
          <h3 className="mt-3 text-lg font-semibold">This page is on the way</h3>
          <p className="mt-1 max-w-md text-sm text-muted-foreground">Here is what it will do:</p>
          <ul className="mt-5 grid grid-cols-1 w-full max-w-xl gap-2 text-left text-sm sm:grid-cols-2">
            {features.map((feature) => (
              <li key={feature} className="flex items-start gap-2 rounded-lg border bg-muted/40 p-3">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                {feature}
              </li>
            ))}
          </ul>
          <Button asChild variant="outline" className="mt-6">
            <Link href="/search">Search jobs meanwhile</Link>
          </Button>
        </CardContent>
      </Card>
    </>
  );
}
