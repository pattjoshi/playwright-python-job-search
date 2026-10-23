"""Read an application form: every field a person would fill in, with its question, type, options and whether it's required.

Runs in the page. Each field (or radio/checkbox group) is tagged with data-ja="<key>" so the filler can find it again.
"""

from dataclasses import dataclass, field

from playwright.sync_api import Page

from job_search.services.auto_apply.platforms import FORM_HINTS

_EXTRACT = r"""
([hint]) => {
  const clean = (t) => (t || "").replace(/\s+/g, " ").trim();
  const shown = (el) => { if (!el) return false; const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.display !== "none" && s.visibility !== "hidden" && (r.width > 0 || r.height > 0); };
  const fieldsIn = (root) => [...root.querySelectorAll("input, textarea, select")].filter((el) =>
    !["hidden", "submit", "button", "reset", "image", "search", "password"].includes(el.type) && !el.disabled
    && el.getAttribute("aria-hidden") !== "true");
  // The form: the platform's usual place, else the <form> with the most fields, else the page.
  let root = hint && [...document.querySelectorAll(hint)].find((el) => fieldsIn(el).length) || null;
  if (!root) root = [...document.querySelectorAll("form")].sort((a, b) => fieldsIn(b).length - fieldsIn(a).length)[0] || document.body;
  const labelOf = (el) => el.id ? document.querySelector(`label[for="${CSS.escape(el.id)}"]`) : null;
  const labelText = (el) => {
    const own = labelOf(el); if (own && clean(own.innerText)) return clean(own.innerText);
    const by = el.getAttribute("aria-labelledby");
    if (by) { const t = clean(by.split(/\s+/).map((id) => document.getElementById(id)?.innerText || "").join(" ")); if (t) return t; }
    if (el.getAttribute("aria-label")) return clean(el.getAttribute("aria-label"));
    const wrap = el.closest("label"); if (wrap && clean(wrap.innerText)) return clean(wrap.innerText);
    return "";
  };
  const questionText = (el) => {  // the question above a field or a group of options
    const set = el.closest("fieldset"); const legend = set && set.querySelector("legend");
    if (legend && clean(legend.innerText)) return clean(legend.innerText);
    let p = el.parentElement;
    for (let i = 0; i < 5 && p && p !== root.parentElement; i++, p = p.parentElement) {
      const l = [...p.querySelectorAll("label, legend, [class*='label'], [class*='question'], [class*='title']")]
        .find((x) => !x.contains(el) && !x.querySelector("input, select, textarea") && clean(x.innerText));
      if (l) return clean(l.innerText);
    }
    return "";
  };
  const fields = []; const groups = {};
  for (const el of fieldsIn(root)) {
    const type = el.tagName === "SELECT" ? "select" : el.tagName === "TEXTAREA" ? "textarea" : (el.type || "text");
    const box = type === "radio" || type === "checkbox";
    if (!box && type !== "file" && !shown(el)) continue;
    if (box && !shown(el) && !shown(el.closest("label")) && !shown(labelOf(el))) continue;
    const required = el.required || el.getAttribute("aria-required") === "true";
    if (box && el.name && root.querySelectorAll(`input[name="${CSS.escape(el.name)}"]`).length > 1) {
      const g = groups[el.name] || (groups[el.name] = { key: `g${fields.length}`, kind: type, multi: type === "checkbox",
        label: questionText(el), required: false, options: [], name: el.name });
      if (!fields.includes(g)) fields.push(g);
      g.required = g.required || required;
      const option = labelText(el) || el.value; g.options.push(option);
      el.setAttribute("data-ja", g.key); el.setAttribute("data-ja-option", option);
      continue;
    }
    const key = `f${fields.length}`; el.setAttribute("data-ja", key);
    const label = (box ? labelText(el) : labelText(el) || questionText(el)) || clean(el.placeholder) || clean(el.name);
    const options = type === "select" ? [...el.options].filter((o) => o.value && !/^(select|choose|please)/i.test(o.text.trim()))
      .map((o) => clean(o.text)) : [];
    fields.push({ key, kind: type, multi: false, label, required, options, name: el.name || "",
      combobox: el.getAttribute("role") === "combobox" });
  }
  for (const f of fields) {  // a "*", "✱" or "(required)" in the question also means required
    if (/[*✱]|\(required\)/i.test(f.label)) f.required = true;
    f.label = clean(f.label.replace(/[*✱]|\(required\)|\(optional\)/gi, ""));
  }
  root.setAttribute("data-ja-form", "1");
  return fields;
}
"""


@dataclass
class FormField:
    key: str
    kind: str  # text | email | tel | url | number | date | textarea | select | file | radio | checkbox
    label: str
    required: bool = False
    options: list[str] = field(default_factory=list)
    name: str = ""
    multi: bool = False  # a group of checkboxes (pick several)
    combobox: bool = False  # a type-to-search box

    @property
    def selector(self) -> str:
        return f'[data-ja="{self.key}"]'


def read_form(page: Page, platform: str = "other") -> list[FormField]:
    """The fields of the application form on the page (empty when there's no form)."""
    raw = page.evaluate(_EXTRACT, [FORM_HINTS.get(platform, "")])
    return [FormField(**{k: v for k, v in item.items() if k in FormField.__dataclass_fields__}) for item in raw]
