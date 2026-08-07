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
import { confirmDialog } from "../../../scripts/confirm-dialog";
import { sourceProvider, kindDef } from "./registry";
import type { EtymologyMorphology } from "./types";
import { cardHeadingButtons } from "./card-heading-buttons";
import { cardMarkdownToHtml } from "./card-markdown";
import { PANEL_TEXT_SIZE_EVENT } from "../../../scripts/panel-text-size";

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
  /** Verified corpus block per etymology row, index-aligned; null = the corpus
   *  declined and the row renders exactly as before. Server-computed only. */
  morphology?: (EtymologyMorphology | null)[];
  source?: { provider: string; label?: string; ref?: string };
  /** Absent = kept. Only `"proposed"` renders the badge and the keep button. */
  review?: "proposed" | "kept";
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
  /** Accept capability: a keep button, shown ONLY on a note still marked
   *  `review: "proposed"`. Omitted by the reader, like the two above — a reading
   *  pass judges nothing. */
  onAccept?: (id: string) => void;
}

/** What a host holds onto. */
export interface ExplanationCard {
  el: HTMLElement;
  setOpen(open: boolean): void;
  /** "The passage this card explains is on screen right now." A presentation
   *  state, kept SEPARATE from open/shut: the Composer drives both from the
   *  scroll position, and a card can be lit while its own expand animation is
   *  still settling. The class is all it is — companion-card.css owns the glow. */
  setInView(on: boolean): void;
  /** "This note has been accepted." Drops the Unreviewed badge and the tick.
   *  Same reason `setOpen` exists — a reused card has to be TOLD what changed,
   *  and rebuilding it to show one badge less would destroy its open editor. */
  markKept(): void;
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
  // A note the machine filed and nobody has read yet says so, ON THE CARD.
  // Without this the whole set reads as approved the moment it is written, which
  // is the failure that withdrew automatic authoring on 2026-08-02: a hundred
  // explanations no human had looked at, indistinguishable from his own.
  // ABSENT `review` means kept, so every note written before today and every
  // note he types himself is unmarked — the badge appears only where it is true.
  // Held rather than dropped: `markKept` below removes it, and it cannot remove
  // an element it never had a reference to.
  let proposedFlag: HTMLElement | null = null;
  if (note.review === "proposed") {
    proposedFlag = document.createElement("span");
    proposedFlag.className = "xpl-proposed";
    proposedFlag.textContent = "Unreviewed";
    meta.append(proposedFlag);
  }

  // ONE identifier, not two. The panel titles a filed note with a truncation of
  // its own passage, so title and quote were the same sentence printed twice —
  // three wrapped lines of header before a word of explanation. When the anchor is
  // just the passage cut short, the passage IS the title.
  const anchorIsQuote =
    !!note.quote &&
    !!note.anchor &&
    note.quote.startsWith(note.anchor.replace(/…$/, "").trim());
  const title = document.createElement("span");
  title.className = "xpl-title";
  setTextWithArabic(title, note.anchor || note.quote || "Explanation");

  const caret = document.createElement("i");
  caret.className = "fa-solid fa-chevron-down xpl-caret";
  caret.setAttribute("aria-hidden", "true");
  head.append(meta, title);

  // The sentence this card is tied to, so a card and a highlight can be matched
  // up by eye — shown only when it says something the title does not.
  if (note.quote && note.anchor && !anchorIsQuote) {
    const quote = document.createElement("span");
    quote.className = "xpl-quote";
    setTextWithArabic(quote, note.quote);
    head.append(quote);
  }
  head.append(caret);
  headRow.append(head);

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
  // Index-aligned with `items`. Spliced on delete, nulled when a row's text is
  // edited (the term may have changed — decline until the next server read
  // re-resolves), and padded with null on add.
  const morphs: (EtymologyMorphology | null)[] = items.map(
    (_, i) => note.morphology?.[i] ?? null,
  );
  const etym = document.createElement("div");
  etym.className = "xpl-etym";

  /**
   * The TERM an entry is about, for the accordion's header.
   *
   * The persona writes "برهان (proof): from the root…", so the term is what
   * precedes the first colon. Older entries are free prose, so fall back to the
   * first Arabic run — which is what the reader is scanning the list for anyway —
   * and to the opening words only if there is no script at all.
   */
  const etymologyTerm = (item: string): string => {
    const colon = item.match(/^\s*([^:\n]{1,60}?)\s*:\s+/);
    if (colon) return colon[1].trim();
    const arabic = item.match(ARABIC_RUN)?.[0]?.trim();
    if (arabic) return arabic;
    const words = item.split(/\s+/).slice(0, 4).join(" ");
    return words || "Etymology";
  };

  /** The explanation minus its leading term, so the body does not repeat the
   *  header. Kept intact when there is no term to strip. */
  const etymologyDetail = (item: string): string =>
    item.replace(/^\s*[^:\n]{1,60}?\s*:\s+/, "").trim() || item;

  /**
   * Grow an entry's field to its whole content.
   *
   * A textarea has a fixed intrinsic height and scrolls whatever overflows it,
   * which put a scrollbar inside a card that is itself inside a scrolling panel
   * — two nested scrolls over one paragraph, and the end of an explanation
   * hidden behind the second. The card is what grows now; the panel is the only
   * thing that scrolls (`overflow-y: hidden` on the field enforces the other
   * half). `height: auto` first, because scrollHeight of an already-grown field
   * reports the height it was last given, never a smaller one, so deleting text
   * would leave the field stuck at its high-water mark.
   *
   * The border has to be added back by hand. `scrollHeight` counts content and
   * padding but NOT border, while under `box-sizing: border-box` the `height`
   * being set INCLUDES it — so assigning scrollHeight directly leaves the field
   * exactly its border short and quietly scrolling by that much. Two pixels,
   * and enough to keep the last line clipped.
   *
   * REFUSING to measure a hidden field is the other half of the contract. An
   * element inside a `display:none` ancestor reports `scrollHeight` 0, and
   * writing that back pins the field at its minimum — so a window resize while
   * the card was collapsed used to leave the entry permanently short on the
   * next expand. With no scrollbar and no resize grip there is no way back from
   * a bad measurement, so the only safe move is not to record one.
   */
  const autoSizeEntry = (field: HTMLTextAreaElement): void => {
    if (field.offsetParent === null) return; // hidden — measures 0, would clamp
    field.style.setProperty("--ety-h", "auto");
    const cs = getComputedStyle(field);
    const border =
      cs.boxSizing === "border-box"
        ? (parseFloat(cs.borderTopWidth) || 0) +
          (parseFloat(cs.borderBottomWidth) || 0)
        : 0;
    field.style.setProperty("--ety-h", `${field.scrollHeight + border}px`);
  };

  /** Shut every entry, so opening one cannot leave two open. */
  const closeAllEntries = (): void => {
    etym
      .querySelectorAll<HTMLElement>('.xpl-ety[data-open="true"]')
      .forEach((other) => {
        other.dataset.open = "false";
        other
          .querySelector(".xpl-ety-head")
          ?.setAttribute("aria-expanded", "false");
      });
  };

  /** Re-measure the open entry. Only one is ever open and the rest are
   *  display:none, so this is a single measurement however many terms there are. */
  const resizeOpenEntry = (): void => {
    const field = etym.querySelector<HTMLTextAreaElement>(
      '.xpl-ety[data-open="true"] textarea.xpl-ety-text',
    );
    if (field) autoSizeEntry(field);
  };

  // A width change re-wraps the text, so a height measured at the old width is
  // wrong. An observer on the container catches every cause of that — a window
  // resize, the drawer being dragged, a layout shift beside it — where a window
  // listener caught only the first. Guarded on WIDTH: this callback's own work
  // changes the container's HEIGHT, and reacting to that would loop.
  let observedWidth = 0;
  let resizeFrame = 0;
  const widthObserver = new ResizeObserver((entries) => {
    const width = entries[0]?.contentRect.width ?? 0;
    if (width === 0 || Math.abs(width - observedWidth) < 1) return;
    observedWidth = width;
    // Measured on the NEXT frame, not in the callback. The width guard stops
    // this observer acting on its own output, but it cannot stop the browser
    // NOTICING it: autoSizeEntry resizes an element inside the observed
    // container, so the observation is still dirty when the callback returns,
    // and Chrome reports that on `window` as "ResizeObserver loop completed
    // with undelivered notifications" — once per width change, on every crossing
    // of the mobile breakpoint. Deferring one frame ends the callback with the
    // layout untouched. Coalesced, because a drag emits a width per frame and
    // only the last one is worth measuring.
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(resizeOpenEntry);
  });
  widthObserver.observe(etym);

  // Text size is the input a resize observer cannot see: the box keeps its
  // width while the text inside it reflows to a different number of lines. The
  // shared stepper announces itself for exactly this (see panel-text-size).
  window.addEventListener(PANEL_TEXT_SIZE_EVENT, resizeOpenEntry);

  const renderEtymology = () => {
    etym.textContent = "";
    if (!items.length && !editable) return;
    const label = document.createElement("p");
    label.className = "xpl-etym-label";
    label.textContent = "Etymology";
    etym.append(label);

    items.forEach((item, i) => {
      // One accordion per term: the word in the header, the whole explanation
      // when it is open. A list of five terms is then five lines you can scan,
      // rather than five paragraphs you have to read past.
      const row = document.createElement("article");
      row.className = "xpl-ety";
      row.dataset.open = "false";

      const head = document.createElement("button");
      head.type = "button";
      head.className = "xpl-ety-head";
      head.setAttribute("aria-expanded", "false");
      const term = document.createElement("span");
      term.className = "xpl-ety-term";
      setTextWithArabic(term, etymologyTerm(item));
      const caret = document.createElement("i");
      caret.className = "fa-solid fa-chevron-down xpl-ety-caret";
      caret.setAttribute("aria-hidden", "true");
      head.append(term, caret);
      head.addEventListener("click", () => {
        const open = row.dataset.open !== "true";
        // One entry at a time. Five open entries is the wall of prose the
        // accordion exists to prevent, and with the fields now grown to their
        // full content it would be a very tall one.
        if (open) closeAllEntries();
        row.dataset.open = String(open);
        head.setAttribute("aria-expanded", String(open));
        if (open) {
          const field = row.querySelector<HTMLTextAreaElement>(
            "textarea.xpl-ety-text",
          );
          // Sizing has to happen HERE rather than at build time: the body is
          // display:none while shut, and a hidden element reports scrollHeight 0.
          if (field) autoSizeEntry(field);
          if (editable) field?.focus();
        }
      });
      row.append(head);

      const body = document.createElement("div");
      body.className = "xpl-ety-body";
      // The VERIFIED half first: root, real derived family, Lane's meaning —
      // straight from the committed morphology corpus, so no disclaimer applies
      // to this block. Read-only in both surfaces (facts are not editable); the
      // persona's interpretive text keeps the textarea below.
      const morph = morphs[i];
      if (morph) {
        const v = document.createElement("div");
        v.className = "xpl-morph";
        const rootLine = document.createElement("p");
        rootLine.className = "xpl-morph-root";
        setTextWithArabic(
          rootLine,
          `Root ${morph.root_dashed} — ${morph.occurrences}× in the Quran, ${morph.lemma_count} derived words`,
        );
        v.append(rootLine);
        const fam = document.createElement("p");
        fam.className = "xpl-morph-family";
        for (const lem of morph.family.slice(0, 8)) {
          const chip = document.createElement("span");
          chip.className = "xpl-morph-chip";
          setTextWithArabic(chip, `${lem.lemma_ar} ${lem.occurrence_count}×`);
          if (lem.first_location)
            chip.title = `first at ${lem.first_location}${lem.pos ? ` · ${lem.pos}` : ""}`;
          fam.append(chip);
        }
        v.append(fam);
        if (morph.lane_en) {
          const lane = document.createElement("p");
          lane.className = "xpl-morph-lane";
          setTextWithArabic(lane, morph.lane_en);
          v.append(lane);
        }
        const src = document.createElement("p");
        src.className = "xpl-morph-src";
        src.textContent = morph.lane_en
          ? "Quranic Arabic Corpus · Lane's Lexicon"
          : "Quranic Arabic Corpus";
        v.append(src);
        body.append(v);
      }
      if (editable) {
        const field = document.createElement("textarea");
        field.className = "xpl-ety-text";
        field.rows = 1; // the real height comes from autoSizeEntry, not from rows
        field.value = item;
        field.setAttribute("aria-label", `Etymology entry ${i + 1}`);
        field.addEventListener("input", () => autoSizeEntry(field));
        field.addEventListener("blur", () => {
          const next = field.value.trim();
          if (next === items[i]) return;
          items[i] = next;
          // The term may have changed — the old verified block no longer
          // provably belongs to this row. Decline until the next server read.
          morphs[i] = null;
          setTextWithArabic(term, etymologyTerm(next));
          void save();
        });
        body.append(field);
      } else {
        const p = document.createElement("p");
        p.className = "xpl-ety-text";
        setTextWithArabic(p, etymologyDetail(item));
        body.append(p);
      }
      row.append(body);

      if (editable) {
        // Hovering over the card rather than sitting in the row: the entry gets
        // the full width, and delete is reachable without opening the entry.
        const del = iconButton(
          "xpl-ety-del",
          "fa-trash-can",
          "Delete this etymology entry",
        );
        del.addEventListener("click", (e) => {
          e.stopPropagation();
          // Confirmed first (Asif, 2026-07-28): a slip of the mouse must not
          // discard an entry. Same themed dialog as every destructive action
          // in the Composer; delete only exists there, where its CSS lives.
          void confirmDialog({
            title: "Delete this etymology entry?",
            body: etymologyTerm(items[i]),
            confirmLabel: "Delete",
            danger: true,
            titleIcon: "fa-solid fa-trash-can",
          }).then((ok) => {
            if (!ok) return;
            items.splice(i, 1);
            morphs.splice(i, 1);
            renderEtymology();
            void save();
          });
        });
        row.append(del);
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
        morphs.push(null);
        renderEtymology();
        const last = etym.querySelector<HTMLElement>(".xpl-ety:last-of-type");
        last?.querySelector<HTMLButtonElement>(".xpl-ety-head")?.click();
      });
      etym.append(add);
    }
  };
  renderEtymology();

  card.append(headRow, preview, bodyEl, etym, status);

  // Delete HOVERS over the card rather than sitting in the header row. In the row
  // it took a fixed column out of the panel's width for a control used once in a
  // card's life, and the header — which carries the sentence this card is about —
  // wrapped to three lines to make room for it. Now the header has the full width
  // and delete appears on hover, in the corner, over the content it removes.
  if (opts.onRemove) {
    const del = iconButton(
      "xpl-del",
      "fa-trash-can",
      "Delete this explanation",
    );
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      // Confirmed first (Asif, 2026-07-28), through the Composer's own themed
      // dialog: the note holds an AI answer that cannot be regenerated
      // verbatim, and the button sits a hover away from the reading flow.
      void confirmDialog({
        title: "Delete this explanation?",
        body: note.anchor || note.quote || "This explanation",
        confirmLabel: "Delete",
        danger: true,
        titleIcon: "fa-solid fa-trash-can",
      }).then((ok) => {
        if (ok) opts.onRemove?.(note.id);
      });
    });
    card.append(del);
  }

  // Accept — the other half of accept-or-delete, and it exists ONLY while there
  // is something to accept. Sits beside delete, unconfirmed: keeping a note is
  // reversible (delete is still there) and a dialog on a reversible act that may
  // be used thirty times in one pass is friction, not safety. Requires onSave
  // for the same reason delete requires onRemove — a reading pass mounts neither.
  let keepBtn: HTMLElement | null = null;
  if (note.review === "proposed" && opts.onAccept) {
    keepBtn = iconButton("xpl-keep", "fa-check", "Keep this explanation");
    keepBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      opts.onAccept?.(note.id);
    });
    card.append(keepBtn);
  }

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
      cleaned.join("\0") === (note.etymology ?? []).join("\0");
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
    if (open) {
      ensureEditor();
      // The etymology block is display:none while the CARD is shut, so any
      // measurement attempted in that window was refused. This is the first
      // moment an open entry can be measured again.
      resizeOpenEntry();
    }
  };
  setOpen(!!opts.open);

  /**
   * The note has been accepted — drop the badge and the tick.
   *
   * A card is REUSED across renders, deliberately: rebuilding it destroys the
   * editor a keystroke after the author opened it. The cost is that a card built
   * from a "proposed" note keeps showing "Unreviewed" and its tick after the note
   * is accepted, because nothing ever told it otherwise. That is what pressing
   * the tick looked like from the outside: the write landed, the file said
   * "kept", and the card was unchanged (2026-08-06).
   *
   * Only this direction exists. The API refuses any `review` but "kept" — going
   * back to unreviewed is the filing pass's to set, never a person's — so a
   * `setReview` taking either value would offer a transition nothing can make.
   * Idempotent, so the panel may call it on every render.
   */
  function markKept(): void {
    proposedFlag?.remove();
    proposedFlag = null;
    keepBtn?.remove();
    keepBtn = null;
  }

  head.addEventListener("click", () => {
    const open = card.dataset.open !== "true";
    setOpen(open);
    opts.onToggle?.(note.id, open);
    // Expanding a card is also how you ask "where is this in the text?"
    opts.onReveal?.(note.id);
  });

  // A SHUT card opens from a click anywhere on it, not just the header strip —
  // collapsed it is one preview line, and the whole line reads as the target
  // (Asif, 2026-07-28). Open-only on purpose: an expanded card holds a live
  // editor and etymology fields, where a click means "put the caret here",
  // never "collapse what I'm reading". Collapse stays on the header, whose own
  // listener above also handles clicks that land on it while shut.
  card.addEventListener("click", (e) => {
    if (card.dataset.open === "true") return;
    const target = e.target as HTMLElement;
    if (target.closest(".xpl-head, .xpl-del, button, a")) return;
    setOpen(true);
    opts.onToggle?.(note.id, true);
    opts.onReveal?.(note.id);
  });

  return {
    el: card,
    setOpen,
    setInView(on: boolean) {
      card.classList.toggle("is-inview", on);
    },
    markKept,
    destroy() {
      window.clearTimeout(flashTimer);
      widthObserver.disconnect();
      // Disconnecting stops new callbacks but not one already queued for the
      // next frame, which would measure a card that is on its way out.
      cancelAnimationFrame(resizeFrame);
      window.removeEventListener(PANEL_TEXT_SIZE_EVENT, resizeOpenEntry);
      editor?.destroy();
      editor = null;
    },
  };
}
