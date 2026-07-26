/**
 * explanation-card.ts — ONE card for a Companion note, in every surface.
 *
 * The Book Composer's Scholar panel (React) and the LIVE Session reader (plain
 * DOM) show the same notes, so they render them with the same code: a framework-
 * free builder returning an element, mounted directly by the reader and through a
 * container ref by the panel. Two implementations of one card is how the two
 * surfaces would start disagreeing about what a note looks like.
 *
 * The card is COLLAPSED by default: a header naming the passage, and a short
 * opening extract. Clicking the header expands it to the full explanation — an
 * answer can run a thousand words, and a wall of them buries both the chapter you
 * are reading beside it and the other notes on the same page.
 *
 * Arabic inside an explanation is set in the book's own Arabic face at a size
 * that reads as equal to the Latin text around it (Arabic needs the extra size to
 * do that — matched point sizes are not matched legibility). All of it is class
 * names resolved by companion-card.css; nothing here sets a style attribute.
 */
import { sourceProvider, kindDef } from "./registry";

export interface CardNote {
  id: string;
  kind: string;
  body: string;
  /** Card title — the passage this explains, or a theme label. */
  anchor?: string;
  quote?: string;
  source?: { provider: string; label?: string; ref?: string };
}

export interface CardOptions {
  /** Expanded on mount. */
  open?: boolean;
  /** Header clicked: the card wants to expand/collapse. */
  onToggle?: (id: string, open: boolean) => void;
  /** Header clicked: the card wants its passage shown in the prose. */
  onReveal?: (id: string) => void;
  /** Offer a remove control (the Composer does; the read-only reader does not). */
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

/** Build one collapsible explanation card. */
export function renderExplanationCard(
  note: CardNote,
  opts: CardOptions = {},
): HTMLElement {
  const card = document.createElement("article");
  card.className = "xpl";
  card.dataset.note = note.id;

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
  head.append(meta, title, caret);

  const preview = document.createElement("p");
  preview.className = "xpl-preview";
  setTextWithArabic(preview, cardPreview(note.body));

  const full = document.createElement("div");
  full.className = "xpl-full";
  for (const para of cardParagraphs(note.body)) {
    const p = document.createElement("p");
    // The etymology the Scholar appends is a distinct kind of statement about
    // the passage, so it keeps the panel's own treatment rather than reading as
    // one more paragraph of the explanation.
    if (/^etymology\.\s/i.test(para)) p.className = "xpl-etym";
    setTextWithArabic(p, para);
    full.append(p);
  }

  card.append(head, preview, full);

  if (opts.onRemove) {
    const foot = document.createElement("div");
    foot.className = "xpl-foot";
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "xpl-remove";
    remove.textContent = "Remove";
    remove.title = "Delete this explanation";
    remove.addEventListener("click", (e) => {
      e.stopPropagation();
      opts.onRemove?.(note.id);
    });
    foot.append(remove);
    card.append(foot);
  }

  const setOpen = (open: boolean) => {
    card.dataset.open = String(open);
    head.setAttribute("aria-expanded", String(open));
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
