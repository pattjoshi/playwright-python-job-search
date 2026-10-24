"use client";

import { EyeOff, Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { isFiltered, NO_FILTER, type ResultFilter, type ResultSort } from "@/lib/results-filter";

const SCORES = [["0", "Any score"], ["60", "60+"], ["70", "70+"], ["80", "80+"]];
const HOURS = [["any", "Any time"], ["1", "Last hour"], ["6", "Last 6 hours"], ["12", "Last 12 hours"], ["24", "Last 24 hours"]];
const SORTS: [ResultSort, string][] = [["score", "Best match"], ["newest", "Newest"], ["company", "Company A–Z"]];

interface ResultsFiltersProps {
  filter: ResultFilter;
  onChange: (filter: ResultFilter) => void;
  leftOut: number;
  hiddenCompanies: string[];
  onShowCompany: (company: string) => void;
}

/** Narrow and sort the results without searching again; companies you hid are listed here too. */
export function ResultsFilters({ filter, onChange, leftOut, hiddenCompanies, onShowCompany }: ResultsFiltersProps) {
  const set = (patch: Partial<ResultFilter>) => onChange({ ...filter, ...patch });
  return (
    <div className="grid grid-cols-1 gap-2 border-b px-5 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-48 flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={filter.query} onChange={(e) => set({ query: e.target.value })} className="h-8 pl-8"
            placeholder="Filter by title, company or location" aria-label="Filter results"
          />
        </div>
        <Select value={String(filter.minScore)} onValueChange={(v) => set({ minScore: Number(v) })}>
          <SelectTrigger size="sm" aria-label="Minimum score" className="w-32"><SelectValue /></SelectTrigger>
          <SelectContent>{SCORES.map(([v, label]) => <SelectItem key={v} value={v}>{label}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={filter.maxHours === null ? "any" : String(filter.maxHours)} onValueChange={(v) => set({ maxHours: v === "any" ? null : Number(v) })}>
          <SelectTrigger size="sm" aria-label="Posted within" className="w-36"><SelectValue /></SelectTrigger>
          <SelectContent>{HOURS.map(([v, label]) => <SelectItem key={v} value={v}>{label}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={filter.sort} onValueChange={(v) => set({ sort: v as ResultSort })}>
          <SelectTrigger size="sm" aria-label="Sort by" className="w-36"><SelectValue /></SelectTrigger>
          <SelectContent>{SORTS.map(([v, label]) => <SelectItem key={v} value={v}>{label}</SelectItem>)}</SelectContent>
        </Select>
        {hiddenCompanies.length ? <HiddenCompanies companies={hiddenCompanies} onShow={onShowCompany} /> : null}
      </div>
      {leftOut > 0 || isFiltered(filter) ? (
        <p className="text-xs text-muted-foreground" role="status">
          {leftOut} left out by filters
          {isFiltered(filter) ? (
            <Button variant="link" size="xs" className="ml-1 h-auto p-0" onClick={() => onChange({ ...NO_FILTER, sort: filter.sort })}>Clear</Button>
          ) : null}
        </p>
      ) : null}
    </div>
  );
}

function HiddenCompanies({ companies, onShow }: { companies: string[]; onShow: (company: string) => void }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm"><EyeOff /> Hidden companies ({companies.length})</Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72">
        <p className="mb-2 text-xs text-muted-foreground">Left out of results and of every future search.</p>
        <ul className="grid max-h-64 grid-cols-1 gap-1 overflow-y-auto">
          {companies.map((company) => (
            <li key={company} className="flex items-center gap-2 text-sm">
              <span className="min-w-0 flex-1 truncate">{company}</span>
              <Button variant="ghost" size="icon-sm" aria-label={`Show ${company} again`} onClick={() => onShow(company)}><X /></Button>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  );
}
