/**
 * publish-dialog.ts — the two modal surfaces the Publish button needs.
 *
 * `publishOptionsDialog` asks what to publish; `publishProgressPanel` shows it
 * happening and then shows the verification. Both reuse the `.cx-confirm-*`
 * shell that `confirm-dialog.ts` established, so they look like every other
 * prompt on the Composer, and add only `.cx-pub-*` for the parts that are new.
 *
 * A THIRD dialog implementation rather than a fourth option on `confirmDialog`,
 * deliberately. That function's focus trap is a two-element array of its own
 * buttons — correct and simple for a yes/no prompt, and wrong the moment there
 * are checkboxes between them. Generalising it would have reworked the trap used
 * by every destructive prompt in the Composer to add a feature only this one
 * needs. The trap here is computed from what is actually in the box.
 *
 * Vanilla, no framework, no inline styles — the site's delivery rules. Built with
 * createElement throughout rather than markup strings, matching confirm-dialog.
 */

export interface PublishChoice {
  id: string;
  label: string;
  hint?: string;
  icon: string;
  checked: boolean;
}

export type PublishTarget = "localhost" | "production" | "both";

export interface PublishTargetChoice {
  id: PublishTarget;
  label: string;
  hint?: string;
  icon: string;
  checked: boolean;
}

export interface PublishAsk {
  bookTitle: string;
  reason: string;
  targets: PublishTargetChoice[];
  choices: PublishChoice[];
}

export interface PublishDialogResult {
  target: PublishTarget;
  options: Record<string, boolean>;
}

/** Everything focusable inside a container, in DOM order — the focus ring for a
 *  modal whose contents are not known in advance. */
function focusablesIn(root: HTMLElement): HTMLElement[] {
  return Array.from(
    root.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
    ),
  );
}

/** Modal shell: scrim, box, focus trap, Escape and backdrop to dismiss.
 *  `onDismiss` is null for a panel that must not be dismissable mid-flight. */
function shell(opts: {
  labelledBy: string;
  role: string;
  onDismiss: (() => void) | null;
}): { scrim: HTMLElement; box: HTMLElement; destroy: () => void } {
  const prevFocus = document.activeElement as HTMLElement | null;

  const scrim = document.createElement("div");
  scrim.className = "cx-confirm-scrim";
  const box = document.createElement("div");
  box.className = "cx-confirm-box cx-pub-box";
  box.setAttribute("role", opts.role);
  box.setAttribute("aria-modal", "true");
  box.setAttribute("aria-labelledby", opts.labelledBy);
  scrim.append(box);

  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape" && opts.onDismiss) {
      e.preventDefault();
      opts.onDismiss();
      return;
    }
    if (e.key !== "Tab") return;
    const ring = focusablesIn(box);
    if (!ring.length) return;
    e.preventDefault();
    const idx = ring.indexOf(document.activeElement as HTMLElement);
    const dir = e.shiftKey ? -1 : 1;
    ring[(idx + dir + ring.length) % ring.length].focus();
  };
  document.addEventListener("keydown", onKey, true);
  scrim.addEventListener("mousedown", (e) => {
    if (e.target === scrim && opts.onDismiss) opts.onDismiss();
  });

  return {
    scrim,
    box,
    destroy() {
      document.removeEventListener("keydown", onKey, true);
      scrim.remove();
      if (prevFocus && typeof prevFocus.focus === "function") prevFocus.focus();
    },
  };
}

function titleRow(
  box: HTMLElement,
  id: string,
  icon: string,
  text: string,
): void {
  const head = document.createElement("div");
  head.className = "cx-confirm-head";
  const badge = document.createElement("span");
  badge.className = "cx-confirm-icon";
  const i = document.createElement("i");
  i.className = icon;
  i.setAttribute("aria-hidden", "true");
  badge.append(i);
  const h = document.createElement("h2");
  h.className = "cx-confirm-title";
  h.id = id;
  h.textContent = text;
  head.append(badge, h);
  box.append(head);
}

/**
 * "Publish" — where it should go, and which parts of it.
 *
 * Resolves to the chosen target plus option ids, or null if dismissed. The
 * options are what the caller passed: this function decides nothing about which
 * are sensible, so the intelligence about defaults lives with the code that
 * knows the book.
 */
export function publishOptionsDialog(
  ask: PublishAsk,
): Promise<PublishDialogResult | null> {
  return new Promise((resolve) => {
    const titleId = "cx-pub-title";
    const { scrim, box, destroy } = shell({
      labelledBy: titleId,
      role: "dialog",
      onDismiss: () => finish(null),
    });

    titleRow(box, titleId, "fa-solid fa-cloud-arrow-up", "Publish");

    const lede = document.createElement("p");
    lede.className = "cx-confirm-body";
    lede.textContent = `${ask.bookTitle} goes to the Podcast Factory Library. ${ask.reason}`;
    box.append(lede);

    const targetList = document.createElement("div");
    targetList.className = "cx-pub-choices cx-pub-targets";
    const targetInputs: Partial<Record<PublishTarget, HTMLInputElement>> = {};
    const targetName = `cx-pub-target-${Date.now()}`;

    for (const target of ask.targets) {
      const row = document.createElement("label");
      row.className = "cx-pub-choice cx-pub-choice--target";

      const input = document.createElement("input");
      input.type = "radio";
      input.name = targetName;
      input.value = target.id;
      input.className = "cx-pub-checkbox cx-pub-radio";
      input.checked = target.checked;
      targetInputs[target.id] = input;

      const icon = document.createElement("span");
      icon.className = "cx-pub-choice-icon";
      const i = document.createElement("i");
      i.className = target.icon;
      i.setAttribute("aria-hidden", "true");
      icon.append(i);

      const text = document.createElement("span");
      text.className = "cx-pub-choice-text";
      const label = document.createElement("span");
      label.className = "cx-pub-choice-label";
      label.textContent = target.label;
      text.append(label);
      if (target.hint) {
        const hint = document.createElement("span");
        hint.className = "cx-pub-choice-hint";
        hint.textContent = target.hint;
        text.append(hint);
      }

      row.append(input, icon, text);
      targetList.append(row);
    }
    box.append(targetList);

    const list = document.createElement("div");
    list.className = "cx-pub-choices";
    const inputs: Record<string, HTMLInputElement> = {};

    for (const choice of ask.choices) {
      const row = document.createElement("label");
      row.className = "cx-pub-choice";

      const input = document.createElement("input");
      input.type = "checkbox";
      input.className = "cx-pub-checkbox";
      input.checked = choice.checked;
      inputs[choice.id] = input;

      const icon = document.createElement("span");
      icon.className = "cx-pub-choice-icon";
      const i = document.createElement("i");
      i.className = choice.icon;
      i.setAttribute("aria-hidden", "true");
      icon.append(i);

      const text = document.createElement("span");
      text.className = "cx-pub-choice-text";
      const label = document.createElement("span");
      label.className = "cx-pub-choice-label";
      label.textContent = choice.label;
      text.append(label);
      if (choice.hint) {
        const hint = document.createElement("span");
        hint.className = "cx-pub-choice-hint";
        hint.textContent = choice.hint;
        text.append(hint);
      }

      row.append(input, icon, text);
      list.append(row);
    }
    box.append(list);

    const foot = document.createElement("p");
    foot.className = "cx-confirm-foot";
    // Says the thing that is easiest to assume wrongly. Publishing makes a book
    // READABLE; it does not decide who may read it, and that distinction is the
    // site's whole access model.
    foot.textContent =
      "The book becomes readable by you and by anyone you have already granted it. Opening it to everyone signed in stays on the admin screen.";
    box.append(foot);

    const actions = document.createElement("div");
    actions.className = "cx-confirm-actions";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "cx-confirm-btn";
    cancel.textContent = "Cancel";
    const go = document.createElement("button");
    go.type = "button";
    go.className = "cx-confirm-btn cx-confirm-btn--primary";
    go.textContent = "Publish";
    actions.append(cancel, go);
    box.append(actions);

    document.body.append(scrim);

    let done = false;
    function finish(result: PublishDialogResult | null): void {
      if (done) return;
      done = true;
      destroy();
      resolve(result);
    }

    cancel.addEventListener("click", () => finish(null));
    go.addEventListener("click", () => {
      const selected =
        (Object.entries(targetInputs).find(
          ([, input]) => input?.checked,
        )?.[0] as PublishTarget | undefined) ?? "both";
      const chosen: Record<string, boolean> = {};
      for (const [id, input] of Object.entries(inputs))
        chosen[id] = input.checked;
      finish({ target: selected, options: chosen });
    });
    go.focus();
  });
}

export type PublishOutcome = "ok" | "bad" | "neutral";

export interface ProgressPanel {
  /** Name the phase now running. */
  step(name: string): void;
  /** One line of output from the run. */
  log(text: string, tone?: "plain" | "warn" | "error"): void;
  /** One verification result. */
  check(name: string, ok: boolean, detail: string): void;
  /** Final state: unlocks Close and shows the banner.
   *
   *  THREE outcomes, not two. A dry run is neither verified nor broken, and
   *  reporting it as a failure — which is what a boolean forced — made a
   *  successful rehearsal read in red as "Finished with problems". */
  finish(outcome: PublishOutcome, text: string): void;
  /** Resolves when the panel is closed — never before `finish`. */
  closed: Promise<void>;
}

/**
 * The live panel: what is happening, then what was proved.
 *
 * NOT dismissable while the run is in flight — no Escape, no backdrop click, no
 * Close button until `finish`. A publish that is halfway through uploading is
 * not improved by the window that was reporting it disappearing, and the panel
 * is the only place the verification is shown.
 */
export function publishProgressPanel(bookTitle: string): ProgressPanel {
  const titleId = "cx-pub-progress-title";
  let running = true;
  let resolveClosed: () => void;
  const closed = new Promise<void>((r) => (resolveClosed = r));

  const { scrim, box, destroy } = shell({
    labelledBy: titleId,
    role: "dialog",
    onDismiss: null,
  });

  titleRow(
    box,
    titleId,
    "fa-solid fa-cloud-arrow-up",
    `Publishing ${bookTitle}`,
  );

  const status = document.createElement("p");
  status.className = "cx-pub-status";
  // Announced rather than merely shown: the run is long and the panel is the
  // only feedback, so a screen reader must hear each phase as it starts.
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  const spinner = document.createElement("i");
  spinner.className = "fa-solid fa-spinner fa-spin cx-pub-spin";
  spinner.setAttribute("aria-hidden", "true");
  const statusText = document.createElement("span");
  statusText.textContent = "Starting…";
  status.append(spinner, statusText);
  box.append(status);

  const logEl = document.createElement("div");
  logEl.className = "cx-pub-log";
  logEl.setAttribute("role", "log");
  box.append(logEl);

  const checksWrap = document.createElement("div");
  checksWrap.className = "cx-pub-checks";
  const checksTitle = document.createElement("h3");
  checksTitle.className = "cx-pub-checks-title";
  checksTitle.textContent = "Confirmed after publish";
  checksWrap.append(checksTitle);
  const checksList = document.createElement("ul");
  checksList.className = "cx-pub-check-list";
  checksWrap.append(checksList);
  checksWrap.hidden = true;
  box.append(checksWrap);

  const banner = document.createElement("p");
  banner.className = "cx-pub-banner";
  banner.hidden = true;
  box.append(banner);

  const actions = document.createElement("div");
  actions.className = "cx-confirm-actions";
  const close = document.createElement("button");
  close.type = "button";
  close.className = "cx-confirm-btn cx-confirm-btn--primary";
  close.textContent = "Close";
  close.hidden = true;
  close.disabled = true;
  actions.append(close);
  box.append(actions);

  document.body.append(scrim);

  close.addEventListener("click", () => {
    if (running) return;
    destroy();
    resolveClosed();
  });

  const transcript: string[] = [];

  const copyDetails = async (details: string, btn: HTMLButtonElement) => {
    const prior = btn.textContent ?? "Copy details";
    try {
      await navigator.clipboard.writeText(details);
      btn.textContent = "Copied";
    } catch {
      btn.textContent = "Select details";
    }
    window.setTimeout(() => {
      btn.textContent = prior;
    }, 1600);
  };

  const renderResult = (outcome: PublishOutcome, text: string) => {
    logEl.replaceChildren();
    logEl.classList.add("cx-pub-log--result");
    logEl.removeAttribute("role");

    const result = document.createElement("div");
    result.className = `cx-pub-result is-${outcome}`;
    const heading = document.createElement("strong");
    heading.className = "cx-pub-result-title";
    heading.textContent =
      outcome === "ok"
        ? "Publish successful"
        : outcome === "bad"
          ? "Publish failed"
          : "Publish finished";
    const message = document.createElement("span");
    message.className = "cx-pub-result-message";
    message.textContent = text;
    result.append(heading, message);
    logEl.append(result);

    if (outcome !== "bad") return;

    const details = [
      `Publish failed for ${bookTitle}`,
      text,
      "",
      "Details:",
      ...transcript,
    ].join("\n");
    const detailsWrap = document.createElement("div");
    detailsWrap.className = "cx-pub-failure-details";
    const label = document.createElement("label");
    label.className = "cx-pub-failure-label";
    label.textContent = "Details to share";
    const detailsBox = document.createElement("textarea");
    detailsBox.className = "cx-pub-failure-text";
    detailsBox.readOnly = true;
    detailsBox.value = details;
    label.append(detailsBox);
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "cx-confirm-btn cx-pub-copy-btn";
    copy.textContent = "Copy details";
    copy.addEventListener("click", () => void copyDetails(details, copy));
    detailsWrap.append(label, copy);
    logEl.append(detailsWrap);
  };

  const append = (text: string, cls: string) => {
    transcript.push(text);
    const line = document.createElement("div");
    line.className = cls;
    line.textContent = text;
    logEl.append(line);
    // Follow the tail only. Scrolling back to read an earlier line and being
    // yanked forward by the next one makes a long run unreadable.
    const atBottom =
      logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight < 40;
    if (atBottom) logEl.scrollTop = logEl.scrollHeight;
  };

  return {
    closed,
    step(name) {
      statusText.textContent = name;
      append(name, "cx-pub-line cx-pub-line--step");
    },
    log(text, tone = "plain") {
      append(text, `cx-pub-line cx-pub-line--${tone}`);
    },
    check(name, ok, detail) {
      transcript.push(`${ok ? "PASS" : "FAIL"}: ${name} — ${detail}`);
      checksWrap.hidden = false;
      const li = document.createElement("li");
      li.className = `cx-pub-check ${ok ? "is-ok" : "is-bad"}`;
      const icon = document.createElement("i");
      icon.className = ok
        ? "fa-solid fa-circle-check"
        : "fa-solid fa-circle-xmark";
      icon.setAttribute("aria-hidden", "true");
      // ONE element beside the icon, holding both halves. The row was a
      // three-column grid with four children, so the fourth wrapped into an
      // implicit row and printed on top of the third — every check unreadable
      // (caught in the browser, 2026-08-06).
      const body = document.createElement("span");
      body.className = "cx-pub-check-body";
      // The tick is decorative; the word carries the result for anyone not
      // seeing colour or icons.
      const sr = document.createElement("span");
      sr.className = "sr-only";
      sr.textContent = ok ? "passed: " : "failed: ";
      const label = document.createElement("span");
      label.className = "cx-pub-check-name";
      label.textContent = name;
      const value = document.createElement("span");
      value.className = "cx-pub-check-detail";
      value.textContent = detail;
      body.append(sr, label, value);
      li.append(icon, body);
      checksList.append(li);
    },
    finish(outcome, text) {
      running = false;
      box.classList.remove("is-ok", "is-bad", "is-neutral");
      box.classList.add(`is-${outcome}`);
      spinner.remove();
      statusText.textContent =
        outcome === "ok"
          ? "Done"
          : outcome === "bad"
            ? "Finished with problems"
            : "Finished";
      renderResult(outcome, text);
      banner.hidden = false;
      banner.className = `cx-pub-banner is-${outcome}`;
      banner.textContent = text;
      close.hidden = false;
      close.disabled = false;
      close.focus();
    },
  };
}
