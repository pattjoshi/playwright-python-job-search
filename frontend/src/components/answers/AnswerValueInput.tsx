"use client";

import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { AnswerKind } from "@/lib/types";

interface AnswerValueInputProps {
  id: string;
  label: string;
  kind: AnswerKind;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}

/** The answer box, shaped like the form field: Yes/No buttons, a list of options, a number or text. */
export function AnswerValueInput({ id, label, kind, options, value, onChange }: AnswerValueInputProps) {
  if (kind === "yes_no") {
    return (
      <ToggleGroup type="single" variant="outline" value={value} onValueChange={onChange} aria-label={label} className="w-fit">
        <ToggleGroupItem value="Yes" className="px-5">Yes</ToggleGroupItem>
        <ToggleGroupItem value="No" className="px-5">No</ToggleGroupItem>
      </ToggleGroup>
    );
  }
  if (kind === "choice" && options.length) {
    return (
      <Select value={value || undefined} onValueChange={onChange}>
        <SelectTrigger id={id} aria-label={label} className="w-full sm:w-72"><SelectValue placeholder="Pick an option" /></SelectTrigger>
        <SelectContent>{options.map((option) => <SelectItem key={option} value={option}>{option}</SelectItem>)}</SelectContent>
      </Select>
    );
  }
  if (kind === "number") {
    return (
      <Input
        id={id} aria-label={label} inputMode="decimal" value={value} onChange={(e) => onChange(e.target.value)}
        placeholder="e.g. 3" className="w-full sm:w-48"
      />
    );
  }
  return (
    <Textarea
      id={id} aria-label={label} rows={2} value={value} onChange={(e) => onChange(e.target.value)}
      placeholder="Your answer" className="min-h-0"
    />
  );
}
