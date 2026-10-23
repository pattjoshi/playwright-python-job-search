// Shapes of the JSON the backend API returns (see backend/src/job_search/api and schemas).

export type SiteId = string;
export type JobStatus = "seen" | "applied" | "hidden";
export type SearchStatus = "running" | "stopping" | "done" | "stopped" | "error";
export type Stage = "resume" | "search" | "details" | "score" | "report";
export type FunnelStep = [label: string, count: number];

export interface HistoryCounts {
  seen: number;
  applied: number;
  hidden: number;
}

export interface SiteConfig {
  id: SiteId;
  name: string;
  results: number;
}

export interface AppConfig {
  sites: SiteConfig[];
  enabled_sites: SiteId[];
  location_choices: string[];
  defaults: {
    locations: string[];
    keywords: string[];
    hours: number;
    experience: [number, number] | null;
    only_new: boolean;
    max_pages: number;
    top: number;
    parallel_sites: boolean;
  };
  has_api_key: boolean;
  running_job: string | null;
  resume_types: string[];
  history: HistoryCounts;
  version?: string;
}

export interface ProfileSummary {
  summary: string;
  current_title: string;
  skills: string[];
  years_experience: number | null;
  keywords: string[];
  locations: string[];
}

export interface Resume {
  resume_id: string;
  file_name: string;
  profile: ProfileSummary;
  suggested_experience: [number, number] | null;
}

export interface Job {
  source: SiteId;
  job_id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  posted_text: string;
  experience: string;
  is_new: boolean;
  score: number | null;
  match_reason: string;
  matched_skills: string[];
  missing_skills: string[];
  status?: JobStatus | null; // only on a search restored from the saved session
}

export interface RunStats {
  duration_s: number;
  ai_calls: number;
  tokens: number;
  cached_tokens: number;
  cost_usd: number | null;
  scores_reused: number;
  descriptions_reused: number;
}

export interface SearchResult {
  sites: { id: SiteId; name: string; jobs: Job[] }[];
  scored: number;
  stats?: RunStats;
  html_report: string;
  excel_report: string;
}

export interface SiteProgress {
  status: "waiting" | "running" | "done" | "failed" | string;
  found: number;
}

export interface SearchJob {
  id: string;
  status: SearchStatus;
  stage: Stage;
  started_at: string;
  finished_at: string | null;
  logs: string[];
  sites: Record<SiteId, SiteProgress>;
  progress: { stage: Stage; done: number; total: number } | null;
  funnel: FunnelStep[] | null;
  requested: Record<SiteId, number>;
  profile: ProfileSummary | null;
  error: string | null;
  result: SearchResult | null;
}

export interface SessionState {
  resume: Resume | null;
  last_job: SearchJob | null;
}

export interface SavedJob {
  source: SiteId;
  job_id: string;
  title: string;
  company: string;
  url: string;
  status: JobStatus;
  first_seen: string;
  updated_at: string;
}

export interface Run {
  id: number;
  started_at: string;
  origin: "web" | "daily" | "cli" | string;
  status: "done" | "stopped" | "error" | string;
  duration_s?: number;
  sites?: Record<SiteId, SiteProgress>;
  shown?: number;
  new?: number;
  usage?: { input_tokens?: number; output_tokens?: number };
  cost_usd?: number | null;
  scores_reused?: number;
  funnel?: FunnelStep[];
  error?: string | null;
  report_url: string | null;
}

export interface ScheduleSummary {
  time: string;
  days: string[];
  open_report: boolean;
  next_run: string;
  sites: Record<SiteId, number>;
}

export interface DailyStatus {
  supported: boolean;
  kind: "windows" | "cron" | "unsupported" | string;
  schedule: ScheduleSummary | null;
  last_run: {
    last_run: string;
    status: "done" | "error" | string;
    jobs?: number;
    new?: number;
    error?: string;
    report_url?: string;
  } | null;
}

/** The search settings sent to POST /api/search and /api/schedule. */
export interface SearchRequest {
  resume_id: string | undefined;
  sites: Record<SiteId, number>;
  keywords: string[];
  locations: string[];
  experience: [number, number] | null;
  hours: number;
  only_new: boolean;
  show_browser: boolean;
  max_pages: number;
  top: number;
}

export interface AuthUser {
  id: number;
  email: string;
  name: string;
  role: "owner" | "member" | string;
  created_at: string;
}

export interface AuthStatus {
  setup_required: boolean;
  user: AuthUser | null;
}

export type ApplicationStatus = "saved" | "applied" | "screening" | "interview" | "offer" | "rejected" | "withdrawn";

export interface Application {
  id: number;
  company: string;
  title: string;
  url: string;
  source: string;
  source_job_id: string | null;
  location: string;
  salary: string;
  status: ApplicationStatus;
  applied_on: string | null;
  follow_up_on: string | null;
  contact: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export type ApplicationInput = Partial<Omit<Application, "id" | "created_at" | "updated_at">>;

export interface ApplicationEvent {
  kind: "created" | "status";
  from_status: ApplicationStatus | null;
  to_status: ApplicationStatus | null;
  at: string;
}

export interface ApplicationStats {
  by_status: Partial<Record<ApplicationStatus, number>>;
  total: number;
  per_day: { date: string; count: number }[];
  follow_ups: Application[];
}

export * from "./answer-types";
