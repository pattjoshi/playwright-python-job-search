import { ArrowRight, ShieldCheck } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="mx-auto max-w-6xl px-4 pt-16 pb-12 text-center md:pt-24">
      <Badge variant="secondary" className="mb-5 max-w-full gap-1.5 px-3 py-1 whitespace-normal">
        <ShieldCheck className="size-3.5" /> Free, open source and private: runs on your computer
      </Badge>
      <h1 className="mx-auto max-w-3xl text-4xl font-extrabold tracking-tight md:text-6xl">
        Your AI assistant for finding the <span className="text-primary">right job</span>
      </h1>
      <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
        Upload your resume once. Job Search checks LinkedIn, Naukri and Indeed for fresh openings, and AI ranks every
        job by how well it fits your skills and experience.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Button asChild size="lg"><Link href="/login">Get started <ArrowRight /></Link></Button>
        <Button asChild size="lg" variant="outline"><a href="#how-it-works">See how it works</a></Button>
      </div>
      <div className="relative mx-auto mt-14 max-w-5xl overflow-hidden rounded-xl border bg-card shadow-2xl">
        <Image src="/screenshots/dashboard-light.png" alt="The Job Search dashboard" width={1280} height={800} priority className="block w-full dark:hidden" />
        <Image src="/screenshots/dashboard-dark.png" alt="The Job Search dashboard in dark mode" width={1280} height={800} className="hidden w-full dark:block" />
      </div>
    </section>
  );
}
