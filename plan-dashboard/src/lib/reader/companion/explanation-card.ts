/**
 * explanation-card.ts — ONE card for a Companion note, in every surface.
 *
 * The Book Composer's Scholar panel and the LIVE Session reader show the SAME
 * cards: same component, same data, same look. The only difference between them is
 * capability — the Composer passes `onSave`/`onRemove` and the card grows an edit
 * form and a delete control; the reader passes neither and the card is read-only.
 * Two implementations of one card is how the two surfaces would start to disagree
 * about what a note looks like, so there is exactly one.
 *
 * Framework-free (a builder returning an element) because one of those hosts is
 * React and the other is plain DOM.
 *
 * The card is COLLAPSED by default: the passage it annotates, plus a short opening
 * extract. Clicking the header expands it to the full explanation — an answer can
 * run a thousand words, and a wall of them buries both the chapter you are reading
 * beside it and the other notes on the same page.
 *
 * The QUOTE is shown in the header, not just stored: a card exists to explain one
 * highlighted sentence, and a card headed only by a theme ("Have you met your own
 * resistance?") leaves you unable to tell which highlight it belongs to.
 *
 * Arabic inside an explanation is set in the book's own Arabic face at a size that
 * reads as equal to the Latin text around it (Arabic renders visually smaller at
 * equal point size). All of it is class names resolved by companion-card.css;
 * nothing here sets a style attribute.
 */
import { sourceProvider, kindDef } from "./registry";

export interface CardNote {
  id: string;
  kind: string;
  body: string;
  /** Card title — a short theme label for the note. */
  anchor?: string;
  /** The chapter sentence this card explains. */
  quote?: string;
  source?: { provider: string; label?: string; ref?: string };
}

export interface CardEdit {
  anchor: string;
  body: string;
}

export interface CardOptions {
  /** Expanded on mount. */
  open?: boolean;
  /** Header clicked: the card wants to expand/collapse. */
  onToggle?: (id: string, open: boolean) => void;
  /** Header clicked: the card wants its passage shown in the prose. */
  onReveal?: (id: string) => void;
  /** Editing capability. Given, the card offers Edit; the reader omits it. */
  onSave?: (id: string, edit: CardEdit) => Promise<void> | void;
  /** Delete capability. Given, the card offers Remove; the reader omits it. */
  onRemove?: (id: string) => void;
}

/** Arabic script, including the presentation forms an OCR pass can emit. */
const ARABIC_RUN = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿][؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿\sً-ْ]*/g;

/** Split an answer into paragraphs, dropping the blank runs between them. */
export function cardParagraphs(text: string): string[] {
  return String(text ?? "")
    .split(/\n{2,}/)
    .map((p) => p.replace(/[ \t]+/g, " ").trim())
    .filter(Boolean);
}

/** The one-line gist shown while the card is collapsed. */
export function cardPreview(text: string, limit = 150): string {
  const first = cardParagraphs(text)[0] ?? "";
  if (first.length <= limit) return first;
  return `${first.slice(0, limit).replace(/\s+\S*$/, "")}…`;
}

/**
 * Fill an element with text, with every Arabic run in its own styled span.
 *
 * Deliberately NOT innerHTML: an explanation is model output and must never be
 * able to introduce markup into a page that also hosts the book's own prose.
 */
export function setTextWithArabic(el: HTMLElement, text: string): void {
  el.textContent = "";
  let last = 0;
  for (const m of text.matchAll(ARABIC_RUN)) {
    const start = m.index ?? 0;
    const run = m[0].replace(/\s+$/, "");
    if (!run) continue;
    if (start > last) el.append(text.slice(last, start));
    const span = document.createElement("span");
    span.className = "xpl-ar";
    span.dir = "rtl";
    span.lang = "ar";
    span.textContent = run;
    el.append(span);
    last = start + run.length;
  }
  if (last < text.length) el.append(text.slice(last));
}

function button(cls: string, label: string, title?: string): HTMLButtonElement {
  const b = document.createElement("button");
  b.type = "button";
  b.className = cls;
  b.textContent = label;
  if (title) b.title = title;
  return b;
}

/** Build one collapsible explanation card. */
export function renderExplanationCard(
  note: CardNote,
  opts: CardOptions = {},
): HTMLElement {
  const card = document.createElement("article");
  card.className = "xpl";
  card.dataset.note = note.id;

  // ── header: what this card is about ──────────────────────────────────────
  const head = document.createElement("button");
  head.type = "button";
  head.className = "xpl-head";
  head.setAttribute("aria-expanded", String(!!opts.open));

  const meta = document.createElement("span");
  meta.className = "xpl-meta";
  const kind = document.createElement("span");
  kind.className = "xpl-kind";
  kind.textContent = kindDef(note.kind).label;
  meta.append(kind);
  const provider = note.source?.provider;
  if (provider) {
    const src = document.createElement("span");
    src.className = "xpl-source";
    src.textContent =
      note.source?.label || note.source?.ref || sourceProvider(provider).label;
    meta.append(src);
  }

  const title = document.createElement("span");
  title.className = "xpl-title";
  setTextWithArabic(title, note.anchor || note.quote || "Explanation");

  const caret = document.createElement("i");
  caret.className = "fa-solid fa-chevron-down xpl-caret";
  caret.setAttribute("aria-hidden", "true");
  head.append(meta, title);

  // The sentence this card is tied to. Shown whenever it isn't already the
  // title, so a card and a highlight can always be matched up by eye.
  if (note.quote && note.anchor && note.quote !== note.anchor) {
    const quote = document.createElement("span");
    quote.className = "xpl-quote";
    setTextWithArabic(quote, note.quote);
    head.append(quote);
  }
  head.append(caret);

  const preview = document.createElement("p");
  preview.className = "xpl-preview";
  setTextWithArabic(preview, cardPreview(note.body));

  const full = document.createElement("div");
  full.className = "xpl-full";
  const fillFull = (body: string) => {
    full.textContent = "";
    for (const para of cardParagraphs(body)) {
      const p = document.createElement("p");
      // The etymology the Scholar appends is a distinct kind of statement about
      // the passage, so it keeps its own treatment rather than reading as one
      // more paragraph of the explanation.
      if (/^etymology\.\s/i.test(para)) p.className = "xpl-etym";
      setTextWithArabic(p, para);
      full.append(p);
    }
  };
  fillFull(note.body);

  card.append(head, preview, full);

  // ── editing: the Composer's half of the contract ─────────────────────────
  if (opts.onSave || opts.onRemove) {
    const foot = document.createElement("div");
    foot.className = "xpl-foot";
    card.append(foot);

    if (opts.onSave) {
      const form = document.createElement("div");
      form.className = "xpl-edit";

      const titleLabel = document.createElement("label");
      titleLabel.className = "xpl-edit-label";
      titleLabel.textContent = "Title";
      const titleInput = document.createElement("input");
      titleInput.type = "text";
      titleInput.className = "xpl-edit-title";
      titleInput.value = note.anchor ?? "";

      const bodyLabel = document.createElement("label");
      bodyLabel.className = "xpl-edit-label";
      bodyLabel.textContent = "Explanation";
      const bodyInput = document.createElement("textarea");
      bodyInput.className = "xpl-edit-body";
      bodyInput.rows = 12;
      bodyInput.value = note.body;

      titleLabel.append(titleInput);
      bodyLabel.append(bodyInput);

      const actions = document.createElement("div");
      actions.className = "xpl-edit-actions";
      const save = button("xpl-btn xpl-btn--primary", "Save");
      const cancel = button("xpl-btn", "Cancel");
      actions.append(save, cancel);
      form.append(titleLabel, bodyLabel, actions);
      card.insertBefore(form, foot);

      const setEditing = (on: boolean) => {
        card.dataset.editing = String(on);
        if (on) bodyInput.focus();
      };
      setEditing(false);

      const edit = button(
        "xpl-btn",
        "Edit",
        "Change this explanation's title or text",
      );
      edit.addEventListener("click", (e) => {
        e.stopPropagation();
        titleInput.value = note.anchor ?? "";
        bodyInput.value = note.body;
        setEditing(true);
      });
      cancel.addEventListener("click", (e) => {
        e.stopPropagation();
        setEditing(false);
      });
      save.addEventListener("click", async (e) => {
        e.stopPropagation();
        const next = {
          anchor: titleInput.value.trim(),
          body: bodyInput.value.trim(),
        };
        if (!next.body) return; // an empty explanation is a delete, not a save
        save.disabled = true;
        try {
          await opts.onSave?.(note.id, next);
          // Reflect the save immediately. The host re-renders too, but the card
          // must not show stale text for the frame in between.
          note.anchor = next.anchor;
          note.body = next.body;
          setTextWithArabic(title, next.anchor || note.quote || "Explanation");
          setTextWithArabic(preview, cardPreview(next.body));
          fillFull(next.body);
          setEditing(false);
        } finally {
          save.disabled = false;
        }
      });
      foot.append(edit);
    }

    if (opts.onRemove) {
      const remove = button(
        "xpl-btn xpl-btn--danger",
        "Remove",
        "Delete this explanation",
      );
      remove.addEventListener("click", (e) => {
        e.stopPropagation();
        opts.onRemove?.(note.id);
      });
      foot.append(remove);
    }
  }

  const setOpen = (open: boolean) => {
    card.dataset.open = String(open);
    head.setAttribute("aria-expanded", String(open));
    if (!open) card.dataset.editing = "false"; // never leave a hidden edit form open
  };
  setOpen(!!opts.open);

  head.addEventListener("click", () => {
    const open = card.dataset.open !== "true";
    setOpen(open);
    opts.onToggle?.(note.id, open);
    // Expanding a card is also how you ask "where is this in the text?" — so the
    // passage lights and scrolls, and the link runs in both directions.
    opts.onReveal?.(note.id);
  });

  return card;
}
