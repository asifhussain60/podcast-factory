/**
 * GemCompanionPanel — the reader's "Ismaili Scholar Companion" side panel.
 *
 * Explains a concept — or the sentence you just selected — in the Ismaili Scholar
 * Gem's voice (POST /api/ai/gem-explain). Since 2026-07-26 it is the ONLY writer of
 * Companion notes: the hand-authored notes panel that used to sit beside it in the
 * Composer's drawer was retired with its floating button, so this panel holds its
 * own state and talks to the note store and the AI route directly.
 *
 * ONE button, two ways in (2026-07-28 — the separate "From selection" button is
 * retired; Explain now looks at the live selection first):
 *   Selection — highlight a sentence IN THE CHAPTER and press Explain: the panel
 *               explains it AND files the answer as a Companion note against that
 *               chapter, with the selected sentence as the note's verbatim `quote`.
 *               The passage is tinted in the chapter from that moment on, and the
 *               LIVE Session raises the same card as you reach it.
 *   Typed     — no selection: Explain answers the typed concept. Ephemeral;
 *               nothing is stored.
 *
 * The panel is a LIST, not a one-shot: it opens showing every explanation anchored
 * in the chapter in front of you, each a collapsed card, in the order the chapter
 * meets them. That is what the chapter's tinted passages point AT — a highlight
 * with no card to open would be a marker for something you could not read. The
 * LIVE Session lists exactly the same cards from the same component; the only
 * difference is that these ones can be edited and deleted and those cannot.
 *
 * Where a note lands is deliberately narrow: _system/companion-notes/<chapter>.json,
 * which the Composer and the LIVE Session read and NOTHING else does — never
 * book.md, never the PDF. Its chapter key comes from `sectionKeyFromHeading`, the
 * same rule that produces the LIVE Session's TOC ids.
 *
 * Design decision (2026-07-17): a slide-in side panel, so the prose stays readable
 * alongside the answer. Follows TermPopover's fetch/stale-guard; all styling lives
 * in gem-companion.css + companion-card.css using the shared --c-* tokens (no
 * inline styles).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { sectionKeyFromHeading } from "../../../lib/reader/companion/keys";
import { defaultStore } from "../../../lib/reader/companion/store.client";
import {
  renderExplanationCard,
  type CardEdit,
  type ExplanationCard,
} from "../../../lib/reader/companion/explanation-card";
import type { CompanionNote } from "../../../lib/reader/companion/types";

interface Result {
  body: string;
  /** One entry per term — the shape the route returns since 2026-07-26. */
  etymology: string[];
}

/** An answer to a typed concept, with the title it will carry as a card. */
interface Ephemeral extends Result {
  title: string;
}

interface Props {
  slug: string;
  bookTitle: string;
  /** Selector for the reading-prose container the selection must live inside. */
  proseSelector?: string;
  /** Render INSIDE a host drawer instead of as its own fixed slide-in.
   *  The Book Composer runs one shared right drawer with three surfaces (Tools,
   *  Arabic, Scholar), so this panel drops its own launcher button and its own
   *  close button there — the host's floating buttons own both jobs, and two
   *  competing drawers on one page is the thing that consolidation removed. */
  docked?: boolean;
  /** The chapter whose explanations to list — the LIVE Session section key. The
   *  host owns this: the Composer already has a chapter picker, and a second one
   *  in here could only ever disagree with it. */
  chapter?: string;
  /** Expand and scroll to this note (a passage was clicked in the chapter). The
   *  nonce makes a repeat click on the SAME note re-fire; the id alone wouldn't. */
  focusNote?: { id: string; nonce: number } | null;
  /** The notes whose passage is ON SCREEN in the chapter right now, in reading
   *  order — the Composer's scroll sweep computes it, because only the host can
   *  see the prose. Each of these cards lights up and expands; every other card
   *  goes dark and collapses, so the list always says where you are standing.
   *  `null` disables the behaviour entirely (the LIVE Session drives its own). */
  inViewIds?: string[] | null;
  /** Show ONLY these notes — the ones whose passage was found in the chapter now
   *  on screen. The host computes it, because only the host has the prose.
   *
   *  Why filter at all: a chapter's notes file also holds the reading notes
   *  written against earlier drafts of the same chapter, and a re-compose leaves
   *  most of them quoting sentences the text no longer contains. They are still
   *  that chapter's notes and they still belong to the LIVE Session — but in the
   *  Composer, where every card is meant to point at a tinted sentence, a card
   *  with nothing to point at is noise. `null` disables the filter entirely. */
  anchoredIds?: string[] | null;
  /** List the cards, but do not let this pass EDIT them (Asif, 2026-07-30).
   *
   *  The Composer's Read mode is a reading surface: the prose is a rendered page,
   *  not a canvas, and the panel beside it must agree — same cards, same tint,
   *  same follow-the-chapter sync, but no rich-text editor mounted in the card and
   *  no delete button. Expressed as "withhold the write callbacks" rather than as
   *  a second card style, because `renderExplanationCard` already derives
   *  editability from `onSave` and already has a read-only render (it is the one
   *  the public reader ships) whose CSS selectors are written as lists paired with
   *  the editable ones — so the two look identical by construction. */
  readOnly?: boolean;
  /** The chapter's notes changed — the host re-tints the prose. */
  onNotesChanged?: (notes: CompanionNote[]) => void;
  /** A card wants its passage shown in the prose. */
  onReveal?: (noteId: string) => void;
  /** A passage was highlighted (or the highlight was cleared/consumed) — the
   *  host paints it as a ProseMirror decoration in Edit mode, where the CSS
   *  Custom Highlight this panel paints itself has no effect (Chromium does
   *  not render `::highlight()` inside `contenteditable`). Read mode ignores
   *  this prop; its own DOM highlight already works there. */
  onPendingRange?: (range: Range | null) => void;
}

/** The element a selection boundary sits in (a text node reports its parent). */
function elementOf(node: Node | null): HTMLElement | null {
  if (!node) return null;
  return node instanceof Element
    ? (node as HTMLElement)
    : (node.parentElement ?? null);
}

/**
 * The chapter a selection belongs to, as the LIVE Session keys it.
 *
 * Two markups to satisfy with one rule. The Book Composer wraps each chapter in
 * `.cx-chapter[data-anchor="## 2. A Stranger in the City"]`, so the raw heading is
 * right there. A plain reading page has no such wrapper — the chapter is whatever
 * `## ` heading precedes the selection — so fall back to the nearest heading above
 * it and use its slug id (rendered by the same rule) or its text.
 */
function chapterKeyFor(node: Node | null): string {
  const el = elementOf(node);
  if (!el) return "";
  const wrapper = el.closest<HTMLElement>("[data-anchor]");
  if (wrapper?.dataset.anchor)
    return sectionKeyFromHeading(wrapper.dataset.anchor);

  const headings = Array.from(document.querySelectorAll<HTMLElement>("h1, h2"));
  let found: HTMLElement | null = null;
  for (const h of headings) {
    const pos = h.compareDocumentPosition(el);
    if (pos & Node.DOCUMENT_POSITION_FOLLOWING)
      found = h; // heading precedes the selection
    else break;
  }
  if (!found) return "";
  return found.id || sectionKeyFromHeading(found.textContent ?? "");
}

/** The transient answer's card id — never a note id, which are uuids. */
const EPHEMERAL = "__ephemeral__";

/** A short card title for the filed note — the passage, not a paraphrase of it. */
function labelFor(text: string): string {
  return text.length <= 72 ? text : `${text.slice(0, 69).trimEnd()}…`;
}

/** Name registered with the CSS Custom Highlight API — must match the
 *  `::highlight(gcp-pending)` rule in companion-card.css. */
const PENDING_HIGHLIGHT = "gcp-pending";

/** Paint `range` with the CSS Custom Highlight API rather than the browser's
 *  native selection: focusing the textarea to type a question collapses
 *  `window.getSelection()` (see readSelection's docs) and would otherwise take
 *  the visible highlight with it. A Custom Highlight is independent of focus
 *  and never touches the DOM, so it is safe to use anywhere — but Chromium
 *  does not actually PAINT `::highlight()` inside `contenteditable`, so this
 *  is Read-mode-only in practice; the Edit canvas gets its visible tint from
 *  `onPendingRange` → pending-selection-decos.ts instead. Registering it
 *  everywhere regardless costs nothing and keeps this function ignorant of
 *  which mode it's running in. No-op where unsupported (feature-detected —
 *  this is a visual nicety, never required for the flow to work). */
function paintPendingSelection(range: Range | null): void {
  if (typeof CSS === "undefined" || !("highlights" in CSS)) return;
  if (!range) {
    CSS.highlights.delete(PENDING_HIGHLIGHT);
    return;
  }
  CSS.highlights.set(PENDING_HIGHLIGHT, new Highlight(range.cloneRange()));
}

export default function GemCompanionPanel({
  slug,
  bookTitle,
  proseSelector = ".bookv-body",
  docked = false,
  chapter = "",
  focusNote = null,
  anchoredIds = null,
  inViewIds = null,
  readOnly = false,
  onNotesChanged,
  onReveal,
  onPendingRange,
}: Props) {
  const [open, setOpen] = useState(docked);
  const [input, setInput] = useState("");
  const [context, setContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [notes, setNotes] = useState<CompanionNote[]>([]);
  const [openIds, setOpenIds] = useState<string[]>([]);
  /** An answer to a typed concept: shown as a card, never stored. */
  const [ephemeral, setEphemeral] = useState<Ephemeral | null>(null);
  const [stage, setStage] = useState("Thinking…");

  // Monotonic request id: only the newest in-flight request may write results,
  // so a late response can never overwrite a newer one (mirrors TermPopover).
  const reqId = useRef(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const launcherRef = useRef<HTMLButtonElement>(null);
  /** The last real prose selection, captured on `selectionchange` so it survives
   *  focusing the textarea (which collapses `window.getSelection()`). Lets a
   *  reader highlight a passage, then type a targeted question about it in the
   *  box, without the highlight being lost the moment they click into the field.
   *  Consumed (cleared) the moment `submit()` uses it. */
  const lastSelectionRef = useRef<{
    text: string;
    context: string;
    chapterContext: string;
    chapter: string;
  } | null>(null);
  /** The held selection's text, mirrored into state so the panel can render it.
   *  `lastSelectionRef` is a ref precisely so capturing a selection does not
   *  re-render on every `selectionchange`; this is the one thing that must be
   *  visible, so it is the one thing kept in state. */
  const [held, setHeld] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const wasOpen = useRef(false);
  /** Live cards by note id. The list is reconciled against this, never rebuilt. */
  const cardsRef = useRef(new Map<string, ExplanationCard>());
  /** The setting the live cards were BUILT at, so a Read/Edit flip can be told
   *  apart from every other reason the list re-runs. */
  const builtReadOnly = useRef(readOnly);
  // Read by card callbacks, which outlive the render that created them.
  const openIdsRef = useRef<string[]>([]);
  const onRevealRef = useRef(onReveal);
  const onPendingRangeRef = useRef(onPendingRange);
  const saveRef = useRef<(id: string, edit: CardEdit) => void>(() => {});
  const removeRef = useRef<(id: string) => void>(() => {});
  const acceptRef = useRef<(id: string) => void>(() => {});

  useEffect(() => {
    if (open) {
      // NOT on a docked panel's first run (Asif, 2026-08-02). Docked means open
      // from mount, so this fired during page load and put the caret in the ask
      // box — on the Composer, that is the page opening with your typing aimed
      // at the note field instead of at the book. Focus belongs to whoever OPENS
      // the panel, and nobody opened this one. A later run still focuses, so the
      // reader's floating panel is unchanged.
      if (wasOpen.current || !docked) inputRef.current?.focus();
      wasOpen.current = true;
    } else if (wasOpen.current) {
      // Return focus to the launcher on close (never steal it on first mount).
      launcherRef.current?.focus();
    }
  }, [open, docked]);

  /** Show (or clear) the pending-selection tint on every surface that has
   *  one: this panel's own CSS Custom Highlight, and — the host's job,
   *  because only the host can reach the ProseMirror view — the Edit canvas
   *  decoration, via `onPendingRange`. */
  const setPendingHighlight = useCallback((range: Range | null) => {
    paintPendingSelection(range);
    onPendingRangeRef.current?.(range);
  }, []);

  /** Let the passage go without explaining it.
   *
   *  The panel HOLDS a selection on purpose — `lastSelectionRef` keeps it alive
   *  past the native selection so you can highlight a sentence and then click
   *  into the box to type a question about it. The cost of that, until now, was
   *  that there was no way out: clicking elsewhere collapses the native
   *  selection but not the held one, so the tint stayed and the next Explain
   *  would answer a passage you had moved on from. Pressing Explain was the only
   *  release (Asif, 2026-08-06).
   *
   *  Collapses the native selection too. Leaving it would let the very next
   *  `selectionchange` — a click, a caret move — re-capture the same passage and
   *  put the tint straight back. */
  const release = useCallback(() => {
    lastSelectionRef.current = null;
    setHeld("");
    setPendingHighlight(null);
    window.getSelection()?.removeAllRanges();
    inputRef.current?.focus();
  }, [setPendingHighlight]);

  // Capture the live prose selection as it happens, not just at submit time —
  // clicking into the textarea to type a question collapses `window.getSelection()`
  // (see readSelection's docs), so without this a highlight-then-type-a-question
  // flow would lose the highlight the instant the reader starts typing.
  useEffect(() => {
    if (!open) return;
    const onSelectionChange = () => {
      const picked = readSelection();
      if (!picked) return;
      lastSelectionRef.current = picked;
      setHeld(picked.text);
      const sel = window.getSelection();
      setPendingHighlight(sel?.rangeCount ? sel.getRangeAt(0) : null);
    };
    document.addEventListener("selectionchange", onSelectionChange);
    return () => {
      document.removeEventListener("selectionchange", onSelectionChange);
      setPendingHighlight(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, setPendingHighlight]);

  // The host's callback, held in a ref so the load effect below depends on the
  // CHAPTER and nothing else. Depending on the callback identity meant a host
  // that passes an inline arrow re-ran the load on every re-render — which
  // refetched the chapter and collapsed the card a click had just expanded.
  const notify = useRef(onNotesChanged);
  useEffect(() => {
    notify.current = onNotesChanged;
    onRevealRef.current = onReveal;
    onPendingRangeRef.current = onPendingRange;
  }, [onNotesChanged, onReveal, onPendingRange]);
  useEffect(() => {
    openIdsRef.current = openIds;
  }, [openIds]);

  const publish = useCallback((next: CompanionNote[]) => {
    setNotes(next);
    notify.current?.(next);
  }, []);

  // Load the chapter's explanations whenever the chapter changes, in FILE order.
  // Not newest-first: the list the reader sees is ordered by where the passages
  // fall in the chapter, and the order notes are handed to the matcher decides
  // which of two notes on the same sentence wraps the outer mark — so file order
  // here is what keeps the two surfaces listing the same cards the same way.
  useEffect(() => {
    if (!chapter) {
      publish([]);
      return;
    }
    let live = true;
    void defaultStore
      .read(slug, chapter)
      .then((doc) => {
        if (!live) return;
        publish(doc.notes);
        setOpenIds([]);
        setEphemeral(null);
      })
      .catch(() => {
        if (live) publish([]);
      });
    return () => {
      live = false;
    };
  }, [slug, chapter, publish]);

  // A passage was clicked in the chapter: expand its card and bring it into view.
  // ONE card at a time (Asif, 2026-07-28) — expanding this one shuts the rest.
  useEffect(() => {
    if (!focusNote) return;
    setOpenIds([focusNote.id]);
    const card = listRef.current?.querySelector<HTMLElement>(
      `[data-note="${CSS.escape(focusNote.id)}"]`,
    );
    card?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [focusNote]);

  const removeNote = useCallback(
    async (id: string) => {
      if (!chapter) return;
      const prev = notes;
      publish(notes.filter((n) => n.id !== id));
      try {
        await defaultStore.remove(slug, chapter, id);
      } catch (e) {
        publish(prev); // put it back — nothing was deleted
        setError(`Could not remove it: ${(e as Error).message}`);
      }
    },
    [chapter, notes, publish, slug],
  );

  /** Accept a machine-filed note: `review` -> "kept", and nothing else.
   *
   *  Optimistic like `removeNote` above and for the same reason — the badge and
   *  the keep button vanish the instant he clicks, and come back if the write
   *  fails. Unlike a delete this is not confirmed: keeping is reversible (the
   *  delete button is still there) and he may accept thirty of these in one
   *  pass, where a dialog each time is friction rather than safety. */
  const acceptNote = useCallback(
    async (id: string) => {
      if (!chapter) return;
      const prev = notes;
      publish(notes.map((n) => (n.id === id ? { ...n, review: "kept" } : n)));
      try {
        await defaultStore.accept(slug, chapter, id);
      } catch (e) {
        publish(prev); // put the badge back — nothing was accepted
        setError(`Could not keep it: ${(e as Error).message}`);
      }
    },
    [chapter, notes, publish, slug],
  );

  /** Save an edited title/body back to the note's file. */
  const saveNote = useCallback(
    async (
      id: string,
      edit: { anchor: string; body: string; etymology: string[] },
    ) => {
      if (!chapter) return;
      const current = notes.find((n) => n.id === id);
      if (!current) return;
      try {
        const saved = await defaultStore.upsert(slug, chapter, {
          id,
          kind: current.kind,
          body: edit.body,
          anchor: edit.anchor || undefined,
          // The quote is DELIBERATELY not sent (Asif, 2026-08-02). It is what
          // ties the card to a sentence in the chapter, it is not the author's
          // to retype here, and the copy this panel holds can be older than the
          // one on disk — the Composer re-points a note the moment its sentence
          // is edited and saved, and sending our copy back would undo that. An
          // absent quote means "keep whatever is filed"; see upsertNote.
          etymology: edit.etymology,
          source: current.source,
        });
        publish(notes.map((n) => (n.id === id ? saved : n)));
      } catch (e) {
        setError(`Could not save it: ${(e as Error).message}`);
      }
    },
    [chapter, notes, publish, slug],
  );

  // A card's callbacks are bound once, at creation, but `saveNote`/`removeNote`
  // close over the CURRENT notes — so the card calls through a ref that is kept
  // fresh, rather than through a stale copy from the render that built it.
  useEffect(() => {
    saveRef.current = (id, edit) => void saveNote(id, edit);
    removeRef.current = (id) => void removeNote(id);
    acceptRef.current = (id) => void acceptNote(id);
  }, [saveNote, removeNote, acceptNote]);

  // The cards actually shown: in the Composer, the notes whose passage is in the
  // chapter on screen. Memoized on the id list (a string, so a host that rebuilds
  // the array every render doesn't rebuild every card with it).
  const anchorKeyList = anchoredIds ? anchoredIds.join("|") : null;
  const visible = useMemo(() => {
    if (anchorKeyList === null) return notes;
    const byId = new Map(notes.map((n) => [n.id, n]));
    // The host's order IS reading order — the cards run down the chapter the way
    // the passages do, matching the LIVE Session's list.
    return anchorKeyList
      .split("|")
      .map((id) => byId.get(id))
      .filter((n): n is CompanionNote => Boolean(n));
  }, [notes, anchorKeyList]);

  /**
   * Mount the card list, REUSING the cards that are already there.
   *
   * Not a wipe-and-rebuild, which is what this was: an expanded card owns a live
   * rich-text editor, and rebuilding the list on every state change destroyed that
   * editor a keystroke after it was opened — taking any unsaved text with it. So
   * cards are keyed by note id, created once, reordered by moving their elements,
   * and destroyed only when their note leaves the list.
   */
  useEffect(() => {
    const host = listRef.current;
    if (!host) return;
    const live = cardsRef.current;

    // Editability is decided when a card is BUILT — renderExplanationCard reads it
    // off the callbacks it was handed — so a Read/Edit flip is the one change the
    // reuse above cannot absorb. Drop every card and let the loop below rebuild
    // them at the new setting; the editors going away is the point, and nothing is
    // lost because leaving Edit has already flushed its saves.
    if (builtReadOnly.current !== readOnly) {
      builtReadOnly.current = readOnly;
      for (const [id, card] of live) {
        card.destroy();
        card.el.remove();
        live.delete(id);
      }
    }

    const wanted: HTMLElement[] = [];
    if (ephemeral) {
      // Rebuilt every time on purpose: it is one transient answer, never stored,
      // and it carries no editor to lose.
      live.get(EPHEMERAL)?.destroy();
      live.get(EPHEMERAL)?.el.remove();
      const card = renderExplanationCard(
        {
          id: EPHEMERAL,
          kind: "explanation",
          body: ephemeral.body,
          anchor: ephemeral.title,
          etymology: ephemeral.etymology,
          source: { provider: "scholar", label: "Not saved" },
        },
        { open: true },
      );
      live.set(EPHEMERAL, card);
      wanted.push(card.el);
    } else if (live.has(EPHEMERAL)) {
      live.get(EPHEMERAL)!.destroy();
      live.get(EPHEMERAL)!.el.remove();
      live.delete(EPHEMERAL);
    }

    for (const note of visible) {
      let card = live.get(note.id);
      if (!card) {
        card = renderExplanationCard(note, {
          open: openIdsRef.current.includes(note.id),
          // ONE card at a time: opening a card is also what closes the others,
          // so the list stays a scannable column of titles with a single
          // explanation unfolded — and with at most one card open there can be
          // at most one etymology accordion open (each card already enforces
          // one within itself).
          onToggle: (id, isOpen) => setOpenIds(isOpen ? [id] : []),
          onReveal: (id) => onRevealRef.current?.(id),
          // Withheld in a reading pass: no editor mounted, no delete button.
          ...(readOnly
            ? {}
            : {
                onSave: (id: string, edit: CardEdit) =>
                  saveRef.current(id, edit),
                onRemove: (id: string) => void removeRef.current(id),
                onAccept: (id: string) => void acceptRef.current(id),
              }),
        });
        live.set(note.id, card);
      }
      wanted.push(card.el);
    }

    const keep = new Set(wanted);
    for (const [id, card] of live) {
      if (keep.has(card.el)) continue;
      card.destroy();
      card.el.remove();
      live.delete(id);
    }
    // Appending an element already in the DOM MOVES it — the editor inside is
    // untouched, which is the whole point of reusing rather than rebuilding.
    host.append(...wanted);
  }, [visible, ephemeral, readOnly]);

  // Open state is not a reason to rebuild a card; it is a reason to tell it.
  useEffect(() => {
    for (const [id, card] of cardsRef.current) {
      if (id === EPHEMERAL) continue;
      card.setOpen(openIds.includes(id));
    }
  }, [openIds, visible]);

  // ── The list follows the chapter (Asif, 2026-07-29) ───────────────────────
  // The host reports which annotated passages are on screen; those cards expand
  // and light up, and every other card shuts — so the panel and the prose beside
  // it are never describing different sentences. This is what the earlier
  // scroll-only sync was missing: moving a card to the top of the list said
  // "here", but with every card shut there was nothing to read when you got
  // there, and with one card manually open the open one was usually the wrong one.
  //
  // Two effects rather than one. WHICH cards are open is React state, so a manual
  // toggle and the scroll share one source of truth and the last to speak wins.
  // The lit ring is a class on a card element that may not have existed when the
  // ids arrived (a chapter change rebuilds the list), so it is re-applied on the
  // card list too — and it runs AFTER the mount effect above, which is what
  // guarantees the cards it reaches for are there.
  const inViewKey = inViewIds ? inViewIds.join("|") : null;
  useEffect(() => {
    if (inViewKey === null) return;
    // Never yank a card out from under an author typing in it. An open card holds
    // a live rich-text editor and saves on focusout; collapsing it mid-edit hides
    // the caret and the toolbar. A scroll while the caret is in a card is not a
    // request to close it.
    if (listRef.current?.contains(document.activeElement)) return;
    setOpenIds(inViewKey ? inViewKey.split("|") : []);
  }, [inViewKey]);

  useEffect(() => {
    if (inViewKey === null) return;
    const lit = new Set(inViewKey ? inViewKey.split("|") : []);
    for (const [id, card] of cardsRef.current) card.setInView(lit.has(id));
  }, [inViewKey, visible]);

  // Tear every editor down when the panel goes away.
  useEffect(() => {
    const live = cardsRef.current;
    return () => {
      for (const card of live.values()) card.destroy();
      live.clear();
    };
  }, []);

  /**
   * Read the live selection out of the chapter.
   *
   * The container test is `closest(proseSelector)` from the selection, NOT
   * `document.querySelector(proseSelector).contains(...)`: the Composer renders
   * every chapter as its own `.cx-chapter` and hides all but one, so the old test
   * asked whether the selection was inside the FIRST chapter and rejected a
   * perfectly good selection in every chapter after it.
   */
  function readSelection(): {
    text: string;
    context: string;
    chapterContext: string;
    chapter: string;
  } | null {
    if (typeof window === "undefined") return null;
    const sel = window.getSelection();
    // Selection.toString() reports the RENDERED selection and comes back empty
    // when the document isn't focused — so fall back to the range's own text,
    // which is the same string and always present.
    const raw =
      sel?.toString() || (sel?.rangeCount ? sel.getRangeAt(0).toString() : "");
    const text = raw.replace(/\s+/g, " ").trim();
    // Silent on failure: Explain PROBES for a selection and falls back to the
    // typed concept, so "no usable selection" is a normal path, not an error.
    if (!text) return null;
    const anchorEl = elementOf(sel?.anchorNode ?? null);
    if (!anchorEl?.closest(proseSelector)) return null;
    const para = anchorEl.closest("p, li, blockquote");
    // The chapter the selection is actually IN, taken from the selection rather
    // than from `document.querySelector(proseSelector)` — the Composer renders
    // every chapter as its own container and hides all but one, so querying the
    // document would hand back the first chapter no matter where you selected.
    // That is the same trap the container test above already documents.
    const chapterEl = anchorEl.closest(proseSelector);
    return {
      text,
      context: (para?.textContent || "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 600),
      chapterContext: (chapterEl?.textContent || "")
        .replace(/\s+/g, " ")
        .trim(),
      chapter: chapterKeyFor(sel?.anchorNode ?? null) || chapter,
    };
  }

  /**
   * Explain `concept`; when `passage` is given, file the answer for the reader.
   * `question`, when given, is a reader-typed ask ABOUT the concept/passage — the
   * answer is targeted at that question rather than a generic explanation of it.
   */
  async function explain(
    concept: string,
    ctx: string,
    passage?: { text: string; chapter: string },
    chapterCtx?: string,
    question?: string,
  ): Promise<void> {
    const id = ++reqId.current;
    setLoading(true);
    setError(null);
    setHint(null);
    setEphemeral(null);
    // Three server steps behind one button; say which one is running.
    setStage(passage ? "Reading the corpus…" : "Thinking…");

    try {
      // Deliberately raw fetch (not apiFetch): the 429 branch reads `retryMs`
      // from the error body, which apiFetch discards when it throws (R1).
      const res = await fetch("/api/ai/gem-explain", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          concept,
          context: ctx || undefined,
          // The chapter, so the explanation is written against the argument the
          // passage sits in rather than against one paragraph of it.
          chapterContext: chapterCtx || undefined,
          bookTitle,
          // Ground a PASSAGE in the library's corpus; a typed concept is a
          // question about an idea, not about a sentence in this chapter.
          ground: Boolean(passage),
          question: question || undefined,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (id !== reqId.current) return; // superseded by a newer request
      if (res.status === 429) {
        const secs = Math.ceil((data.retryMs ?? 5000) / 1000);
        throw new Error(`The Companion is busy — try again in about ${secs}s.`);
      }
      if (!res.ok || !data.ok) {
        throw new Error(
          typeof data.error === "string"
            ? data.error
            : `Request failed (${res.status}).`,
        );
      }
      const answer: Result = {
        body: String(data.body ?? ""),
        etymology: Array.isArray(data.etymology)
          ? data.etymology.map((e: unknown) => String(e ?? "")).filter(Boolean)
          : [],
      };
      if (passage) {
        await file(answer, passage, id);
      } else {
        setEphemeral({ ...answer, title: labelFor(concept) });
        setOpenIds([]); // the ephemeral answer renders open — it is the ONE open card
      }
    } catch (e) {
      if (id !== reqId.current) return;
      setError((e as Error).message);
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }

  /** Persist one explanation as a Companion note against its chapter. */
  async function file(
    answer: Result,
    passage: { text: string; chapter: string },
    id: number,
  ): Promise<void> {
    if (!passage.chapter) {
      setEphemeral({ ...answer, title: labelFor(passage.text) });
      setHint(
        "Explained, but not filed — I could not tell which chapter that selection is in.",
      );
      return;
    }
    try {
      const note = await defaultStore.upsert(slug, passage.chapter, {
        kind: "explanation",
        body: answer.body,
        etymology: answer.etymology,
        anchor: labelFor(passage.text),
        quote: passage.text,
        source: { provider: "scholar", label: "Ismaili Scholar" },
      });
      if (id !== reqId.current) return;
      publish([...notes.filter((n) => n.id !== note.id), note]);
      setOpenIds([note.id]); // the new answer is the ONE open card
    } catch (e) {
      if (id !== reqId.current) return;
      setEphemeral({ ...answer, title: labelFor(passage.text) });
      setHint(`Explained, but not filed: ${(e as Error).message}`);
    }
  }

  /**
   * The ONE button, three ways in:
   *   Selection + typed text — the box holds a targeted QUESTION about the
   *     highlighted passage (captured via `lastSelectionRef` so it survives
   *     focusing the textarea to type). The answer addresses that question,
   *     not a generic explanation of the passage, and is still filed against
   *     the chapter like any passage explanation.
   *   Selection only — unchanged: the passage is explained generically and
   *     filed as a Companion note.
   *   Typed text only, no selection — unchanged: the typed concept is
   *     explained (ephemeral, nothing filed).
   * The box is cleared the moment Explain is pressed, in every case — it is
   * not meant to keep showing what was just asked while the answer loads.
   */
  function submit(): void {
    const live = readSelection();
    if (live) lastSelectionRef.current = live;
    const picked = live ?? lastSelectionRef.current;
    const typed = input.trim();

    if (picked && typed) {
      setContext(picked.context);
      setInput("");
      lastSelectionRef.current = null;
      setHeld("");
      setPendingHighlight(null);
      void explain(
        picked.text,
        picked.context,
        { text: picked.text, chapter: picked.chapter },
        picked.chapterContext,
        typed,
      );
      return;
    }
    if (picked) {
      setContext(picked.context);
      setInput("");
      lastSelectionRef.current = null;
      setHeld("");
      setPendingHighlight(null);
      void explain(
        picked.text,
        picked.context,
        { text: picked.text, chapter: picked.chapter },
        picked.chapterContext,
      );
      return;
    }
    if (!typed) {
      setHint(
        "Highlight a sentence in the chapter — or type a concept — then press Explain.",
      );
      return;
    }
    setInput("");
    void explain(typed, context);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  }

  if (!open && !docked) {
    return (
      <button
        type="button"
        className="gcp-launcher"
        ref={launcherRef}
        onClick={() => setOpen(true)}
        aria-label="Ismaili Scholar Companion"
        title="Ismaili Scholar Companion"
      >
        <i className="fa-solid fa-book-open-reader" aria-hidden="true" />
      </button>
    );
  }

  return (
    <aside
      className={docked ? "gcp gcp--docked" : "gcp"}
      role="complementary"
      aria-label="Ismaili Scholar Companion"
      onKeyDown={(e) => {
        if (e.key === "Escape" && !docked) setOpen(false);
      }}
    >
      <div className="gcp-head">
        <h2 className="gcp-title">Ismaili Scholar Companion</h2>
        {!docked && (
          <button
            type="button"
            className="gcp-close"
            aria-label="Close Companion"
            onClick={() => setOpen(false)}
          >
            <i className="fa-solid fa-xmark" aria-hidden="true" />
          </button>
        )}
      </div>

      {/* The composing half of the panel — ask for an explanation, watch it arrive.
          Withheld in a reading pass (Asif, 2026-07-30): read-only cards beside a
          live "Explain" box was half a contradiction, offering to WRITE a new note
          into a chapter whose prose is currently a rendered page. Everything below
          this block is the reading half and stays. */}
      {!readOnly && (
        <>
          <label className="gcp-label" htmlFor="gcp-input">
            Concept to explain
          </label>
          <textarea
            id="gcp-input"
            ref={inputRef}
            className="gcp-input"
            rows={2}
            placeholder="e.g. wilayah — or highlight a sentence in the chapter and press Explain."
            value={input}
            onChange={(e) => setInput(e.currentTarget.value)}
            onKeyDown={onKeyDown}
          />

          <div className="gcp-actions">
            <button
              type="button"
              className="gcp-btn gcp-btn--primary"
              onClick={submit}
              disabled={loading}
              title="Explain the highlighted passage (and keep it with the chapter) — or the typed concept"
            >
              {loading ? stage : "Explain"}
            </button>
          </div>

          {/* What is held right now, and the way to let it go. Shows the
              passage itself rather than the words "a passage is selected": the
              tint is in the chapter, which may be scrolled off screen, so the
              panel has to be able to answer "selected WHAT" on its own. */}
          {held && (
            <p className="gcp-held">
              <i className="fa-solid fa-highlighter" aria-hidden="true" />
              <span className="gcp-held__text" title={held}>
                {held}
              </span>
              <button
                type="button"
                className="gcp-held__clear"
                onClick={release}
                title="Let this passage go"
                aria-label="Clear the selected passage"
              >
                <i className="fa-solid fa-xmark" aria-hidden="true" />
              </button>
            </p>
          )}

          {context && !held && (
            <p className="gcp-context" title={context}>
              <i className="fa-solid fa-quote-left" aria-hidden="true" />{" "}
              Grounding in the selected passage.
            </p>
          )}
          {hint && <p className="gcp-hint">{hint}</p>}
          {error && (
            <p className="gcp-error" role="alert">
              {error}
            </p>
          )}

          {loading && (
            <div className="gcp-result gcp-result--loading" aria-busy="true">
              <span className="gcp-skel" />
              <span className="gcp-skel" />
              <span className="gcp-skel gcp-skel--short" />
            </div>
          )}
        </>
      )}

      <div className="gcp-list" ref={listRef} />

      {!loading && !visible.length && !ephemeral && (
        <p className="gcp-hint">
          {!chapter
            ? "Open a chapter to see its explanations."
            : readOnly
              ? // Don't send a reader after a button that is not on screen.
                "No explanations for this chapter yet. Switch to Edit to write one."
              : "No explanations for this chapter yet. Highlight a sentence and press Explain."}
        </p>
      )}

      {(visible.length > 0 || ephemeral) && (
        <p className="gcp-disclaimer">
          Generated by AI in a scholarly persona. Verify against the source; AI
          can make mistakes.
        </p>
      )}
    </aside>
  );
}
