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
