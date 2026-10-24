// Talks to the local Job Search app (http://127.0.0.1:8000 by default) with the key from the Auto-apply page.

export const DEFAULTS = { server: "http://127.0.0.1:8000", key: "", pace: 1 };

export async function config() {
  const { settings } = await chrome.storage.local.get("settings");
  return { ...DEFAULTS, ...(settings || {}) };
}

export async function call(path, { method = "GET", body } = {}) {
  const { server, key } = await config();
  if (!key) throw new Error("Not connected: paste the key from the app's Auto-apply page.");
  const response = await fetch(`${server.replace(/\/$/, "")}/api/extension${path}`, {
    method,
    headers: { Authorization: `Bearer ${key}`, ...(body ? { "Content-Type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (path === "/resume") {
    if (!response.ok) return null;
    const blob = await response.blob();
    const name = (response.headers.get("content-disposition") || "").match(/filename\*?=(?:UTF-8'')?"?([^";]+)/)?.[1] || "resume.pdf";
    return { name: decodeURIComponent(name), type: blob.type, base64: await toBase64(blob) };
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `The app answered ${response.status}`);
  return data;
}

async function toBase64(blob) {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let text = "";
  for (let i = 0; i < bytes.length; i += 0x8000) text += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(text);
}
