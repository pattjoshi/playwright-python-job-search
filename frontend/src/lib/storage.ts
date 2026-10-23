/** Browser storage for per-viewer conveniences. Every access is guarded: storage can be blocked. */

const PREFS_KEY = "job-search-ui-v2"; // same key as the old page, so saved settings carry over
const SESSION_KEY = "job-search-session"; // keywords you edited; cleared by "Clear"

export interface SitePref {
  on: boolean;
  results: number | string;
}

export interface Preferences {
  sites?: Record<string, SitePref>;
  hours?: number;
  locations?: string[];
  only_new?: boolean;
  show_browser?: boolean;
  max_pages?: number | string;
  top?: number | string;
  experience?: [number | string, number | string] | null;
}

function read<T>(key: string): T | null {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // private mode or storage disabled: settings just aren't remembered
  }
}

export const loadPreferences = (): Preferences => read<Preferences>(PREFS_KEY) ?? {};
export const savePreferences = (prefs: Preferences) => write(PREFS_KEY, prefs);

export const loadSavedKeywords = (): string[] | null => read<{ keywords?: string[] }>(SESSION_KEY)?.keywords ?? null;
export const saveKeywords = (keywords: string[]) => write(SESSION_KEY, { keywords });
export const clearSavedKeywords = () => write(SESSION_KEY, null);

const TRACKER_VIEW_KEY = "job-search-tracker-view";
export const loadTrackerView = (): "board" | "table" => (read<string>(TRACKER_VIEW_KEY) === "table" ? "table" : "board");
export const saveTrackerView = (view: "board" | "table") => write(TRACKER_VIEW_KEY, view);
