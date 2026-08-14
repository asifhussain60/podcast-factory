/**
 * compose-quote-kind-command.ts — the Composer's quote-kind dropdown.
 *
 * Registered through the editor package's extension point, like the alignment
 * and colour controls beside it. Requested 2026-08-14: the same three-way
 * declaration (Saying / Verse / Prophetic tradition) already lived as three
 * buttons under the right panel's "Reshape now" tab, reachable only by
 * scrolling there or remembering the ⌥⌘4/5/6 shortcuts — this puts the same
 * declaration one click away in the bar itself, for the person who wants it
 * without leaving the toolbar.
 *
 * It does NOT duplicate the write path. `onApply` is the host's existing
 * `runSetQuoteKind`, the same function the three buttons already call — one
 * function decides how a kind reaches `_system/quote-kind.json`, this is a
 * second door onto it, never a second implementation.
 *
 * `current` is honest about what it cannot know: unlike alignment or colour,
 * this repo keeps no live "kind of the selection" index on the client, only
 * the DOM class (`k-quote`/`k-poem`/`k-hadith`) an already-declared blockquote
 * carries. The host's `getActive` hook walks the ProseMirror tree for that
 * class; returning null (cursor outside any declared blockquote) falls back
 * to the first option — deliberately labelled "Default card" rather than
 * silently showing "Saying" as if that were the true state, which the
 * package's own dropdown does for any unmatched id.
 *
 * CLICK-TO-TARGET (2026-08-14). The original three-button panel required a
 * real drag-selected range of text — `selectionText()` on the host — because
 * that was the only way it had to answer "which quotation." Reported live:
 * a person places the cursor inside an already-rendered card (a single
 * click, no drag) and picks a kind, and nothing saves — `selectionText()`
 * sees a collapsed cursor, which is empty, which the guard correctly refuses
 * as "nothing to declare." That refusal was correct given what it had to
 * work with; the fix is giving it more to work with. `resolveQuoteTarget`
 * below is the same "walk up to the nearest blockquote" `getActive` already
 * does, generalized: given a REAL selection, use exactly that text (nothing
 * about the drag-select workflow changes for anyone relying on it); given a
 * collapsed cursor, fall back to the FULL TEXT of the blockquote it sits in,
 * so a single click anywhere on a card is enough to re-target it. A
 * collapsed cursor outside any blockquote still resolves to nothing — there
 * is no card to swap.
 *
 * LIVE REPAINT (2026-08-14, same day). Declaring a kind wrote the file
 * correctly from the very first version of this dropdown — the status line
 * said so ("Marked as Prophetic tradition. Switch to Read to see the
 * card.") — but the card sitting right under the cursor kept showing its
 * OLD label and colour until a reload, because the label the edit canvas
 * paints (`data-q-label`, read by a CSS `::before` in book-composer.css) is
 * a ProseMirror node attribute baked in ONCE, at page load, from whatever
 * `_system/quote-kind.json` said back then. A save that only reaches the
 * file leaves that attribute stale. `nextCardAttrs` computes what the
 * attribute SHOULD become for a given kind, purely (no editor needed, so it
 * is the one piece of this fix a test can check without mounting a live
 * document); `repaintQuoteCard` is the thin wrapper that actually writes it
 * into the open document the moment the save succeeds — no reload, no
 * switch to Read.
 */
import { defineDropdown } from "@asifhussain/prose-editor";
import type { RegisteredDropdown } from "@asifhussain/prose-editor";
import type { Editor } from "@tiptap/core";
import type { Node as PMNode } from "@tiptap/pm/model";

export type QuoteKindId = "" | "quote" | "poem" | "hadith";

/** A COPY of the same mapping in book-composer.ts and markdown.ts, not an
 *  import — markdown.ts's own comment on its copy explains why: three
 *  independent browser bundles, one intentionally duplicated constant,
 *  rather than an import path that would either reach into a different
 *  bundle's internals or risk pulling something server-only along with it.
 *  A drift here is a display bug, not silent data corruption — the write
 *  path (`onApply`) never touches this map at all. */
const QUOTE_KIND_LABEL: Record<Exclude<QuoteKindId, "">, string> = {
  quote: "Saying",
  poem: "Verse",
  hadith: "Prophetic tradition",
};

/** The four class tokens a blockquote can carry to mark WHO declared it —
 *  `k-quran` included even though this dropdown never sets it, because a
 *  repaint must still know to remove a stale one if a person later
 *  re-declares an auto-detected Qur'an passage as something else. */
const KIND_CLASS_TOKENS = ["k-quran", "k-hadith", "k-poem", "k-quote"];

export interface QuoteKindHooks {
  /** Declare the current target's kind — the same guard-and-write path the
   *  three panel buttons use. The target is resolved by `resolveQuoteTarget`
   *  (a real selection if there is one, otherwise the enclosing card); an
   *  unresolvable target declares nothing and reports why, never a silent
   *  no-op. */
  onApply: (kind: QuoteKindId) => void;
  /** The kind of the blockquote the cursor sits in, or null when the cursor
   *  is not in one, the block has no declaration, or the block is Qur'an
   *  (auto-detected — not a kind this dropdown can set). */
  getActive: () => QuoteKindId | null;
}

export interface QuoteTarget {
  /** The full text a declaration would be about. */
  text: string;
  /** The trimmed first non-blank line of `text` — the key `_system/quote-
   *  kind.json` and every renderer's `quoteKindKey` look declarations up by.
   *  Computed here, once, so the host and any future caller cannot compute
   *  it two different ways. */
  firstLine: string;
  /** The document position of the enclosing blockquote's OWN node — where
   *  `doc.nodeAt(blockquotePos)` returns the blockquote itself — so a
   *  successful declare can repaint that exact card. Null when the target
   *  has no enclosing blockquote at all (a plain paragraph selection: the
   *  declaration still writes, there is simply no card on screen to
   *  repaint until that text becomes a blockquote some other way). */
  blockquotePos: number | null;
}

/** The position + node of the nearest ANCESTOR blockquote containing
 *  `doc.resolve(pos)`, or null. Shared by `resolveQuoteTarget` (to report
 *  where a repaint should land) and `getActive` on the host (to read what
 *  kind is already there) — both are "walk up from here to the nearest
 *  blockquote," so this is the one place that walk is written. */
export function enclosingBlockquote(
  doc: PMNode,
  pos: number,
): { pos: number; node: PMNode } | null {
  const $pos = doc.resolve(pos);
  for (let d = $pos.depth; d >= 0; d--) {
    const node = $pos.node(d);
    if (node.type.name === "blockquote") return { pos: $pos.before(d), node };
  }
  return null;
}

/** The first non-blank, trimmed line of a block of text, or "" for a block
 *  that is all whitespace. Mirrors `quoteKindKey` in quote-kind.mjs, which
 *  takes the same "first line, trimmed" of whatever text it is handed. */
function firstLineOf(text: string): string {
  for (const line of text.split("\n")) {
    const t = line.trim();
    if (t) return t;
  }
  return "";
}

/**
 * What a quote-kind declaration should act on, given the document and the
 * current selection's `from`/`to` (equal when the selection is collapsed —
 * a plain cursor, not a drag-selected range).
 *
 * A real (non-collapsed) selection wins outright: its exact text is the
 * target, unchanged from how the three-button panel has always worked, so a
 * person who intentionally selects PART of a longer passage still declares
 * only that part.
 *
 * A collapsed cursor resolves to the nearest ANCESTOR blockquote's full
 * text — not a sibling, not the whole chapter — so clicking once inside a
 * rendered card targets that card and nothing else. A cursor collapsed
 * outside any blockquote (a plain paragraph, a heading) resolves to null:
 * there is no card there to swap, and guessing one would silently declare a
 * kind for a passage nobody asked to mark.
 *
 * A resolved target whose text is empty (a blockquote parsed with no
 * content, an edge case rather than a real quotation) also returns null —
 * an empty firstLine can never match anything a renderer looks up.
 *
 * FIRSTLINE, FOR A CARD WITH MORE THAN ONE PARAGRAPH INSIDE — e.g. an
 * Arabic line over its own English translation, two separate paragraph
 * nodes in one blockquote. `quoteKindKey` in quote-kind.mjs keys on the
 * quotation's own FIRST paragraph, given as one array entry per paragraph —
 * never a string it has to split. `node.textContent` flattens every child
 * paragraph together with NO separator at all (confirmed live: two
 * paragraphs "Arabic line." and "Translation." concatenate to
 * "Arabic line.Translation.", not even a space), so splitting THAT on `\n`
 * would never find the boundary and would key the whole card under one
 * run-on string no declaration could ever match. The fix reads the
 * blockquote's OWN first child node directly — the same "first paragraph,
 * verbatim" `quoteKindKey` already expects — rather than trying to recover
 * a paragraph boundary from text that no longer carries one.
 */
export function resolveQuoteTarget(
  doc: PMNode,
  from: number,
  to: number,
): QuoteTarget | null {
  if (from !== to) {
    const text = doc.textBetween(from, to, " ").trim();
    if (!text) return null;
    const enclosing = enclosingBlockquote(doc, from);
    return {
      text,
      firstLine: firstLineOf(text),
      blockquotePos: enclosing?.pos ?? null,
    };
  }
  const enclosing = enclosingBlockquote(doc, from);
  if (!enclosing) return null;
  const { pos, node } = enclosing;
  const text = node.textBetween(0, node.content.size, " ").trim();
  if (!text) return null;
  const firstParagraph = node.maybeChild(0)?.textContent.trim();
  return {
    text,
    firstLine: firstParagraph || firstLineOf(text),
    blockquotePos: pos,
  };
}

export interface CardAttrs {
  class: string | null;
  "data-q-label": string | null;
}

/**
 * What a blockquote's `class` and `data-q-label` attributes SHOULD become
 * for a given declared kind, given whatever the node's `class` attribute
 * currently is. Pure — no editor, no document, just strings — so this is
 * checkable without mounting a live ProseMirror view.
 *
 * Strips every existing `k-*` token before adding the new one: a card can
 * carry exactly one declared kind, never two stale tokens stacked from an
 * earlier declaration. Every OTHER class survives untouched (`quran`,
 * `is-quranic`, whatever else the block carries) — this repaints WHAT KIND
 * a person declared, not the auto-detected provenance underneath it.
 */
export function nextCardAttrs(
  currentClass: unknown,
  kind: QuoteKindId,
): CardAttrs {
  const kept = String(currentClass ?? "")
    .split(/\s+/)
    .filter(Boolean)
    .filter((c) => !KIND_CLASS_TOKENS.includes(c));
  const classes = kind ? [...kept, `k-${kind}`] : kept;
  return {
    class: classes.length ? classes.join(" ") : null,
    "data-q-label": kind ? QUOTE_KIND_LABEL[kind] : null,
  };
}

/**
 * Write `nextCardAttrs` straight into the OPEN document at `blockquotePos`
 * — the repaint itself. A no-op, deliberately quiet, if that position no
 * longer holds a blockquote (the document changed between resolving the
 * target and the save completing) rather than throwing mid-save; the file
 * write already succeeded by the time this runs, so a skipped repaint costs
 * a stale label until the next reload, never a corrupted document.
 */
export function repaintQuoteCard(
  editor: Editor,
  blockquotePos: number,
  kind: QuoteKindId,
): void {
  const node = editor.state.doc.nodeAt(blockquotePos);
  if (!node || node.type.name !== "blockquote") return;
  const attrs = nextCardAttrs(node.attrs.class, kind);
  editor.view.dispatch(
    editor.state.tr.setNodeMarkup(blockquotePos, undefined, {
      ...node.attrs,
      ...attrs,
    }),
  );
}

/** id "" is deliberately first: it is the fallback label the dropdown shows
 *  whenever `getActive` returns null, so that fallback reads as "nothing
 *  declared here" rather than naming a specific kind that is not, in fact,
 *  the state. Clicking it clears a declaration back to the default card,
 *  the one action the three-button panel has no way to do at all. */
const OPTIONS = [
  { id: "", label: "Default card" },
  { id: "quote", label: "Saying" },
  { id: "poem", label: "Verse" },
  { id: "hadith", label: "Prophetic tradition" },
] as const;

export function quoteKindDropdown(hooks: QuoteKindHooks): RegisteredDropdown {
  return defineDropdown({
    id: "quoteKind",
    label: "Quote kind",
    tooltip:
      "Select a quotation, then declare what it is — Saying, Verse, or Prophetic tradition.",
    priority: 52,
    options: OPTIONS,
    current: () => hooks.getActive(),
    run: (_api, optionId) => hooks.onApply(optionId as QuoteKindId),
  });
}
