import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

import { ComingSoonStrip } from "./ComingSoonStrip";
import { Faq } from "./Faq";
import { Features } from "./Features";
import { Hero } from "./Hero";
import { HomeHeader } from "./HomeHeader";
import { HowItWorks } from "./HowItWorks";

/** The public home page: what the app does, and a way in. */
export function HomePage() {
  return (
    <div className="min-h-svh bg-background">
      <HomeHeader />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <ComingSoonStrip />
        <Faq />
        <section className="mx-auto max-w-6xl px-4 pb-20">
          <div className="rounded-2xl bg-primary px-6 py-12 text-center text-primary-foreground">
            <h2 className="text-3xl font-bold tracking-tight">Ready to find your next job?</h2>
            <p className="mx-auto mt-3 max-w-lg opacity-90">Set up takes a minute. Your first ranked list takes about five.</p>
            <Button asChild size="lg" variant="secondary" className="mt-6"><Link href="/login">Get started <ArrowRight /></Link></Button>
          </div>
        </section>
      </main>
      <footer className="border-t">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-6 text-sm text-muted-foreground">
          <span>Job Search · runs on your computer</span>
          <a href="https://github.com/pattjoshi/playwright-python-job-search" className="hover:text-foreground">Source code on GitHub</a>
        </div>
      </footer>
    </div>
  );
}
