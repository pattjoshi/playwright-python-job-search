/** Small fetch wrapper: JSON in, JSON out, and the backend's {"error": "..."} turned into an Error. */

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, init);
  let body: unknown = {};
  try {
    body = await response.json();
  } catch {
    // empty or non-JSON body
  }
  if (response.status === 401 && !path.startsWith("/api/auth/")) redirectToSignIn();
  if (!response.ok) {
    const message = (body as { error?: string }).error ?? `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }
  return body as T;
}

export function postJson<T>(path: string, data?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
}

/** The session ended (signed out elsewhere, or expired): go to the sign-in page and come back after. */
export function redirectToSignIn(): void {
  if (typeof window === "undefined" || window.location.pathname.startsWith("/login")) return;
  const next = window.location.pathname + window.location.search;
  window.location.replace(`/login?next=${encodeURIComponent(next)}`);
}
