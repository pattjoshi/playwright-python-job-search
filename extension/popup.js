// The popup: connect to the app with its key, Start / Stop, and what's happening.
import { config, DEFAULTS } from "./lib/api.js";

const $ = (id) => document.getElementById(id);
const send = (type) => chrome.runtime.sendMessage({ type });
const NAMES = { naukri: "Naukri", linkedin: "LinkedIn", indeed: "Indeed" };

async function showStatus() {
  const reply = await send("check");
  if (reply.error) {
    $("status").textContent = reply.error;
    $("boards").replaceChildren();
    return false;
  }
  $("status").textContent = `Connected as ${reply.user} · ${reply.waiting} waiting · ${reply.dry_run ? "dry run (nothing is submitted)" : "LIVE: applications are submitted"}`;
  $("boards").replaceChildren(...Object.entries(reply.boards).map(([board, info]) => {
    const item = document.createElement("li");
    item.textContent = info.on ? `${NAMES[board]}: on, ${info.left_today} left today` : `${NAMES[board]}: off (turn it on in the app)`;
    return item;
  }));
  if (!reply.has_resume) $("status").textContent += " · upload your resume in the app first";
  return true;
}

async function showRun() {
  const run = await send("state");
  $("start").disabled = run.running;
  $("stop").disabled = !run.running;
  $("log").textContent = (run.log || []).join("\n");
  $("log").scrollTop = $("log").scrollHeight;
}

$("save").addEventListener("click", async () => {
  const settings = { ...(await config()), server: $("server").value.trim() || DEFAULTS.server, key: $("key").value.trim() };
  await chrome.storage.local.set({ settings });
  await showStatus();
});
$("start").addEventListener("click", async () => { if (await showStatus()) { await send("start"); showRun(); } });
$("stop").addEventListener("click", async () => { await send("stop"); showRun(); });

(async () => {
  const settings = await config();
  $("server").value = settings.server;
  $("key").value = settings.key;
  if (settings.key) await showStatus();
  await showRun();
  setInterval(showRun, 1500);
})();
