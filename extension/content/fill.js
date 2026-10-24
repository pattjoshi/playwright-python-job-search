// What goes in each field (same rules as the app): resume upload, AI cover letter, names, else the Answer Bank.
(() => {
  const JSA = (window.JSA = window.JSA || {});
  const TEXT = new Set(["text", "email", "tel", "url", "number", "date", "textarea"]);
  const RESUME = /\b(resume|résumé|cv|curriculum)\b/i;
  const COVER = /\b(cover|motivation) letter\b/i;
  const WHY = /why (do|would) you (want|like)|why are you interested|why (this|our|us)\b|what (interests|excites|attracts) you/i;
  const FIRST = /^(legal |preferred )?(first|given) name$|^preferred name$/i;
  const LAST = /^(legal )?(last|family) name$|^surname$/i;
  const FULL = /^(your |legal )?(full )?name$/i;
  const YES = /^(yes|y|true|i agree|agree)$/i;

  /** Ask the app (through background.js). */
  JSA.ask = async (message) => {
    const reply = await chrome.runtime.sendMessage(message);
    if (reply && reply.error) throw new Error(reply.error);
    return reply;
  };
  const resolve = async (job, question, options, required) => {
    const reply = await JSA.ask({ type: "answer", jobId: job.id, question, options, required });
    return [reply.answer, reply.how];
  };
  const write = async (job, question) => (await JSA.ask({ type: "write", jobId: job.id, question })).text || "";
  const textFile = (name, text) => ({ name, type: "text/plain", base64: btoa(unescape(encodeURIComponent(text))) });

  const filled = (f) => (f.boxes ? f.boxes.some((b) => b.checked) : f.kind === "file" ? f.el.files?.length > 0
    : f.kind === "checkbox" ? f.el.checked : Boolean(f.el.value || f.el.innerText));

  async function decide(f, job, memo) {
    const label = f.label;
    if (f.kind === "file") {
      if (COVER.test(label)) {
        memo.letter = memo.letter ?? await write(job, "Cover letter");
        return memo.letter ? ["Cover letter written by AI", "ai_letter", textFile("cover-letter.txt", memo.letter)] : [null, ""];
      }
      if (RESUME.test(label) || RESUME.test(f.name)) {
        memo.resume = memo.resume ?? await JSA.ask({ type: "resume" });
        return memo.resume ? ["Your resume file", "resume", memo.resume] : [null, ""];
      }
      return [null, ""];
    }
    if (TEXT.has(f.kind) && (COVER.test(label) || WHY.test(label))) {
      const text = COVER.test(label) ? (memo.letter = memo.letter ?? await write(job, "Cover letter")) : await write(job, label);
      return text ? [text, "ai_letter"] : [null, ""];
    }
    if (TEXT.has(f.kind) && (FIRST.test(label) || LAST.test(label) || (FULL.test(label) && f.kind !== "textarea"))) {
      const [full, how] = await resolve(job, "Full name", [], f.required);
      if (!full) return [null, how];
      const [first, ...rest] = full.trim().split(/\s+/);
      return [FIRST.test(label) ? first : LAST.test(label) ? rest.join(" ") : full, how];
    }
    if (f.kind === "radio" && f.options.length && RESUME.test(label)) return [f.options[0], "resume"];  // a saved resume
    const options = f.kind === "checkbox" && !f.multi ? ["Yes", "No"] : f.options;
    return resolve(job, label, options, f.required);
  }

  function put(f, value, file) {
    if (f.kind === "file") { JSA.attach(f.el, file); return true; }
    if (TEXT.has(f.kind)) { JSA.setValue(f.el, value); return true; }
    if (f.kind === "select") {
      const option = JSA.pick(f.options, value);
      const match = option && [...f.el.options].find((o) => JSA.clean(o.text) === option);
      if (!match) return false;
      JSA.setValue(f.el, match.value);
      return true;
    }
    if (f.boxes) {
      const wanted = (f.multi ? value.split(",") : [value]).map((part) => JSA.pick(f.options, part)).filter(Boolean);
      if (!wanted.length) return false;
      f.boxes.forEach((box, i) => wanted.includes(f.options[i]) && JSA.check(box));
      return true;
    }
    if (f.kind === "checkbox") { if (YES.test(JSA.clean(value))) JSA.check(f.el); return true; }
    return false;
  }

  /** Fill every field in root: {answers, missing}. A field the page already filled in is left as it is. */
  JSA.fill = async (root, job) => {
    const answers = [], missing = [], memo = JSA.memo = JSA.memo || {};
    for (const f of JSA.readFields(root)) {
      if (!f.label) continue;
      const [value, how, file] = await decide(f, job, memo);
      if (value != null && put(f, value, file)) {
        answers.push({ question: f.label, answer: String(value).slice(0, 500), how });
        await JSA.pause(0.3, 1);
      } else if (f.required && !filled(f)) {
        missing.push(f.label);
      }
    }
    return { answers, missing, letter: memo.letter || "" };
  };
})();
