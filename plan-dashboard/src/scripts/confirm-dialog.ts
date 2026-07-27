/**
 * confirm-dialog.ts — a themed, promise-based replacement for window.confirm().
 *
 * Vanilla (no framework). Returns Promise<boolean> — true = confirmed, false =
 * cancelled (Esc, backdrop click, or the cancel button). Modal semantics: a focus
 * trap between the two buttons, Escape / backdrop-to-cancel, and focus restored to
 * the element that was focused before it opened. Styling lives in book-composer.css
 * (`.cx-confirm-*`), reusing the --c-* theme tokens — no inline styles (site DoD).
 */

export interface ConfirmOptions {
  title: string;
  body?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** danger: red primary button + default focus on Cancel (the safe choice). */
  danger?: boolean;
  /** Font Awesome classes (e.g. "fa-solid fa-feather-pointed") rendered as an
   *  accent badge beside the title. Decorative — aria-hidden. */
  titleIcon?: string;
  /** Icon-led bullet points rendered between body and actions — the rich form
   *  for prompts that promise several things at once. Icons are FA classes. */
  points?: { icon: string; text: string }[];
  /** Small muted line under the points (duration hints, side effects). */
  footnote?: string;
}

/** The optional rich middle of a confirm box: icon badge in the title row,
 *  icon-led points, footnote. Shared by confirmDialog; built with
 *  createElement throughout (no markup strings), styled in book-composer.css. */
function applyRichContent(
  box: HTMLElement,
  h: HTMLElement,
  opts: Pick<ConfirmOptions, "titleIcon" | "points" | "footnote">,
): void {
  if (opts.titleIcon) {
    const head = document.createElement("div");
    head.className = "cx-confirm-head";
    const badge = document.createElement("span");
    badge.className = "cx-confirm-icon";
    const i = document.createElement("i");
    i.className = opts.titleIcon;
    i.setAttribute("aria-hidden", "true");
    badge.append(i);
    h.replaceWith(head);
    head.append(badge, h);
  }
  if (opts.points?.length) {
    const ul = document.createElement("ul");
    ul.className = "cx-confirm-points";
    for (const pt of opts.points) {
      const li = document.createElement("li");
      const ic = document.createElement("span");
      ic.className = "cx-confirm-point-icon";
      const i = document.createElement("i");
      i.className = pt.icon;
      i.setAttribute("aria-hidden", "true");
      ic.append(i);
      const tx = document.createElement("span");
      tx.textContent = pt.text;
      li.append(ic, tx);
      ul.append(li);
    }
    box.append(ul);
  }
  if (opts.footnote) {
    const f = document.createElement("p");
    f.className = "cx-confirm-foot";
    f.textContent = opts.footnote;
    box.append(f);
  }
}

export function confirmDialog(opts: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    const prevFocus = document.activeElement as HTMLElement | null;

    const scrim = document.createElement("div");
    scrim.className = "cx-confirm-scrim";

    const box = document.createElement("div");
    box.className = "cx-confirm-box";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    const titleId = `cx-confirm-title-${Math.abs(hashString(opts.title))}`;
    box.setAttribute("aria-labelledby", titleId);

    const h = document.createElement("h2");
    h.className = "cx-confirm-title";
    h.id = titleId;
    h.textContent = opts.title;
    box.append(h);

    if (opts.body) {
      const bodyId = `${titleId}-body`;
      const p = document.createElement("p");
      p.className = "cx-confirm-body";
      p.id = bodyId;
      p.textContent = opts.body;
      box.append(p);
      box.setAttribute("aria-describedby", bodyId); // announce the explanation, not just the title
    }

    applyRichContent(box, h, opts);

    const actions = document.createElement("div");
    actions.className = "cx-confirm-actions";
    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "cx-confirm-btn";
    cancelBtn.textContent = opts.cancelLabel ?? "Cancel";
    const okBtn = document.createElement("button");
    okBtn.type = "button";
    okBtn.className = `cx-confirm-btn cx-confirm-btn--primary${opts.danger ? " cx-confirm-btn--danger" : ""}`;
    okBtn.textContent = opts.confirmLabel ?? "Confirm";
    actions.append(cancelBtn, okBtn);
    box.append(actions);
    scrim.append(box);
    document.body.append(scrim);

    let closed = false;
    const close = (result: boolean) => {
      if (closed) return;
      closed = true;
      document.removeEventListener("keydown", onKey, true);
      scrim.remove();
      if (prevFocus && typeof prevFocus.focus === "function") prevFocus.focus();
      resolve(result);
    };

    const focusables = [cancelBtn, okBtn];
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close(false);
      } else if (e.key === "Tab") {
        // Trap focus between the two buttons.
        e.preventDefault();
        const idx = focusables.indexOf(
          document.activeElement as HTMLButtonElement,
        );
        const dir = e.shiftKey ? -1 : 1;
        focusables[(idx + dir + focusables.length) % focusables.length].focus();
      }
    };
    document.addEventListener("keydown", onKey, true);
    scrim.addEventListener("mousedown", (e) => {
      if (e.target === scrim) close(false);
    });
    cancelBtn.addEventListener("click", () => close(false));
    okBtn.addEventListener("click", () => close(true));

    // Danger prompts default to the safe (Cancel) button; others to the primary.
    (opts.danger ? cancelBtn : okBtn).focus();
  });
}

/** A one-button themed notice — replaces window.alert() for error/info messages. */
export function noticeDialog(opts: {
  title: string;
  body?: string;
  dismissLabel?: string;
  danger?: boolean;
}): Promise<void> {
  return new Promise((resolve) => {
    const prevFocus = document.activeElement as HTMLElement | null;

    const scrim = document.createElement("div");
    scrim.className = "cx-confirm-scrim";
    const box = document.createElement("div");
    box.className = "cx-confirm-box";
    box.setAttribute("role", "alertdialog");
    box.setAttribute("aria-modal", "true");
    const titleId = `cx-confirm-title-${Math.abs(hashString(opts.title))}`;
    box.setAttribute("aria-labelledby", titleId);

    const h = document.createElement("h2");
    h.className = "cx-confirm-title";
    h.id = titleId;
    h.textContent = opts.title;
    box.append(h);
    if (opts.body) {
      const bodyId = `${titleId}-body`;
      const p = document.createElement("p");
      p.className = "cx-confirm-body";
      p.id = bodyId;
      p.textContent = opts.body;
      box.append(p);
      box.setAttribute("aria-describedby", bodyId);
    }

    const actions = document.createElement("div");
    actions.className = "cx-confirm-actions";
    const okBtn = document.createElement("button");
    okBtn.type = "button";
    okBtn.className = `cx-confirm-btn cx-confirm-btn--primary${opts.danger ? " cx-confirm-btn--danger" : ""}`;
    okBtn.textContent = opts.dismissLabel ?? "OK";
    actions.append(okBtn);
    box.append(actions);
    scrim.append(box);
    document.body.append(scrim);

    let closed = false;
    const close = () => {
      if (closed) return;
      closed = true;
      document.removeEventListener("keydown", onKey, true);
      scrim.remove();
      if (prevFocus && typeof prevFocus.focus === "function") prevFocus.focus();
      resolve();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" || e.key === "Enter") {
        e.preventDefault();
        close();
      } else if (e.key === "Tab") {
        e.preventDefault();
        okBtn.focus();
      } // trap on the sole button
    };
    document.addEventListener("keydown", onKey, true);
    scrim.addEventListener("mousedown", (e) => {
      if (e.target === scrim) close();
    });
    okBtn.addEventListener("click", close);
    okBtn.focus();
  });
}

/** Handle returned by busyDialog — the caller drives the lifecycle. */
export interface BusyHandle {
  /** Replace the status line (e.g. polling progress). */
  update(status: string): void;
  /** Remove the modal and restore focus. Safe to call twice. */
  close(): void;
}

/**
 * busyDialog — a BLOCKING progress modal for AI actions: centered scrim, a
 * ring-spinner around the action's icon, title, live status line. No buttons,
 * Esc and backdrop are swallowed — the caller closes it from its own
 * success/error paths (every caller must close() in a finally). aria-busy +
 * a polite live region so the status updates are announced.
 */
export function busyDialog(opts: {
  title: string;
  status?: string;
  /** FA classes for the icon at the spinner's centre. */
  icon?: string;
  /** Small muted line under the status (what is locked, how long it takes). */
  note?: string;
}): BusyHandle {
  const prevFocus = document.activeElement as HTMLElement | null;

  const scrim = document.createElement("div");
  scrim.className = "cx-confirm-scrim cx-busy-scrim";
  const box = document.createElement("div");
  box.className = "cx-confirm-box cx-busy-box";
  box.setAttribute("role", "alertdialog");
  box.setAttribute("aria-modal", "true");
  box.setAttribute("aria-busy", "true");
  const titleId = `cx-busy-title-${Math.abs(hashString(opts.title))}`;
  box.setAttribute("aria-labelledby", titleId);

  const spin = document.createElement("span");
  spin.className = "cx-busy-spinner";
  const i = document.createElement("i");
  i.className = opts.icon ?? "fa-solid fa-feather-pointed";
  i.setAttribute("aria-hidden", "true");
  spin.append(i);
  box.append(spin);

  const h = document.createElement("h2");
  h.className = "cx-confirm-title";
  h.id = titleId;
  h.textContent = opts.title;
  box.append(h);

  const status = document.createElement("p");
  status.className = "cx-busy-status";
  status.setAttribute("aria-live", "polite");
  status.textContent = opts.status ?? "";
  box.append(status);

  if (opts.note) {
    const f = document.createElement("p");
    f.className = "cx-confirm-foot";
    f.textContent = opts.note;
    box.append(f);
  }

  scrim.append(box);
  document.body.append(scrim);

  // Blocking: swallow Esc and Tab (there is nothing to focus), ignore backdrop.
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape" || e.key === "Tab") e.preventDefault();
  };
  document.addEventListener("keydown", onKey, true);
  (box as HTMLElement).tabIndex = -1;
  box.focus();

  let closed = false;
  return {
    update(msg: string) {
      if (!closed) status.textContent = msg;
    },
    close() {
      if (closed) return;
      closed = true;
      document.removeEventListener("keydown", onKey, true);
      scrim.remove();
      if (prevFocus && typeof prevFocus.focus === "function") prevFocus.focus();
    },
  };
}

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++)
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return h;
}
