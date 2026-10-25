"use client";

import { useEffect, useSyncExternalStore } from "react";

import { searchFiltersApi } from "@/lib/api/endpoints";

// One shared list for the whole page: hiding a company in the results updates the search form's box, and back.
let hidden: string[] = [];
let loaded = false;
const listeners = new Set<() => void>();

function set(next: string[]) {
  hidden = next;
  listeners.forEach((listener) => listener());
}
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
const snapshot = () => hidden;
const NONE: string[] = [];

async function hideCompany(company: string) {
  set((await searchFiltersApi.hideCompany(company)).filters.exclude_companies);
}
async function showCompany(company: string) {
  set((await searchFiltersApi.showCompany(company)).filters.exclude_companies);
}

/** Companies left out of every search (and of the results on screen). */
export function useSearchFilters() {
  const hiddenCompanies = useSyncExternalStore(subscribe, snapshot, () => NONE);

  useEffect(() => {
    if (loaded) return;
    loaded = true;
    searchFiltersApi.get().then(({ filters }) => set(filters.exclude_companies), () => {
      loaded = false; // try again next time a part of the page needs it
    });
  }, []);

  return { hiddenCompanies, hideCompany, showCompany };
}
