// Runs the auto-apply queue in your own Chrome: next job → open it in a tab → apply → screenshot → report.
import { call, config } from "./lib/api.js";

const FILES = ["content/fields.js", "content/fill.js", "content/boards.js", "content/naukri-chat.js"];
const GAP_S = [30, 50]; // seconds between two applications, like a person (Chrome alarms can't go below 30 s)
const submitting = {}; // job id → answers, once Submit was pressed (the page may navigate away)

async function state() {
  const { run } = await chrome.storage.local.get("run");
  return { running: false, tabId: null, log: [], ...(run || {}) };
}
async function save(patch) {
  const next = { ...(await state()), ...patch };
  await chrome.storage.local.set({ run: next });
  return next;
}
async function say(text) {
  const line = `${new Date().toLocaleTimeString()}  ${text}`;
  await save({ log: [...(await state()).log, line].slice(-80) });
}

chrome.runtime.onMessage.addListener((message, _sender, reply) => {
  handle(message).then(reply, (error) => reply({ error: error.message }));
  return true; // answer asynchronously
});
chrome.alarms.onAlarm.addListener((alarm) => alarm.name === "next" && tick());

async function handle(message) {
  switch (message.type) {
    case "start":
      await save({ running: true, log: [] });
      await say("Started.");
      tick();
      return state();
    case "stop":
      await chrome.alarms.clear("next");
      await save({ running: false });
      await say("Stopped.");
      return state();
    case "state": return state();
    case "check": return call("/status");
    case "answer":
      return call(`/jobs/${message.jobId}/answer`, { method: "POST",
        body: { question: message.question, options: message.options || [], required: message.required !== false } });
    case "write": return call(`/jobs/${message.jobId}/write`, { method: "POST", body: { question: message.question } });
    case "resume": return call("/resume");
    case "submitting":
      submitting[message.jobId] = message.answers || [];
      return { ok: true };
    default: return { error: "Unknown message" };
  }
}

let busy = false;
async function tick() {
  if (busy || !(await state()).running) return;
  busy = true;
  let gap = null;
  try {
    const { pace } = await config();
    const { job } = await call("/next", { method: "POST" });
    if (!job) {
      await say("Nothing waiting: the queue is empty, or today's limits are reached.");
      await save({ running: false });
      return;
    }
    await say(`Applying: ${job.title} at ${job.company}${job.dry_run ? " (dry run)" : ""}`);
    const outcome = await applyTo(job, pace);
    await say(`${job.company}: ${outcome.message}`);
    gap = pace ? (GAP_S[0] + Math.random() * (GAP_S[1] - GAP_S[0])) * pace : 0;
  } catch (error) {
    await say(`Stopped: ${error.message}`);
    await save({ running: false });
  } finally {
    busy = false;
  }
  if (gap === null || !(await state()).running) return;
  if (gap >= 30) chrome.alarms.create("next", { when: Date.now() + gap * 1000 });
  else setTimeout(tick, gap * 1000 + 300);
}

/** Wait for the tab to finish loading after `start()` (which navigates it). */
function navigate(tabId, start, timeout = 45000) {
  return new Promise((resolve) => {
    const done = () => { chrome.tabs.onUpdated.removeListener(listen); clearTimeout(timer); resolve(); };
    // A new tab's about:blank also "completes": only the real page counts.
    const listen = (id, info, tab) => id === tabId && info.status === "complete" && !/^about:/.test(tab.url || "") && done();
    chrome.tabs.onUpdated.addListener(listen);
    const timer = setTimeout(done, timeout);
    start();
  });
}

async function openTab(url) {
  const { tabId } = await state();
  const existing = tabId ? await chrome.tabs.get(tabId).catch(() => null) : null;
  if (existing) {
    await navigate(existing.id, () => chrome.tabs.update(existing.id, { url, active: true }));
    return existing.id;
  }
  const tab = await chrome.tabs.create({ url: "about:blank", active: true });
  await save({ tabId: tab.id });
  await navigate(tab.id, () => chrome.tabs.update(tab.id, { url }));
  return tab.id;
}

async function inject(tabId, job, pace, entry = "run") {
  await chrome.scripting.executeScript({ target: { tabId }, files: FILES });
  const [frame] = await chrome.scripting.executeScript({
    target: { tabId }, args: [job, pace, entry],
    func: (job, pace, entry) => {
      if (entry === "indeedSteps") { window.JSA.pace = pace; window.JSA.memo = {}; return window.JSA.boards.indeedSteps(job); }
      return window.JSA.run(job, pace);
    },
  });
  return frame.result;
}

async function applyTo(job, pace) {
  delete submitting[job.id];
  let tabId = await openTab(job.url);
  let outcome;
  try {
    const opened = new Promise((resolve) => {
      const listen = (tab) => tab.openerTabId === tabId && (chrome.tabs.onCreated.removeListener(listen), resolve(tab.id));
      chrome.tabs.onCreated.addListener(listen);
      setTimeout(() => (chrome.tabs.onCreated.removeListener(listen), resolve(null)), 12000);
    });
    outcome = await inject(tabId, job, pace);
    if (outcome?.newTab) { // Indeed opens its application in a new tab (or the same one)
      const newTab = await opened;
      if (newTab) { await navigate(newTab, () => {}, 20000); tabId = newTab; } else await new Promise((r) => setTimeout(r, 3000));
      outcome = await inject(tabId, job, pace, "indeedSteps");
    }
  } catch (error) {
    outcome = submitting[job.id]
      ? { status: "unconfirmed", message: "Submitted; the page moved on before a confirmation could be read. Check your email.", answers: submitting[job.id] }
      : { status: "failed", message: `The page changed while applying: ${String(error.message).slice(0, 150)}` };
  }
  outcome = outcome || { status: "failed", message: "The page didn't answer." };
  await report(job, outcome, tabId);
  const { tabId: mainTab } = await state();
  if (tabId !== mainTab) await chrome.tabs.remove(tabId).catch(() => {});
  return outcome;
}

async function report(job, outcome, tabId) {
  const tab = await chrome.tabs.get(tabId).catch(() => null);
  const screenshot = tab ? await chrome.tabs.captureVisibleTab(tab.windowId, { format: "png" }).catch(() => "") : "";
  let page = "";
  if (tab && !["filled", "submitted"].includes(outcome.status)) {
    const [frame] = await chrome.scripting.executeScript({ target: { tabId }, func: () => document.documentElement.outerHTML.slice(0, 2_000_000) })
      .catch(() => [{}]);
    page = frame?.result || "";
  }
  const status = outcome.status === "continue" ? "failed" : outcome.status;
  await call(`/jobs/${job.id}/result`, { method: "POST", body: {
    status, message: outcome.message, answers: outcome.answers || [], screenshot, page, signed_in: Boolean(outcome.signedIn),
  } });
}
