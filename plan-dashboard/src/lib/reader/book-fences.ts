/**
 * book-fences.ts — keep the pipeline's machine fences alive across a rich-text
 * edit of book.md.
 *
 * THE PROBLEM THIS SOLVES
 * `0book-augment` writes source-grounded asides into book.md wrapped in machine
 * markers (`<!-- editorial:begin -->` … `<!-- editorial:end -->`); `_book_bridges`
 * does the same with `bridge:` and the self-study layer with `study-summary:`.
 * Those markers are load-bearing: `_book_voice.py` extracts fenced spans so the
 * re-voicing LLM never rewrites them, and `_book_augment._strip_existing_blocks`
 * uses them to replace rather than stack asides on the next run.
 *
 * The Composer's editor cannot preserve them on its own. The reader renderer
 * turns a comment line into a visible `.md-comment` div (markdown.ts), TipTap's
 * StarterKit schema has no HTML-comment node, so the serializer emits the marker
 * back as a BARE TEXT line (`editorial:begin`) — and PUT /api/studio/book-md
 * replaces the whole chapter body with that. Left alone, one save strips the
 * fences (and leaves their text visible in the prose), after which the Python
 * phases silently stop protecting and stop replacing the aside.
 *
 * The fix mirrors what `_book_voice.py` already does on the Python side —
 * fences are extracted and restored around the edit rather than trusted to
 * survive it:
 *   1. RESTORE — a bare `kind:begin` / `kind:end` line becomes its comment form
 *      again. This is the normal path and is lossless.
 *   2. RE-WRAP — a span whose markers vanished entirely but whose prose is still
 *      present gets its markers put back around that prose, in place.
 *   3. APPEND — a span that disappeared completely is re-appended verbatim at
 *      the end of the chapter, so its content is never lost (the same
 *      end-of-chapter fallback `_book_voice.py` uses).
 *   4. DROP ORPHANS — an unbalanced marker is removed rather than written, since
 *      a dangling fence would corrupt the Python parsers downstream.
 *
 * Pure string in / string out — no fs, no network — so it is unit-testable and
 * usable from both the API route and any future caller.
 */

/** Fence kinds the pipeline owns. Add one here and every step below follows.
 *
 * `edition-intro` joined 2026-07-21: `_book_frontmatter.py` fences the edition's
 * introduction with it, and on a book whose front matter opens the first chapter
 * the span lives inside that chapter's BODY — so a Composer save of that chapter
 * used to strip the markers, after which the Python `strip_introduction` stopped
 * matching and every later compose stacked a second introduction next to the
 * first. */
export const FENCE_KINDS = [
  "editorial",
  "study-summary",
  "bridge",
  "edition-intro",
] as const;

const INTRO_BEGIN_RE = /<!--\s*edition-intro:begin\s*-->/g;
const INTRO_END_RE = /<!--\s*edition-intro:end\s*-->/g;

/**
 * Net count of edition-intro spans opened minus closed in `text`.
 *
 * The introduction's own `## Introduction` heading lives INSIDE the fenced span
 * (so the Python strip removes the whole section in one cut), which means any
 * consumer that enumerates `## ` headings — the Composer's chapter list, the
 * chapter writer — will otherwise mistake the edition's apparatus for an
 * editable chapter. An "edit" of that section can never survive: the pipeline
 * strips and re-authors the introduction on every compose, so the saved edit is
 * orphaned each time. Callers walk the document keeping a running depth from
 * this delta and skip headings seen while the depth is positive.
 */
export function editionIntroDelta(text: string): number {
  const begins = text.match(INTRO_BEGIN_RE)?.length ?? 0;
  const ends = text.match(INTRO_END_RE)?.length ?? 0;
  return begins - ends;
}

const KIND_ALT = FENCE_KINDS.join("|");
const COMMENT_RE = new RegExp(`^<!--\\s*(${KIND_ALT}):(begin|end)\\s*-->$`);
const BARE_RE = new RegExp(`^(${KIND_ALT}):(begin|end)$`);

interface Marker {
  kind: string;
  side: "begin" | "end";
}

interface Span {
  kind: string;
  /** Lines between the markers, verbatim (blockquote prefixes included). */
  inner: string[];
}

export interface PreserveResult {
  body: string;
  /** Markers recovered from bare text (the normal path). */
  restored: number;
  /** Spans whose markers were re-wrapped around surviving prose. */
  rewrapped: number;
  /** Spans re-appended at the end because their prose was gone too. */
  appended: number;
  /** Unbalanced markers removed. */
  orphansDropped: number;
}

function markerOf(line: string): Marker | null {
  const t = line.trim();
  const m = t.match(COMMENT_RE) ?? t.match(BARE_RE);
  return m ? { kind: m[1], side: m[2] as "begin" | "end" } : null;
}

const begin = (kind: string) => `<!-- ${kind}:begin -->`;
const end = (kind: string) => `<!-- ${kind}:end -->`;

/** Comparable form of a span's prose: blockquote markers, emphasis and spacing
 *  all removed, so a cosmetic edit still matches its original span. */
function norm(lines: string[] | string): string {
  const s = Array.isArray(lines) ? lines.join(" ") : lines;
  return s
    .replace(/^>\s?/gm, "")
    .replace(/[*_`~#]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

/** Every balanced fenced span in a body, in document order. */
export function extractSpans(body: string): Span[] {
  const spans: Span[] = [];
  let cur: Span | null = null;
  for (const line of body.split("\n")) {
    const mk = markerOf(line);
    if (mk?.side === "begin" && !cur) {
      cur = { kind: mk.kind, inner: [] };
      continue;
    }
    if (mk?.side === "end" && cur && cur.kind === mk.kind) {
      spans.push(cur);
      cur = null;
      continue;
    }
    if (cur) cur.inner.push(line);
  }
  return spans;
}

/** Step 1 + 4: bare marker text back to comment form; drop unbalanced markers. */
function restoreMarkers(body: string): {
  lines: string[];
  restored: number;
  orphansDropped: number;
} {
  const src = body.split("\n");
  // First pass: which marker lines participate in a balanced pair?
  const keep = new Array<boolean>(src.length).fill(true);
  const open: { kind: string; idx: number }[] = [];
  for (let i = 0; i < src.length; i += 1) {
    const mk = markerOf(src[i]);
    if (!mk) continue;
    if (mk.side === "begin") {
      open.push({ kind: mk.kind, idx: i });
      continue;
    }
    const partner = open.findIndex((o) => o.kind === mk.kind);
    if (partner === -1)
      keep[i] = false; // end with no begin
    else open.splice(partner, 1);
  }
  for (const o of open) keep[o.idx] = false; // begin with no end

  const lines: string[] = [];
  let restored = 0;
  let orphansDropped = 0;
  for (let i = 0; i < src.length; i += 1) {
    const mk = markerOf(src[i]);
    if (!mk) {
      lines.push(src[i]);
      continue;
    }
    if (!keep[i]) {
      orphansDropped += 1;
      continue;
    }
    const canonical = mk.side === "begin" ? begin(mk.kind) : end(mk.kind);
    if (src[i].trim() !== canonical) restored += 1;
    lines.push(canonical);
  }
  return { lines, restored, orphansDropped };
}

/** Split a body's lines into blank-line-separated blocks, keeping line indices. */
function blocksOf(lines: string[]): { start: number; end: number }[] {
  const blocks: { start: number; end: number }[] = [];
  let start = -1;
  for (let i = 0; i < lines.length; i += 1) {
    const blank = lines[i].trim() === "";
    if (!blank && start === -1) start = i;
    if (blank && start !== -1) {
      blocks.push({ start, end: i - 1 });
      start = -1;
    }
  }
  if (start !== -1) blocks.push({ start, end: lines.length - 1 });
  return blocks;
}

/**
 * Reconcile `nextBody` (the editor's serialization) against `originalBody` so
 * every fenced span the pipeline owns survives the edit.
 *
 * The human's prose always wins — this only ever restores MARKERS, or re-appends
 * a span whose content vanished entirely. It never rewrites edited prose.
 */
export function preserveFences(
  originalBody: string,
  nextBody: string,
): PreserveResult {
  const originalSpans = extractSpans(originalBody);
  const { lines, restored, orphansDropped } = restoreMarkers(nextBody);

  // Nothing to protect — return the restored body untouched.
  if (originalSpans.length === 0) {
    return {
      body: lines.join("\n"),
      restored,
      rewrapped: 0,
      appended: 0,
      orphansDropped,
    };
  }

  let rewrapped = 0;
  let appended = 0;
  const survivingKeys = new Set(
    extractSpans(lines.join("\n")).map((s) => norm(s.inner)),
  );

  for (const span of originalSpans) {
    const key = norm(span.inner);
    if (!key || survivingKeys.has(key)) continue;

    // Step 2 — the prose is still there, only the markers went missing. Wrap the
    // block that carries it, in place, so the aside keeps its position.
    const target = blocksOf(lines).find((b) => {
      const text = norm(lines.slice(b.start, b.end + 1));
      return text === key || (text.length > 0 && text.includes(key));
    });
    if (target) {
      lines.splice(target.end + 1, 0, end(span.kind));
      lines.splice(target.start, 0, begin(span.kind));
      survivingKeys.add(key);
      rewrapped += 1;
      continue;
    }

    // Step 3 — content and markers both gone: re-append verbatim rather than
    // lose a pipeline-owned aside.
    lines.push("", begin(span.kind), ...span.inner, end(span.kind));
    survivingKeys.add(key);
    appended += 1;
  }

  return {
    body: lines.join("\n"),
    restored,
    rewrapped,
    appended,
    orphansDropped,
  };
}
