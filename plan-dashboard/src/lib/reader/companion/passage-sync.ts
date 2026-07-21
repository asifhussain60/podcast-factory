/**
 * passage-sync.ts — the two-way link between a Companion note and the sentence
 * it annotates.
 *
 * A note already stores the passage it is about (`quote`, captured from the
 * reader's selection). Until now that string only ever appeared inside the card,
 * so a reader had to find the sentence themselves. This module does both halves
 * of the link:
 *
 *   panel -> text   every note's quote is marked in the chapter, in the reader
 *                   surface's OWN highlighter colour (--reader-mark /
 *                   --reader-mark-edge, declared once in book-reader.css). No
 *                   second highlight is invented here.
 *   text -> panel   an IntersectionObserver over those marks reports which
 *                   passage is in view, so the panel can raise its card.
 *
 * Framework-free on purpose: it is DOM work, the reader surface it marks is
 * server-rendered HTML, and keeping it out of React means the Composer's plain
 * TypeScript surfaces can use it too.
 *
 * THREE things it must not do, each learned from this codebase:
 *   - Never mark inside a `contenteditable`. The Composer's Edit mode replaces
 *     the read render with a TipTap editor over the same chapter; a <mark> that
 *     landed in there would be round-tripped into book.md on the next autosave.
 *   - Never assume the marks survive. book-composer.ts's render() resets each
 *     chapter body to its pristine HTML to re-place figures, which drops every
 *     mark. It announces that with `pf:prose-rendered`, and this module re-marks
 *     on that event.
 *   - Never confuse the two scrollers. The chapter scrolls the WINDOW; the panel
 *     scrolls inside `.cx-surface`. The observer's root is therefore the
 *     viewport (root: null) and the panel's scrolling is somebody else's job —
 *     this module only reports which note is live.
 */

/** The event book-composer.ts fires after it rewrites a chapter's prose. */
export const PROSE_RENDERED_EVENT = "pf:prose-rendered";

/** Class on the wrapping element, so CSS and the observer share one hook. */
const MARK_CLASS = "cpn-passage";

/** Shorter than this and a "quote" matches half the chapter. */
const MIN_QUOTE = 4;

export interface PassageNote {
  id: string;
  quote?: string;
}

export interface PassageSyncOptions {
  /** Selector for the prose container. The first VISIBLE match is used — the
   *  Composer renders every chapter and hides all but the open one. */
  proseSelector: string;
  notes: PassageNote[];
  /** Called with the id of the note whose passage is in view, or null. */
  onActive: (id: string | null) => void;
  /** Called with the ids that were actually marked. A quote can be absent from
   *  the chapter or split by inline markup, and the panel must not offer a jump
   *  to a passage that has no mark to jump to. */
  onMarked?: (ids: string[]) => void;
}

/**
 * The nearest ancestor that actually scrolls, or null. The Companion panel is
 * docked inside `.cx-surface` in the Composer and is its own scroller in the
 * reader, so neither surface can hard-code its scroll target.
 */
export function scrollAncestor(el: HTMLElement): HTMLElement | null {
  let node: HTMLElement | null = el.parentElement;
  while (node) {
    const oy = getComputedStyle(node).overflowY;
    if (
      (oy === "auto" || oy === "scroll") &&
      node.scrollHeight > node.clientHeight
    )
      return node;
    node = node.parentElement;
  }
  return null;
}

/** Collapse runs of whitespace, remembering where each kept character came from,
 *  so a match found in the normalised string can be mapped back to raw offsets.
 *  Needed because a stored quote is whitespace-collapsed while the HTML text
 *  node it came from still carries the source's line breaks and indentation. */
function normalizeWithMap(raw: string): { text: string; map: number[] } {
  const out: string[] = [];
  const map: number[] = [];
  let pendingSpace = false;
  for (let i = 0; i < raw.length; i++) {
    const ch = raw[i];
    if (/\s/.test(ch)) {
      pendingSpace = out.length > 0;
      continue;
    }
    if (pendingSpace) {
      out.push(" ");
      map.push(i);
      pendingSpace = false;
    }
    out.push(ch);
    map.push(i);
  }
  return { text: out.join(""), map };
}

export function normalizeQuote(s: string): string {
  return s.replace(/\s+/g, " ").trim();
}

/** The first visible element matching `selector`, or the first one if none is
 *  laid out (server render before hydration, or a container in a hidden panel). */
function resolveContainer(selector: string): HTMLElement | null {
  const all = Array.from(document.querySelectorAll<HTMLElement>(selector));
  return all.find((el) => el.offsetParent !== null) ?? all[0] ?? null;
}

/**
 * Wrap the first verbatim occurrence of `quote` inside `container` in a mark.
 * Returns the mark, or null when the passage cannot be wrapped cleanly — it is
 * absent, too short, or it straddles inline markup (`<em>`, a footnote link),
 * which `surroundContents` cannot span. A missed passage is a card without a
 * highlight, never a mangled chapter.
 *
 * Two notes may point at the SAME sentence, or one may quote a phrase inside
 * another's longer quote. DOM elements cannot overlap, so the second note joins
 * the existing mark instead of getting one of its own: `data-note` holds a
 * space-separated list of ids, matched with the `~=` attribute selector. Without
 * this the shorter quote silently lost its link, which is how the two notes on
 * "their keys are remembrance" behaved before.
 */
function markPassage(
  container: HTMLElement,
  quote: string,
  id: string,
): HTMLElement | null {
  const needle = normalizeQuote(quote).toLowerCase();
  if (needle.length < MIN_QUOTE) return null;

  const existing = Array.from(
    container.querySelectorAll<HTMLElement>(`.${MARK_CLASS}`),
  ).find((m) =>
    normalizeQuote(m.textContent ?? "")
      .toLowerCase()
      .includes(needle),
  );
  if (existing) {
    existing.dataset.note = `${existing.dataset.note ?? ""} ${id}`.trim();
    return existing;
  }

  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      // Never touch the editor's own text, and never nest one mark in another.
      if (parent.closest(`[contenteditable], .${MARK_CLASS}`))
        return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  let node: Node | null;
  while ((node = walker.nextNode())) {
    const raw = node.textContent ?? "";
    const { text, map } = normalizeWithMap(raw);
    const at = text.toLowerCase().indexOf(needle);
    if (at < 0) continue;

    const range = document.createRange();
    try {
      range.setStart(node, map[at]);
      range.setEnd(node, map[at + needle.length - 1] + 1);
      const mark = document.createElement("mark");
      mark.className = MARK_CLASS;
      mark.dataset.note = id;
      range.surroundContents(mark);
      return mark;
    } catch {
      return null;
    }
  }
  return null;
}

/** Remove every mark this module added, restoring the original text nodes. */
function clearMarks(container: HTMLElement): void {
  container.querySelectorAll<HTMLElement>(`.${MARK_CLASS}`).forEach((m) => {
    const parent = m.parentNode;
    if (!parent) return;
    while (m.firstChild) parent.insertBefore(m.firstChild, m);
    parent.removeChild(m);
    parent.normalize(); // re-join the split text nodes so a re-mark can match
  });
}

/**
 * Scroll the chapter to a note's marked passage and flash it. The counterpart of
 * the observer: click a card, land on the sentence.
 */
export function revealPassage(id: string): boolean {
  const mark = document.querySelector<HTMLElement>(
    `.${MARK_CLASS}[data-note~="${CSS.escape(id)}"]`,
  );
  if (!mark) return false;
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)")
    ?.matches;
  // "start", not "center": mountPassageSync counts a passage as live only in the
  // TOP 45% of the viewport (rootMargin below), so centring it at 50% landed the
  // passage you just jumped to just OUTSIDE that band — nothing lit, or an earlier
  // mark higher on screen won the document-order tiebreak and the wrong card rose.
  // Landing it at the top puts it inside the band AND makes it the topmost visible
  // mark, so it wins that tiebreak. .cpn-passage carries the scroll-margin-top that
  // keeps it clear of the sticky topnav.
  mark.scrollIntoView({
    block: "start",
    behavior: reduce ? "auto" : "smooth",
  });
  return true;
}

/**
 * Mark every note's passage in the chapter and report which one is in view.
 * Returns a dispose function; React callers MUST call it on cleanup, or the
 * observer outlives the render that made it and keeps reporting into a dead
 * setState.
 */
export function mountPassageSync(opts: PassageSyncOptions): () => void {
  const { proseSelector, notes, onActive, onMarked } = opts;
  let observer: IntersectionObserver | null = null;
  /** (note, its mark) in DOCUMENT order — the tiebreak when several are on
   *  screen. Several entries can share one mark; see markPassage. */
  let order: { id: string; mark: HTMLElement }[] = [];
  /** The unique mark elements, for lighting exactly one of them. */
  let elements: HTMLElement[] = [];
  const visible = new Set<HTMLElement>();
  let last: string | null = null;

  function report(): void {
    const next = order.find((e) => visible.has(e.mark)) ?? null;
    if ((next?.id ?? null) === last) return;
    last = next?.id ?? null;
    // Exactly one passage is ever lit — the one whose card is raised.
    for (const mark of elements) {
      if (next && mark === next.mark) mark.dataset.active = "1";
      else delete mark.dataset.active;
    }
    onActive(last);
  }

  function apply(): void {
    observer?.disconnect();
    observer = null;
    visible.clear();
    order = [];
    elements = [];

    const container = resolveContainer(proseSelector);
    if (!container) {
      onMarked?.([]);
      return;
    }
    clearMarks(container);

    const found: { id: string; mark: HTMLElement }[] = [];
    for (const note of notes) {
      if (!note.quote) continue;
      const mark = markPassage(container, note.quote, note.id);
      if (mark) found.push({ id: note.id, mark });
    }
    onMarked?.(found.map((e) => e.id));
    if (!found.length) {
      report(); // no passages on screen — let the panel drop its active card
      return;
    }
    // Document order, not notes order: the card that rises is the one whose
    // sentence you have actually reached, whatever order the notes were written.
    order = found.sort((a, b) =>
      a.mark.compareDocumentPosition(b.mark) &
      Node.DOCUMENT_POSITION_FOLLOWING
        ? -1
        : 1,
    );
    elements = [...new Set(order.map((e) => e.mark))];
    // A re-mark (chapter re-render) rebuilds every node, so the remembered
    // "active" id no longer points at a live element. Forget it, or the first
    // report after a re-render would match `last` and light nothing.
    last = null;

    observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          const el = e.target as HTMLElement;
          if (e.isIntersecting) visible.add(el);
          else visible.delete(el);
        }
        report();
      },
      {
        // The viewport, because the CHAPTER scrolls the window. The bottom inset
        // narrows "in view" to the top 45% of the screen, so the live card is the
        // passage you are reading rather than one four paragraphs ahead.
        root: null,
        rootMargin: "0px 0px -55% 0px",
        threshold: 0,
      },
    );
    elements.forEach((m) => observer?.observe(m));
  }

  apply();
  // The Composer rebuilds a chapter's prose whenever figures move, which drops
  // every mark. Re-apply rather than trying to preserve them across an innerHTML
  // reset — the pristine HTML is the source of truth for that surface.
  const onRerender = () => apply();
  window.addEventListener(PROSE_RENDERED_EVENT, onRerender);

  return () => {
    window.removeEventListener(PROSE_RENDERED_EVENT, onRerender);
    observer?.disconnect();
    observer = null;
    const container = resolveContainer(proseSelector);
    if (container) clearMarks(container);
  };
}
