"use client";

import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { AnswerStatus } from "@/lib/types";

import { CATEGORIES, type StatusCounts, STATUS_TABS } from "./meta";

export type AnswerTab = AnswerStatus | "all";

interface AnswersToolbarProps {
  tab: AnswerTab;
  onTab: (tab: AnswerTab) => void;
  counts: StatusCounts;
  query: string;
  onQuery: (query: string) => void;
  category: string;
  onCategory: (category: string) => void;
}

/** Needs answer / Needs review / Answered / All, a search box and a category filter. */
export function AnswersToolbar({ tab, onTab, counts, query, onQuery, category, onCategory }: AnswersToolbarProps) {
  const total = counts.answered + counts.needs_answer + counts.needs_review;
  return (
    <div className="mb-4 grid grid-cols-1 gap-3">
      <Tabs value={tab} onValueChange={(value) => onTab(value as AnswerTab)}>
        <TabsList className="flex-wrap group-data-[orientation=horizontal]/tabs:h-auto">
          {STATUS_TABS.map(({ id, label }) => (
            <TabsTrigger key={id} value={id} className="h-8 flex-none">
              {label}
              <span className="rounded-full bg-background/80 px-1.5 text-xs tabular-nums text-muted-foreground">
                {id === "all" ? total : counts[id]}
              </span>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-0 flex-1 basis-56">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            type="search" value={query} onChange={(e) => onQuery(e.target.value)} placeholder="Search questions and answers"
            aria-label="Search the Answer Bank" className="pl-8"
          />
        </div>
        <Select value={category || "all"} onValueChange={(value) => onCategory(value === "all" ? "" : value)}>
          <SelectTrigger aria-label="Filter by category" className="w-52"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {CATEGORIES.map((c) => <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
