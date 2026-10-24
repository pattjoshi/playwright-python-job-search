// Easy Apply on each board, run inside the job's tab. Returns {status, message, answers, signedIn}.
(() => {
  const JSA = (window.JSA = window.JSA || {});
  const SIGN_IN = /^(sign in|log ?in)( to apply)?$|^(login|register) to apply$/i;
  const result = (status, message, answers = [], extra = {}) => ({ status, message, answers, ...extra });
  const missingText = (missing) => "Waiting for your answer to: " + missing.slice(0, 5).join("; ");
  const signedOut = () => Boolean(JSA.button(SIGN_IN)) || /\/login|\/signin|authwall|nlogin/i.test(location.href);

  /** Fill each page of a multi-step form, clicking Next until Submit (which a dry run doesn't press). */
  JSA.steps = async (job, scope, next, submit, sent, onDryRun = () => {}) => {
    const answers = [];
    for (let step = 0; step < 12; step++) {
      await JSA.pause(1, 2.5);
      const { answers: given, missing } = await JSA.fill(scope(), job);
      answers.push(...given);
      if (missing.length) return result("needs_answer", missingText(missing), answers, { signedIn: true });
      const send = JSA.button(submit, scope());
      if (send) {
        if (job.dry_run) { onDryRun(); return result("filled", "Dry run: every step was filled; Submit was not pressed.", answers, { signedIn: true }); }
        await JSA.ask({ type: "submitting", jobId: job.id, answers });
        await JSA.pause();
        send.click();
        const ok = await JSA.until(() => sent.test(JSA.text()), 15);
        return ok ? result("submitted", "Submitted.", answers, { signedIn: true })
          : result("unconfirmed", "Submitted, but no confirmation was shown. Check your email.", answers, { signedIn: true });
      }
      const forward = JSA.button(next, scope());
      if (!forward) return result("failed", "Couldn't find the Next or Submit button.", answers, { signedIn: true });
      const before = scope().innerText;
      forward.click();
      await JSA.sleep(900);
      const errors = [...scope().querySelectorAll("[role=alert], .artdeco-inline-feedback--error, [aria-invalid=true]")]
        .filter((e) => JSA.shown(e) && JSA.clean(e.innerText)).map((e) => JSA.clean(e.innerText));
      if (errors.length && scope().innerText === before) return result("failed", "The form showed errors: " + errors.slice(0, 3).join("; "), answers);
    }
    return result("failed", "The application had more steps than expected.", answers);
  };

  JSA.boards = {
    async linkedin(job) {
      const easy = () => JSA.button(/easy apply/i);
      await JSA.until(() => easy() || JSA.button(/^apply( now)?$|apply on company website/i) || signedOut(), 20);
      await JSA.pause();
      if (!easy() && signedOut()) return result("blocked", "Not signed in to LinkedIn in this Chrome. Sign in to LinkedIn, then press Start again.");
      if (!easy()) return result("blocked", "No Easy Apply on this job (it's applied to on the company's site).", [], { signedIn: true });
      easy().click();
      const dialog = await JSA.until(() => document.querySelector(".jobs-easy-apply-modal, [role=dialog]"), 15);
      if (!dialog) return result("failed", "The Easy Apply window didn't open.");
      const scope = () => document.querySelector(".jobs-easy-apply-modal, [role=dialog]") || document.body;
      return JSA.steps(job, scope, /^(next|continue|review)( to next step| your application)?$/i, /^submit( application)?$/i,
        /application (was )?sent|your application was sent/i, () => {
          JSA.button(/dismiss|close/i, scope())?.click();
          setTimeout(() => JSA.button(/^discard$/i)?.click(), 600);
        });
    },

    async indeed(job) {
      if (/smartapply|\/apply/i.test(location.href) && document.querySelector("input, textarea, select")) return JSA.indeedSteps(job);
      const apply = () => JSA.button(/^apply now$|^easily apply$/i);
      await JSA.until(() => apply() || JSA.button(/apply on company site/i) || signedOut(), 20);
      if (JSA.button(/apply on company site/i)) return result("blocked", "This job is applied to on the company's site, not on Indeed.", [], { signedIn: true });
      if (!apply()) return signedOut() ? result("blocked", "Not signed in to Indeed in this Chrome. Sign in, then press Start again.")
        : result("failed", "Couldn't find Indeed's Apply now button.");
      await JSA.pause();
      apply().click();
      return result("continue", "Opening the application…", [], { newTab: true, signedIn: true });
    },
    async indeedSteps(job) {
      return JSA.steps(job, () => document.body, /^(continue|next|review your application)$/i, /^submit( your application)?$/i,
        /application (has been |was )?submitted|your application has been sent/i);
    },

    async naukri(job) {
      const find = (p) => JSA.button(p);
      await JSA.until(() => find(/^apply$/i) || find(/^applied$/i) || find(/apply on company (site|website)/i) || signedOut(), 20);
      await JSA.pause();
      if (signedOut()) return result("blocked", "Not signed in to Naukri in this Chrome. Sign in to Naukri, then press Start again.");
      if (find(/^applied$/i)) return result("submitted", "Already applied on Naukri.", [], { signedIn: true });
      if (find(/apply on company (site|website)/i)) return result("blocked", "This job is applied to on the company's site, not on Naukri.", [], { signedIn: true });
      if (!find(/^apply$/i)) return result("failed", "Couldn't find Naukri's Apply button.", [], { signedIn: true });
      if (job.dry_run) return result("filled", "Dry run: signed in and Easy Apply is available. (Naukri applies on the first click, so nothing was clicked.)", [], { signedIn: true });
      await JSA.ask({ type: "submitting", jobId: job.id, answers: [] });
      find(/^apply$/i).click();
      return JSA.naukriChat(job);
    },
  };

  JSA.run = async (job, pace) => {
    JSA.pace = pace;
    JSA.memo = {};
    const flow = JSA.boards[job.platform];
    if (!flow) return result("failed", `The extension can't apply on ${job.platform}.`);
    try {
      return await flow(job);
    } catch (error) {
      return result("failed", `Something went wrong: ${String(error.message || error).slice(0, 200)}`);
    }
  };
})();
