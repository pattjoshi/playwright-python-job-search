"use client";

import { useCallback, useState } from "react";

import { MAX_KEYWORDS, MAX_LOCATIONS } from "@/lib/constants";
import { uniqueTrimmed } from "@/lib/format";
import { loadPreferences, loadSavedKeywords, saveKeywords, savePreferences, type SitePref } from "@/lib/storage";
import type { AppConfig, Resume, SearchRequest } from "@/lib/types";

export interface Experience {
  any: boolean;
  min: string;
  max: string;
}

export interface SearchForm {
  keywords: string[];
  locations: string[];
  experience: Experience;
  hours: number;
  sites: Record<string, SitePref>;
  onlyNew: boolean;
  showBrowser: boolean;
  maxPages: string;
  top: string;
}

function initialForm(config: AppConfig): SearchForm {
  const prefs = loadPreferences();
  const defaults = config.defaults;
  const sites: Record<string, SitePref> = {};
  for (const site of config.sites) {
    const saved = prefs.sites?.[site.id];
    sites[site.id] = { on: saved?.on ?? config.enabled_sites.includes(site.id), results: saved?.results ?? site.results };
  }
  const experience = prefs.experience !== undefined ? prefs.experience : defaults.experience ?? [1, 3];
  return {
    keywords: uniqueTrimmed(loadSavedKeywords() ?? defaults.keywords ?? [], MAX_KEYWORDS),
    locations: uniqueTrimmed(prefs.locations ?? defaults.locations ?? [], MAX_LOCATIONS),
    experience: experience
      ? { any: false, min: String(experience[0]), max: String(experience[1]) }
      : { any: true, min: "1", max: "3" },
    hours: Number(prefs.hours || defaults.hours),
    sites,
    onlyNew: prefs.only_new ?? defaults.only_new,
    showBrowser: prefs.show_browser ?? true,
    maxPages: String(prefs.max_pages || defaults.max_pages),
    top: String(prefs.top || defaults.top),
  };
}

const toInt = (value: string | number) => parseInt(String(value), 10);

/** Turns the form into the API request. Throws an Error with a friendly message when something is off. */
export function buildRequest(form: SearchForm, resumeId: string | undefined): SearchRequest {
  const sites: Record<string, number> = {};
  for (const [id, site] of Object.entries(form.sites)) if (site.on) sites[id] = toInt(site.results);
  if (!Object.keys(sites).length) throw new Error("Pick at least one job site.");
  if (Object.values(sites).some((n) => !(n >= 1 && n <= 100))) throw new Error("Jobs to show must be between 1 and 100.");

  let experience: [number, number] | null = null;
  if (!form.experience.any) {
    const low = toInt(form.experience.min);
    const high = toInt(form.experience.max);
    if (!(low >= 0 && high >= 0 && low <= 50 && high <= 50)) throw new Error("Experience must be between 0 and 50 years.");
    if (low > high) throw new Error("Experience 'from' can't be more than 'to'.");
    experience = [low, high];
  }
  return {
    resume_id: resumeId, sites, keywords: form.keywords, locations: form.locations, experience,
    hours: form.hours, only_new: form.onlyNew, show_browser: form.showBrowser,
    max_pages: toInt(form.maxPages), top: toInt(form.top),
  };
}

export function chosenSites(form: SearchForm): string[] {
  return Object.entries(form.sites).filter(([, site]) => site.on).map(([id]) => id);
}

/** The settings in the left column: loaded from your last visit, remembered when you search. */
export function useSearchForm(config: AppConfig) {
  const [form, setForm] = useState<SearchForm>(() => initialForm(config));

  const update = useCallback((patch: Partial<SearchForm>) => setForm((current) => ({ ...current, ...patch })), []);

  const setKeywords = useCallback((keywords: string[]) => {
    const clean = uniqueTrimmed(keywords, MAX_KEYWORDS);
    saveKeywords(clean);
    setForm((current) => ({ ...current, keywords: clean }));
  }, []);

  const setLocations = useCallback(
    (locations: string[]) => setForm((current) => ({ ...current, locations: uniqueTrimmed(locations, MAX_LOCATIONS) })),
    [],
  );

  /** After a resume is read: use its keywords, its cities (if none picked) and a suggested experience range. */
  const fillFromResume = useCallback((resume: Resume) => {
    const keywords = uniqueTrimmed(resume.profile.keywords, MAX_KEYWORDS);
    saveKeywords(keywords);
    const keepExperience = Boolean(loadPreferences().experience);
    setForm((current) => ({
      ...current,
      keywords,
      locations: current.locations.length ? current.locations : uniqueTrimmed(resume.profile.locations, MAX_LOCATIONS),
      experience:
        !keepExperience && resume.suggested_experience
          ? { any: false, min: String(resume.suggested_experience[0]), max: String(resume.suggested_experience[1]) }
          : current.experience,
    }));
  }, []);

  const rememberSettings = useCallback(() => {
    savePreferences({
      sites: form.sites, hours: form.hours, locations: form.locations, only_new: form.onlyNew,
      show_browser: form.showBrowser, max_pages: form.maxPages, top: form.top,
      experience: form.experience.any ? null : [form.experience.min, form.experience.max],
    });
  }, [form]);

  return { form, update, setKeywords, setLocations, fillFromResume, rememberSettings };
}

export type SearchFormApi = ReturnType<typeof useSearchForm>;
