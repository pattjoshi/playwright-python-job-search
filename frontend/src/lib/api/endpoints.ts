/** One typed function per backend endpoint. */

import { postJson, request } from "@/lib/api/client";
import type {
  Answer,
  AutoApplyJob,
  AutoApplyOverview,
  AutoApplyRun,
  AutoApplySettings,
  AnswerInput,
  Application,
  ApplicationEvent,
  ApplicationInput,
  ApplicationStats,
  AppConfig,
  AuthStatus,
  AuthUser,
  DailyStatus,
  HistoryCounts,
  JobStatus,
  Resume,
  Run,
  SavedJob,
  SearchJob,
  SearchRequest,
  SessionState,
  TryResult,
} from "@/lib/types";

export const authApi = {
  status: () => request<AuthStatus>("/api/auth/status"),
  setup: (body: { name: string; email: string; password: string }) => postJson<{ user: AuthUser }>("/api/auth/setup", body),
  login: (body: { email: string; password: string }) => postJson<{ user: AuthUser }>("/api/auth/login", body),
  logout: () => postJson<{ ok: boolean }>("/api/auth/logout"),
  logoutEverywhere: () => postJson<{ ok: boolean }>("/api/auth/logout-everywhere"),
  changePassword: (current: string, next: string) => postJson<{ ok: boolean }>("/api/auth/password", { current, new: next }),
};

export const applicationsApi = {
  list: (q = "", status = "") =>
    request<{ applications: Application[] }>(`/api/applications?${new URLSearchParams({ q, status })}`),
  get: (id: number) => request<{ application: Application; events: ApplicationEvent[] }>(`/api/applications/${id}`),
  create: (body: ApplicationInput) => postJson<{ application: Application }>("/api/applications", body),
  update: (id: number, body: ApplicationInput) =>
    request<{ application: Application }>(`/api/applications/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }),
  remove: (id: number) => request<{ ok: boolean }>(`/api/applications/${id}`, { method: "DELETE" }),
  stats: () => request<ApplicationStats>("/api/applications/stats"),
  track: (job: { source: string; job_id: string; title: string; company: string; url: string; location: string }) =>
    postJson<{ application: Application; created: boolean }>("/api/applications/track", job),
  importApplied: () => postJson<{ added: number }>("/api/applications/import-applied"),
};

export const answersApi = {
  list: () => request<{ answers: Answer[] }>("/api/answers"),
  create: (body: AnswerInput) => postJson<{ answer: Answer }>("/api/answers", body),
  update: (id: number, body: AnswerInput) =>
    request<{ answer: Answer }>(`/api/answers/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }),
  approve: (id: number) => postJson<{ answer: Answer }>(`/api/answers/${id}/approve`),
  remove: (id: number) => request<{ ok: boolean }>(`/api/answers/${id}`, { method: "DELETE" }),
  addStarters: () => postJson<{ added: number }>("/api/answers/starters"),
  fillFromResume: () => postJson<{ filled: number }>("/api/answers/fill-from-resume"),
  tryQuestion: (question: string, options: string[]) => postJson<TryResult>("/api/answers/try", { question, options }),
};

export const autoApplyApi = {
  overview: () => request<AutoApplyOverview>("/api/auto-apply"),
  saveSettings: (body: Partial<AutoApplySettings>) =>
    request<{ settings: AutoApplySettings }>("/api/auto-apply/settings", {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }),
  queueLastSearch: () => postJson<{ added: number }>("/api/auto-apply/queue-last-search"),
  run: () => postJson<{ run: AutoApplyRun }>("/api/auto-apply/run"),
  stop: () => postJson<{ run: AutoApplyRun }>("/api/auto-apply/stop"),
  retry: (id: number) => postJson<{ job: AutoApplyJob }>(`/api/auto-apply/${id}/retry`),
  remove: (id: number) => request<{ ok: boolean }>(`/api/auto-apply/${id}`, { method: "DELETE" }),
  screenshotUrl: (id: number, version: string) => `/api/auto-apply/${id}/screenshot?v=${encodeURIComponent(version)}`,
};

export const api = {
  config: () => request<AppConfig>("/api/config"),

  analyzeResume(file: File) {
    const form = new FormData();
    form.append("resume", file);
    return request<Resume>("/api/analyze", { method: "POST", body: form });
  },

  startSearch: (search: SearchRequest) => postJson<{ id: string }>("/api/search", search),
  searchStatus: (id: string) => request<SearchJob>(`/api/search/${id}`),
  stopSearch: (id: string) => postJson<{ ok: boolean }>(`/api/search/${id}/stop`),

  setJobStatus: (job: { source: string; job_id: string; title?: string; company?: string; url?: string; location?: string }, status: JobStatus) =>
    postJson<{ ok: boolean; history: HistoryCounts; tracked?: boolean }>("/api/jobs/status", { ...job, status }),
  savedJobs: (status: "applied" | "hidden") =>
    request<{ jobs: SavedJob[]; history: HistoryCounts }>(`/api/history?status=${status}`),
  forgetSeen: () => postJson<{ forgotten: number; history: HistoryCounts }>("/api/history/forget"),
  runs: () => request<{ runs: Run[]; costs_configured: boolean }>("/api/runs"),

  daily: () => request<DailyStatus>("/api/schedule"),
  saveDaily: (body: SearchRequest & { time: string; days: string[]; open_report: boolean }) =>
    postJson<DailyStatus>("/api/schedule", body),
  turnOffDaily: () => request<DailyStatus>("/api/schedule", { method: "DELETE" }),

  session: () => request<SessionState>("/api/session"),
  clearSession: () => postJson<SessionState>("/api/session/clear"),
};
