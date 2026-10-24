"use client";

import { useCallback, useEffect, useState } from "react";

import { searchFiltersApi } from "@/lib/api/endpoints";

/** Companies you hid: every search leaves them out, and results drop them at once. */
export function useSearchFilters() {
  const [hiddenCompanies, setHidden] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    searchFiltersApi.get().then(({ filters }) => !cancelled && setHidden(filters.exclude_companies), () => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const hideCompany = useCallback(async (company: string) => {
    setHidden((await searchFiltersApi.hideCompany(company)).filters.exclude_companies);
  }, []);
  const showCompany = useCallback(async (company: string) => {
    setHidden((await searchFiltersApi.showCompany(company)).filters.exclude_companies);
  }, []);

  return { hiddenCompanies, hideCompany, showCompany };
}
