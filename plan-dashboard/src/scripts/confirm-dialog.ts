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
}

export function confirmDialog(opts: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    const prevFocus = document.activeElement as HTMLElement | null;

    const scrim = document.createElement('div');
    scrim.className = 'cx-confirm-scrim';

    const box = document.createElement('div');
    box.className = 'cx-confirm-box';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    const titleId = `cx-confirm-title-${Math.abs(hashString(opts.title))}`;
    box.setAttribute('aria-labelledby', titleId);

    const h = document.createElement('h2');
    h.className = 'cx-confirm-title';
    h.id = titleId;
    h.textContent = opts.title;
    box.append(h);

    if (opts.body) {
      const bodyId = `${titleId}-body`;
      const p = document.createElement('p');
      p.className = 'cx-confirm-body';
      p.id = bodyId;
      p.textContent = opts.body;
      box.append(p);
      box.setAttribute('aria-describedby', bodyId); // announce the explanation, not just the title
    }

    const actions = document.createElement('div');
    actions.className = 'cx-confirm-actions';
    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'cx-confirm-btn';
    cancelBtn.textContent = opts.cancelLabel ?? 'Cancel';
    const okBtn = document.createElement('button');
    okBtn.type = 'button';
    okBtn.className = `cx-confirm-btn cx-confirm-btn--primary${opts.danger ? ' cx-confirm-btn--danger' : ''}`;
    okBtn.textContent = opts.confirmLabel ?? 'Confirm';
    actions.append(cancelBtn, okBtn);
    box.append(actions);
    scrim.append(box);
    document.body.append(scrim);

    let closed = false;
    const close = (result: boolean) => {
      if (closed) return;
      closed = true;
      document.removeEventListener('keydown', onKey, true);
      scrim.remove();
      if (prevFocus && typeof prevFocus.focus === 'function') prevFocus.focus();
      resolve(result);
    };

    const focusables = [cancelBtn, okBtn];
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        close(false);
      } else if (e.key === 'Tab') {
        // Trap focus between the two buttons.
        e.preventDefault();
        const idx = focusables.indexOf(document.activeElement as HTMLButtonElement);
        const dir = e.shiftKey ? -1 : 1;
        focusables[(idx + dir + focusables.length) % focusables.length].focus();
      }
    };
    document.addEventListener('keydown', onKey, true);
    scrim.addEventListener('mousedown', (e) => {
      if (e.target === scrim) close(false);
    });
    cancelBtn.addEventListener('click', () => close(false));
    okBtn.addEventListener('click', () => close(true));

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

    const scrim = document.createElement('div');
    scrim.className = 'cx-confirm-scrim';
    const box = document.createElement('div');
    box.className = 'cx-confirm-box';
    box.setAttribute('role', 'alertdialog');
    box.setAttribute('aria-modal', 'true');
    const titleId = `cx-confirm-title-${Math.abs(hashString(opts.title))}`;
    box.setAttribute('aria-labelledby', titleId);

    const h = document.createElement('h2');
    h.className = 'cx-confirm-title';
    h.id = titleId;
    h.textContent = opts.title;
    box.append(h);
    if (opts.body) {
      const bodyId = `${titleId}-body`;
      const p = document.createElement('p');
      p.className = 'cx-confirm-body';
      p.id = bodyId;
      p.textContent = opts.body;
      box.append(p);
      box.setAttribute('aria-describedby', bodyId);
    }

    const actions = document.createElement('div');
    actions.className = 'cx-confirm-actions';
    const okBtn = document.createElement('button');
    okBtn.type = 'button';
    okBtn.className = `cx-confirm-btn cx-confirm-btn--primary${opts.danger ? ' cx-confirm-btn--danger' : ''}`;
    okBtn.textContent = opts.dismissLabel ?? 'OK';
    actions.append(okBtn);
    box.append(actions);
    scrim.append(box);
    document.body.append(scrim);

    let closed = false;
    const close = () => {
      if (closed) return;
      closed = true;
      document.removeEventListener('keydown', onKey, true);
      scrim.remove();
      if (prevFocus && typeof prevFocus.focus === 'function') prevFocus.focus();
      resolve();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === 'Enter') { e.preventDefault(); close(); }
      else if (e.key === 'Tab') { e.preventDefault(); okBtn.focus(); } // trap on the sole button
    };
    document.addEventListener('keydown', onKey, true);
    scrim.addEventListener('mousedown', (e) => { if (e.target === scrim) close(); });
    okBtn.addEventListener('click', close);
    okBtn.focus();
  });
}

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return h;
}
