// Reading and filling form fields on a job page (injected by background.js). Same rules as the app's form reader.
(() => {
  const JSA = (window.JSA = window.JSA || {});
  const clean = (t) => (t || "").replace(/\s+/g, " ").trim();
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  JSA.clean = clean;
  JSA.sleep = sleep;
  JSA.shown = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.display !== "none" && s.visibility !== "hidden" && (r.width > 0 || r.height > 0);
  };
  /** Like a person between steps (pace 0 in tests). */
  JSA.pause = (low = 1.5, high = 4) => sleep((low + Math.random() * (high - low)) * 1000 * (JSA.pace ?? 1));
  JSA.until = async (check, seconds = 15) => {
    const end = Date.now() + seconds * 1000;
    while (Date.now() < end) {
      const found = check();
      if (found) return found;
      await sleep(400);
    }
    return check();
  };
  /** The last visible button or link whose text or label matches. */
  JSA.button = (pattern, root = document) =>
    [...root.querySelectorAll("button, a, [role=button], input[type=submit]")]
      .filter((el) => JSA.shown(el) && !el.disabled && pattern.test(clean(el.innerText || el.value || el.getAttribute("aria-label"))))
      .pop() || null;
  JSA.text = () => document.body ? document.body.innerText : "";

  const fieldsIn = (root) => [...root.querySelectorAll("input, textarea, select")].filter((el) =>
    !["hidden", "submit", "button", "reset", "image", "search", "password"].includes(el.type) && !el.disabled
    && el.getAttribute("aria-hidden") !== "true");
  const labelOf = (el) => (el.id ? document.querySelector(`label[for="${CSS.escape(el.id)}"]`) : null);
  const labelText = (el) => {
    const own = labelOf(el); if (own && clean(own.innerText)) return clean(own.innerText);
    const by = el.getAttribute("aria-labelledby");
    if (by) { const t = clean(by.split(/\s+/).map((id) => document.getElementById(id)?.innerText || "").join(" ")); if (t) return t; }
    if (el.getAttribute("aria-label")) return clean(el.getAttribute("aria-label"));
    const wrap = el.closest("label"); return wrap ? clean(wrap.innerText) : "";
  };
  const questionText = (el, root) => {
    const legend = el.closest("fieldset")?.querySelector("legend");
    if (legend && clean(legend.innerText)) return clean(legend.innerText);
    let p = el.parentElement;
    for (let i = 0; i < 5 && p && p !== root.parentElement; i++, p = p.parentElement) {
      const l = [...p.querySelectorAll("label, legend, [class*='label'], [class*='question'], [class*='title']")]
        .find((x) => !x.contains(el) && !x.querySelector("input, select, textarea") && clean(x.innerText));
      if (l) return clean(l.innerText);
    }
    return "";
  };

  /** [{el(s), kind, label, required, options, multi}] for the form inside root. */
  JSA.readFields = (root) => {
    const fields = []; const groups = {};
    for (const el of fieldsIn(root)) {
      const kind = el.tagName === "SELECT" ? "select" : el.tagName === "TEXTAREA" ? "textarea" : (el.type || "text");
      const box = kind === "radio" || kind === "checkbox";
      if (!box && kind !== "file" && !JSA.shown(el)) continue;
      if (box && !JSA.shown(el) && !JSA.shown(el.closest("label")) && !JSA.shown(labelOf(el))) continue;
      const required = el.required || el.getAttribute("aria-required") === "true";
      if (box && el.name && root.querySelectorAll(`input[name="${CSS.escape(el.name)}"]`).length > 1) {
        const g = groups[el.name] || (groups[el.name] = { kind, multi: kind === "checkbox", label: questionText(el, root),
          required: false, options: [], boxes: [], name: el.name });
        if (!fields.includes(g)) fields.push(g);
        g.required = g.required || required;
        g.options.push(labelText(el) || el.value); g.boxes.push(el);
        continue;
      }
      const label = (box ? labelText(el) : labelText(el) || questionText(el, root)) || clean(el.placeholder) || clean(el.name);
      const options = kind === "select" ? [...el.options].filter((o) => o.value && !/^(select|choose|please)/i.test(o.text.trim()))
        .map((o) => clean(o.text)) : [];
      fields.push({ el, kind, label, required, options, name: el.name || "", multi: false });
    }
    for (const f of fields) {
      if (/[*✱]|\(required\)/i.test(f.label)) f.required = true;
      f.label = clean(f.label.replace(/[*✱]|\(required\)|\(optional\)/gi, ""));
    }
    return fields;
  };

  /** Type a value the way a person would, so React / Ember pages notice it. */
  JSA.setValue = (el, value) => {
    el.focus();
    if (el.isContentEditable) {
      document.execCommand("selectAll", false);
      document.execCommand("insertText", false, value);
      return;
    }
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement : el.tagName === "SELECT" ? HTMLSelectElement : HTMLInputElement;
    Object.getOwnPropertyDescriptor(proto.prototype, "value").set.call(el, value);
    for (const type of ["input", "change", "blur"]) el.dispatchEvent(new Event(type, { bubbles: true }));
  };
  JSA.check = (el, on = true) => {
    if (el.checked !== on) (labelOf(el) || el.closest("label") || el).click();
    if (el.checked !== on) el.click();
  };
  JSA.attach = (el, file) => {
    const bytes = Uint8Array.from(atob(file.base64), (c) => c.charCodeAt(0));
    const transfer = new DataTransfer();
    transfer.items.add(new File([bytes], file.name, { type: file.type || "application/octet-stream" }));
    el.files = transfer.files;
    el.dispatchEvent(new Event("change", { bubbles: true }));
  };

  const words = (t) => clean(t).toLowerCase().replace(/[^\p{L}\p{N}\s]+/gu, " ").split(/\s+/).filter(Boolean);
  /** The option an answer means: exact, then starting with the same words, then containing them. */
  JSA.pick = (options, answer) => {
    const wanted = words(answer);
    if (!wanted.length) return null;
    const tests = [(w) => w.join(" ") === wanted.join(" "), (w) => wanted.every((x, i) => w[i] === x),
      (w) => w.length > 0 && w.every((x, i) => wanted[i] === x), (w) => w.join(" ").includes(wanted.join(" "))];
    for (const test of tests) {
      const found = options.find((o) => test(words(o)));
      if (found !== undefined) return found;
    }
    return null;
  };
})();
