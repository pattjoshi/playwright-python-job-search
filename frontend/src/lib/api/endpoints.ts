/** One typed function per backend endpoint. */

import { postJson, request } from "@/lib/api/client";
import type {
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
