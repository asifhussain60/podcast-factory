/**
 * explanation-card.ts — ONE card for a Companion note, in every surface.
 *
 * The Book Composer's Scholar panel and the LIVE Session reader show the SAME
 * cards: same component, same markdown, same look. The only difference is
 * CAPABILITY. Given `onSave`, an expanded card mounts the repo's own rich-text
 * editor (`@asifhussain/prose-editor`) over the note's markdown and writes on blur;
 * given `onRemove`, it carries a delete button. The reader passes neither, so it
 * renders the same markdown as read-only prose with no controls at all — there is
 * no read-only "mode" to keep in step, only elements that are never built.
 *
 * Framework-free (a builder returning a handle) because one host is React and the
 * other is plain DOM.
 *
 * THE HANDLE MATTERS. A card owns an editor, which owns document listeners and a
 * ProseMirror view; a host that drops the element without calling `destroy` leaks
 * both. `setOpen` exists for the same reason: the panel must be able to expand and
 * collapse a card WITHOUT rebuilding it, because rebuilding is how you destroy the
 * editor a keystroke after the author opened it.
 */
import { mount } from "@asifhussain/prose-editor";
import type { ProseEditor } from "@asifhussain/prose-editor";
import { sourceProvider, kindDef } from "./registry";
import { cardHeadingButtons } from "./card-heading-buttons";
import { cardMarkdownToHtml } from "./card-markdown";

export interface CardNote {
  id: string;
  kind: string;
  /** Markdown. */
  body: string;
  /** Card title — a short theme label for the note. */
  anchor?: string;
  /** The chapter sentence this card explains. */
  quote?: string;
  /** One entry per term. */
  etymology?: string[];
  source?: { provider: string; label?: string; ref?: string };
}

export interface CardEdit {
  anchor: string;
  body: string;
  etymology: string[];
}

export interface CardOptions {
  /** Expanded on mount. */
  open?: boolean;
  onToggle?: (id: string, open: boolean) => void;
  /** The card wants its passage shown in the prose. */
  onReveal?: (id: string) => void;
  /** Editing capability: the expanded card becomes a rich-text editor that saves
   *  on blur. Omitted by the reader. */
  onSave?: (id: string, edit: CardEdit) => Promise<void> | void;
  /** Delete capability: a trash button in the header. Omitted by the reader. */
  onRemove?: (id: string) => void;
}

/** What a host holds onto. */
export interface ExplanationCard {
  el: HTMLElement;
  setOpen(open: boolean): void;
  destroy(): void;
}

/**
 * The toolbar a note needs — one row, no dropdown, nothing the card's markdown
 * cannot round-trip (Asif, 2026-07-26).
 *
 * The heading dropdown is replaced by two toggles rather than dropped: a card can
 * only carry h3 and h4, and removing the control outright would have removed the
 * headings the cards were restructured around. Clear-formatting is gone; with six
 * controls left there is nothing to clear that a second press of the same button
 * does not undo.
 */
const CARD_TOOLBAR = [
  ...cardHeadingButtons(),
  "|",
  "bold",
  "italic",
  "|",
  "bulletList",
  "orderedList",
  "blockquote",
];

/** Arabic script, including the presentation forms an OCR pass can emit. */
const ARABIC_RUN = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿][؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿\sً-ْ]*/g;

/** The one-line gist shown while the card is collapsed. */
export function cardPreview(markdown: string, limit = 150): string {
  const firstProse =
    String(markdown ?? "")
      .split(/\n{2,}/)
      .map((b) => b.trim())
      .find((b) => b && !/^#{1,6}\s/.test(b)) ?? "";
  const flat = firstProse
    .replace(/^\s*[-*]\s+|^\s*\d+[.)]\s+/gm, "")
    .replace(/[*`>]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (flat.length <= limit) return flat;
  return `${flat.slice(0, limit).replace(/\s+\S*$/, "")}…`;
}

/**
 * Fill an element with text, with every Arabic run in its own styled span.
 *
 * Deliberately NOT innerHTML: these are short strings from model output, and the
 * page they land on also hosts the book's prose.
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

function iconButton(
  cls: string,
  icon: string,
  label: string,
): HTMLButtonElement {
  const b = document.createElement("button");
  b.type = "button";
  b.className = cls;
  b.title = label;
  b.setAttribute("aria-label", label);
  const i = document.createElement("i");
  i.className = `fa-solid ${icon}`;
  i.setAttribute("aria-hidden", "true");
  b.append(i);
  return b;
}

/** Build one collapsible explanation card. */
export function renderExplanationCard(
  note: CardNote,
  opts: CardOptions = {},
): ExplanationCard {
  const editable = !!opts.onSave;
  const card = document.createElement("article");
  card.className = "xpl";
  card.dataset.note = note.id;
  if (editable) card.dataset.editable = "true";

  // ── header ───────────────────────────────────────────────────────────────
  const headRow = document.createElement("div");
  headRow.className = "xpl-headrow";
  const head = document.createElement("button");
  head.type = "button";
  head.className = "xpl-head";

  const meta = document.createElement("span");
  meta.className = "xpl-meta";
  const kind = document.createElement("span");
  kind.className = "xpl-kind";
  kind.textContent = kindDef(note.kind).label;
  meta.append(kind);
  if (note.source?.provider) {
    const src = document.createElement("span");
    src.className = "xpl-source";
    src.textContent =
      note.source.label ||
      note.source.ref ||
      sourceProvider(note.source.provider).label;
    meta.append(src);
  }

  const title = document.createElement("span");
  title.className = "xpl-title";
  setTextWithArabic(title, note.anchor || note.quote || "Explanation");

  const caret = document.createElement("i");
  caret.className = "fa-solid fa-chevron-down xpl-caret";
  caret.setAttribute("aria-hidden", "true");
  head.append(meta, title);

  // The sentence this card is tied to, so a card and a highlight can be matched
  // up by eye.
  if (note.quote && note.anchor && note.quote !== note.anchor) {
    const quote = document.createElement("span");
    quote.className = "xpl-quote";
    setTextWithArabic(quote, note.quote);
    head.append(quote);
  }
  head.append(caret);
  headRow.append(head);
  if (opts.onRemove) {
    const del = iconButton(
      "xpl-del",
      "fa-trash-can",
      "Delete this explanation",
    );
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      opts.onRemove?.(note.id);
    });
    headRow.append(del);
  }

  const preview = document.createElement("p");
  preview.className = "xpl-preview";
  setTextWithArabic(preview, cardPreview(note.body));

  // ── body: rendered prose (reader) or the editor's host (Composer) ────────
  const bodyEl = document.createElement("div");
  bodyEl.className = "xpl-full";
  if (!editable)
    bodyEl.innerHTML = cardMarkdownToHtml(note.body, { arabicSpans: true });

  const status = document.createElement("span");
  status.className = "xpl-status";
  status.setAttribute("aria-live", "polite");

  // ── etymology: discrete items, curated one at a time ─────────────────────
  let items = [...(note.etymology ?? [])];
  const etym = document.createElement("div");
  etym.className = "xpl-etym";

  const renderEtymology = () => {
    etym.textContent = "";
    if (!items.length && !editable) return;
    const label = document.createElement("p");
    label.className = "xpl-etym-label";
    label.textContent = "Etymology";
    etym.append(label);
    items.forEach((item, i) => {
      const row = document.createElement("div");
      row.className = "xpl-etym-item";
      if (editable) {
        const field = document.createElement("textarea");
        field.className = "xpl-etym-text";
        field.rows = 2;
        field.value = item;
        field.setAttribute("aria-label", `Etymology entry ${i + 1}`);
        field.addEventListener("blur", () => {
          const next = field.value.trim();
          if (next === items[i]) return;
          items[i] = next;
          void save();
        });
        row.append(field);
        const del = iconButton(
          "xpl-etym-del",
          "fa-xmark",
          "Delete this etymology entry",
        );
        del.addEventListener("click", () => {
          items.splice(i, 1);
          renderEtymology();
          void save();
        });
        row.append(del);
      } else {
        const p = document.createElement("p");
        p.className = "xpl-etym-text";
        setTextWithArabic(p, item);
        row.append(p);
      }
      etym.append(row);
    });
    if (editable) {
      const add = document.createElement("button");
      add.type = "button";
      add.className = "xpl-etym-add";
      add.textContent = "+ Add etymology";
      add.addEventListener("click", () => {
        items.push("");
        renderEtymology();
        etym
          .querySelector<HTMLTextAreaElement>(
            ".xpl-etym-item:last-of-type .xpl-etym-text",
          )
          ?.focus();
      });
      etym.append(add);
    }
  };
  renderEtymology();

  card.append(headRow, preview, bodyEl, etym, status);

  // ── the editor, and the one thing it must never do ───────────────────────
  let editor: ProseEditor | null = null;
  let savedBody = note.body;
  // The title is the passage label, set when the note was filed; the card does not
  // edit it, so it is carried through the save unchanged rather than dropped.
  const savedAnchor = note.anchor ?? "";
  let flashTimer = 0;

  const flash = (text: string) => {
    status.textContent = text;
    window.clearTimeout(flashTimer);
    if (text)
      flashTimer = window.setTimeout(() => (status.textContent = ""), 1600);
  };

  async function save(): Promise<void> {
    if (!opts.onSave) return;
    const body = (editor ? editor.serialize() : savedBody).trim();
    const anchor = savedAnchor.trim();
    const cleaned = items.map((i) => i.trim()).filter(Boolean);
    const unchanged =
      body === savedBody.trim() &&
      anchor === (note.anchor ?? "").trim() &&
      cleaned.join(" ") === (note.etymology ?? []).join(" ");
    if (unchanged) return;
    if (!body) {
      // An emptied explanation is a delete, and deleting has its own button.
      if (editor)
        editor.editor.commands.setContent(
          cardMarkdownToHtml(savedBody, { arabicSpans: false }),
        );
      return;
    }
    flash("Saving…");
    try {
      await opts.onSave(note.id, { anchor, body, etymology: cleaned });
      savedBody = body;
      note.body = body;
      note.anchor = anchor;
      note.etymology = cleaned;
      items = [...cleaned];
      setTextWithArabic(preview, cardPreview(body));
      flash("Saved");
    } catch {
      flash("Not saved — try again");
    }
  }

  /** Mount the editor the first time the card is opened, never before. */
  function ensureEditor(): void {
    if (editor || !editable) return;
    bodyEl.textContent = "";
    // The editor owns its own host element so the toolbar can be placed ABOVE it
    // — mount() hands the toolbar back rather than positioning it, on purpose.
    const host = document.createElement("div");
    bodyEl.append(host);
    editor = mount(host, {
      content: cardMarkdownToHtml(note.body, { arabicSpans: false }),
      serializer: { kind: "markdown" },
      toolbar: {
        items: CARD_TOOLBAR,
        ariaLabel: "Formatting",
        // One row: no overflow menu to fold controls into, and the CSS keeps
        // them from wrapping.
        overflow: "none",
        // The package's OWN prefix, deliberately: its stylesheet dresses `.rte-*`
        // and the Composer's theme adapter already aliases those onto the site's
        // tokens. A private prefix here would ship an unstyled toolbar.
      },
      editorAttributes: { class: "rte-prose xpl-prose" },
    });
    if (editor.toolbarEl) bodyEl.prepend(editor.toolbarEl);
  }

  // Save when focus leaves the CARD — not on any blur. The toolbar lives inside
  // the card, so a plain blur handler would fire (and save) between clicking Bold
  // and the command running.
  card.addEventListener("focusout", (e) => {
    const next = (e as FocusEvent).relatedTarget as Node | null;
    if (next && card.contains(next)) return;
    void save();
  });

  const setOpen = (open: boolean) => {
    card.dataset.open = String(open);
    head.setAttribute("aria-expanded", String(open));
    if (open) ensureEditor();
  };
  setOpen(!!opts.open);

  head.addEventListener("click", () => {
    const open = card.dataset.open !== "true";
    setOpen(open);
    opts.onToggle?.(note.id, open);
    // Expanding a card is also how you ask "where is this in the text?"
    opts.onReveal?.(note.id);
  });

  return {
    el: card,
    setOpen,
    destroy() {
      window.clearTimeout(flashTimer);
      editor?.destroy();
      editor = null;
    },
  };
}
