"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";

import { FormField } from "@/components/ui/form-field";
import { TagInput } from "@/components/ui/tag-input";
import { useSearchFilters } from "@/hooks/useSearchFilters";

/** Companies every search leaves out. Same list as "Hide this company" in the results. */
export function ExcludeCompaniesField() {
  const { hiddenCompanies, hideCompany, showCompany } = useSearchFilters();
  const [text, setText] = useState("");
  const input = useRef<HTMLInputElement>(null);

  const run = (action: Promise<void>) => action.catch((err: Error) => toast.error(err.message));
  const commit = () => {
    const names = text.split(",").map((name) => name.trim()).filter(Boolean);
    setText("");
    names.forEach((name) => run(hideCompany(name)));
  };
  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit();
    } else if (e.key === "Backspace" && !text && hiddenCompanies.length) {
      run(showCompany(hiddenCompanies[hiddenCompanies.length - 1]));
    }
  };

  return (
    <FormField label={<label htmlFor="exclude-company-input">Exclude companies</label>} hint="Never show their jobs">
      <TagInput tags={hiddenCompanies} onClick={() => input.current?.focus()} onRemove={(name) => run(showCompany(name))}>
        <input
          ref={input} id="exclude-company-input" placeholder="e.g. TCS, Wipro" autoComplete="off"
          value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKeyDown} onBlur={commit}
        />
      </TagInput>
    </FormField>
  );
}
