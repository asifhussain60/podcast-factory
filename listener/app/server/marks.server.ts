/**
 * Everything a reader accumulates: position, bookmarks, highlights, notes.
 *
 * The counterpart to access.server.ts. That file decides who may open a book;
 * this one holds what they did once inside it, and the two never overlap — there
 * is no entitlement logic here at all. Every route that calls into this module
 * sits behind `requireUnitAccess`, so the question "may this person touch this
 * book's rows" was already answered by the same resolver the page used, against
 * the same `params.slug`. Re-asking it here would be a second authorization path,
 * and a second path is a path that can disagree.
 *
 * Two invariants, both of which the tests pin:
 *
 *   1. `normalizeEmail` on EVERY read and EVERY write. The email is the key, so
 *      an unfolded address is a second, invisible account holding a second set of
 *      notes. Callers pass `viewer.email`, which is already normalized; doing it
 *      again here is deliberate belt-and-braces and is idempotent by design
 *      (email.server.ts is tested for exactly that).
 *
 *   2. Writes are idempotent, because the client replays them. A phone that was
 *      offline holds an outbox and flushes it on reconnect, possibly twice, and
 *      possibly in an order the server has already seen. Every statement here is
 *      an UPSERT or a soft-delete stamp, never a bare INSERT and never a
 *      `DELETE FROM`; replaying a whole outbox against an up-to-date server is a
 *      no-op rather than an error or a duplicate.
 */

import { normalizeEmail } from "./email.server";

export const COLOURS = ["gold", "sage", "sky", "rose"] as const;
export type Colour = (typeof COLOURS)[number];

export const isColour = (v: unknown): v is Colour =>
  typeof v === "string" && (COLOURS as readonly string[]).includes(v);

export interface Progress {
  anchorKey: string;
  fraction: number;
  chaptersDone: number;
  updatedAt: string;
}

export interface Bookmark {
  id: string;
  anchorKey: string;
  blockIndex: number;
  label: string;
  createdAt: string;
}

export interface Annotation {
  id: string;
  anchorKey: string;
  blockIndex: number;
  startOffset: number;
  endOffset: number;
  quote: string;
  prefix: string;
  colour: Colour;
  note: string | null;
  createdAt: string;
  updatedAt: string;
}

/** Everything one person has accumulated in one book, in one round trip. */
export interface Marks {
  progress: Progress | null;
  bookmarks: Bookmark[];
  annotations: Annotation[];
  /** Seconds into each episode, by episode number. Absent means not started. */
  listening: Record<number, number>;
}

/**
 * How much text may be stored alongside a highlight.
 *
 * `quote` is the authority for re-anchoring, so it cannot be trimmed to a token —
 * but it is also attacker-controlled length in the sense that a client posts it,
 * and a book is not a place to store megabytes. 4,000 characters is longer than
 * any paragraph in the corpus by a wide margin. Over-long values are REJECTED
 * rather than truncated: a truncated quote would silently stop matching its own
 * passage, which is the one failure this design exists to avoid.
 */
const MAX_QUOTE = 4_000;
const MAX_NOTE = 10_000;
const MAX_LABEL = 200;
const MAX_PREFIX = 200;

export class InvalidMarkError extends Error {}

const requireText = (value: unknown, max: number, what: string): string => {
  if (typeof value !== "string") throw new InvalidMarkError(`${what} is missing`);
  const trimmed = value.trim();
  if (trimmed === "") throw new InvalidMarkError(`${what} is empty`);
  if (trimmed.length > max) throw new InvalidMarkError(`${what} is too long`);
  return trimmed;
};

const requireIndex = (value: unknown, what: string): number => {
  const n = Number(value);
  if (!Number.isInteger(n) || n < 0) throw new InvalidMarkError(`${what} is not an index`);
  return n;
};

/**
 * An identifier the CLIENT generated.
 *
 * It has to be accepted rather than assigned, because an annotation made offline
 * needs an identity before the server has seen it. Accepting it means validating
 * its SHAPE — it lands in a primary key, and a client that sends 100KB of text as
 * an id would otherwise store it. Format is a v4-ish uuid; anything else is
 * refused rather than coerced.
 */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

const requireId = (value: unknown): string => {
  if (typeof value !== "string" || !ID.test(value)) throw new InvalidMarkError("bad id");
  return value;
};

/* -------------------------------------------------------------------------- */
/* Reading                                                                     */
/* -------------------------------------------------------------------------- */

export async function marksFor(db: D1Database, email: string, slug: string): Promise<Marks> {
  const who = normalizeEmail(email);

  // One batch, three statements. The reader's first paint is behind this call,
  // so three sequential round trips to D1 would be three times the latency for
  // data that is always wanted together.
  const [progress, bookmarks, annotations, listening] = await Promise.all([
    db
      .prepare(
        `SELECT anchor_key, fraction, chapters_done, updated_at
           FROM reading_progress WHERE user_email = ?1 AND slug = ?2`,
      )
      .bind(who, slug)
      .first<{ anchor_key: string; fraction: number; chapters_done: number; updated_at: string }>(),

    db
      .prepare(
        `SELECT id, anchor_key, block_index, label, created_at
           FROM bookmark
          WHERE user_email = ?1 AND slug = ?2 AND deleted_at IS NULL
          ORDER BY created_at`,
      )
      .bind(who, slug)
      .all<{
        id: string;
        anchor_key: string;
        block_index: number;
        label: string;
        created_at: string;
      }>(),

    db
      .prepare(
        `SELECT id, anchor_key, block_index, start_offset, end_offset, quote, prefix,
                colour, note, created_at, updated_at
           FROM annotation
          WHERE user_email = ?1 AND slug = ?2 AND deleted_at IS NULL
          ORDER BY block_index, start_offset`,
      )
      .bind(who, slug)
      .all<{
        id: string;
        anchor_key: string;
        block_index: number;
        start_offset: number;
        end_offset: number;
        quote: string;
        prefix: string;
        colour: Colour;
        note: string | null;
        created_at: string;
        updated_at: string;
      }>(),

    listeningFor(db, who, slug),
  ]);

  return {
    progress:
      progress === null
        ? null
        : {
            anchorKey: progress.anchor_key,
            fraction: progress.fraction,
            chaptersDone: progress.chapters_done,
            updatedAt: progress.updated_at,
          },
    bookmarks: bookmarks.results.map((r) => ({
      id: r.id,
      anchorKey: r.anchor_key,
      blockIndex: r.block_index,
      label: r.label,
      createdAt: r.created_at,
    })),
    annotations: annotations.results.map((r) => ({
      id: r.id,
      anchorKey: r.anchor_key,
      blockIndex: r.block_index,
      startOffset: r.start_offset,
      endOffset: r.end_offset,
      quote: r.quote,
      prefix: r.prefix,
      colour: r.colour,
      note: r.note,
      createdAt: r.created_at,
      updatedAt: r.updated_at,
    })),
    listening,
  };
}

/**
 * Progress across every book at once, for the library grid and the book page.
 *
 * Returned as a map keyed by slug rather than a list, because both callers want
 * to ask "what about this one" per card and neither wants to scan. Books with no
 * progress are simply absent — a missing key is "not started", which is the
 * honest answer and needs no row.
 */
export async function progressForAll(
  db: D1Database,
  email: string,
): Promise<Record<string, Progress>> {
  const { results } = await db
    .prepare(
      `SELECT slug, anchor_key, fraction, chapters_done, updated_at
         FROM reading_progress WHERE user_email = ?1`,
    )
    .bind(normalizeEmail(email))
    .all<{
      slug: string;
      anchor_key: string;
      fraction: number;
      chapters_done: number;
      updated_at: string;
    }>();

  const out: Record<string, Progress> = {};
  for (const r of results) {
    out[r.slug] = {
      anchorKey: r.anchor_key,
      fraction: r.fraction,
      chaptersDone: r.chapters_done,
      updatedAt: r.updated_at,
    };
  }
  return out;
}

/** Where the listener had got to in each episode of one book, by episode number. */
export async function listeningFor(
  db: D1Database,
  email: string,
  slug: string,
): Promise<Record<number, number>> {
  const { results } = await db
    .prepare(`SELECT number, seconds FROM listening_progress WHERE user_email = ?1 AND slug = ?2`)
    .bind(normalizeEmail(email), slug)
    .all<{ number: number; seconds: number }>();

  const out: Record<number, number> = {};
  for (const r of results) out[r.number] = r.seconds;
  return out;
}

/* -------------------------------------------------------------------------- */
/* Writing                                                                     */
/* -------------------------------------------------------------------------- */

/**
 * Last-writer-wins, deliberately.
 *
 * Two devices open on the same book will disagree about where "here" is, and
 * there is no correct merge — the answer is wherever the reader most recently
 * was. Guarding on `updated_at` would mean a phone with a slow clock could pin
 * progress in the past and never advance.
 */
export async function setProgress(
  db: D1Database,
  email: string,
  slug: string,
  input: { anchorKey: unknown; fraction: unknown; chaptersDone: unknown },
  now: string,
): Promise<void> {
  const fraction = Number(input.fraction);
  if (!Number.isFinite(fraction)) throw new InvalidMarkError("fraction is not a number");

  await db
    .prepare(
      `INSERT INTO reading_progress (user_email, slug, anchor_key, fraction, chapters_done, updated_at)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6)
       ON CONFLICT(user_email, slug) DO UPDATE SET
         anchor_key = ?3, fraction = ?4, chapters_done = ?5, updated_at = ?6`,
    )
    .bind(
      normalizeEmail(email),
      slug,
      requireText(input.anchorKey, 400, "chapter"),
      Math.min(1, Math.max(0, fraction)),
      requireIndex(input.chaptersDone, "chapters read"),
      now,
    )
    .run();
}

export async function setListening(
  db: D1Database,
  email: string,
  slug: string,
  input: { number: unknown; seconds: unknown },
  now: string,
): Promise<void> {
  const seconds = Number(input.seconds);
  if (!Number.isFinite(seconds)) throw new InvalidMarkError("seconds is not a number");

  await db
    .prepare(
      `INSERT INTO listening_progress (user_email, slug, number, seconds, updated_at)
       VALUES (?1, ?2, ?3, ?4, ?5)
       ON CONFLICT(user_email, slug, number) DO UPDATE SET seconds = ?4, updated_at = ?5`,
    )
    .bind(
      normalizeEmail(email),
      slug,
      requireIndex(input.number, "episode"),
      Math.max(0, Math.floor(seconds)),
      now,
    )
    .run();
}

/**
 * Create a bookmark, or resurrect one the same id already named.
 *
 * The UPSERT clearing `deleted_at` is what makes a replayed outbox safe: a device
 * that adds, removes and re-adds the same mark while offline flushes three
 * statements, and the last one must win rather than collide with the primary key.
 */
export async function addBookmark(
  db: D1Database,
  email: string,
  slug: string,
  input: { id: unknown; anchorKey: unknown; blockIndex: unknown; label: unknown },
  now: string,
): Promise<void> {
  await db
    .prepare(
      `INSERT INTO bookmark (id, user_email, slug, anchor_key, block_index, label, created_at)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
       ON CONFLICT(id) DO UPDATE SET deleted_at = NULL, block_index = ?5, label = ?6`,
    )
    .bind(
      requireId(input.id),
      normalizeEmail(email),
      slug,
      requireText(input.anchorKey, 400, "chapter"),
      requireIndex(input.blockIndex, "paragraph"),
      requireText(input.label, MAX_LABEL, "label"),
      now,
    )
    .run();
}

/**
 * The `user_email` in the WHERE clause is not redundant.
 *
 * `requireUnitAccess` proves the caller may open the BOOK; it says nothing about
 * whose row this id belongs to, and ids are client-generated so one could be
 * guessed or copied. Scoping every mutation to the caller's own email is what
 * makes an id unguessable-in-effect: knowing someone else's changes nothing.
 */
export async function removeBookmark(
  db: D1Database,
  email: string,
  slug: string,
  id: unknown,
  now: string,
): Promise<void> {
  await db
    .prepare(
      `UPDATE bookmark SET deleted_at = ?4
        WHERE id = ?1 AND user_email = ?2 AND slug = ?3 AND deleted_at IS NULL`,
    )
    .bind(requireId(id), normalizeEmail(email), slug, now)
    .run();
}

export async function saveAnnotation(
  db: D1Database,
  email: string,
  slug: string,
  input: {
    id: unknown;
    anchorKey: unknown;
    blockIndex: unknown;
    startOffset: unknown;
    endOffset: unknown;
    quote: unknown;
    prefix?: unknown;
    colour: unknown;
    note?: unknown;
  },
  now: string,
): Promise<void> {
  if (!isColour(input.colour)) throw new InvalidMarkError("unknown colour");

  const start = requireIndex(input.startOffset, "selection start");
  const end = requireIndex(input.endOffset, "selection end");
  if (end <= start) throw new InvalidMarkError("selection is empty");

  const note =
    input.note === undefined || input.note === null || String(input.note).trim() === ""
      ? null
      : requireText(input.note, MAX_NOTE, "note");

  const prefix =
    input.prefix === undefined || input.prefix === null ? "" : String(input.prefix).slice(0, MAX_PREFIX);

  // The anchor is rewritten on conflict as well as inserted. That is what lets
  // the client SAVE A CORRECTION: when a re-compose has moved a passage and the
  // quote is re-found elsewhere, the corrected offsets are written back through
  // this same call, so the next device to open the chapter finds it first time
  // instead of repeating the search.
  await db
    .prepare(
      `INSERT INTO annotation
         (id, user_email, slug, anchor_key, block_index, start_offset, end_offset,
          quote, prefix, colour, note, created_at, updated_at)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12)
       ON CONFLICT(id) DO UPDATE SET
         deleted_at = NULL, anchor_key = ?4, block_index = ?5, start_offset = ?6,
         end_offset = ?7, quote = ?8, prefix = ?9, colour = ?10, note = ?11,
         updated_at = ?12`,
    )
    .bind(
      requireId(input.id),
      normalizeEmail(email),
      slug,
      requireText(input.anchorKey, 400, "chapter"),
      requireIndex(input.blockIndex, "paragraph"),
      start,
      end,
      requireText(input.quote, MAX_QUOTE, "quote"),
      prefix,
      input.colour,
      note,
      now,
    )
    .run();
}

export async function removeAnnotation(
  db: D1Database,
  email: string,
  slug: string,
  id: unknown,
  now: string,
): Promise<void> {
  await db
    .prepare(
      `UPDATE annotation SET deleted_at = ?4, updated_at = ?4
        WHERE id = ?1 AND user_email = ?2 AND slug = ?3 AND deleted_at IS NULL`,
    )
    .bind(requireId(id), normalizeEmail(email), slug, now)
    .run();
}

/**
 * Everything one person holds, across the whole library.
 *
 * Only used by the account-wide count on the library page. Scoped to the caller's
 * own email and returning counts rather than content, so it never becomes a way
 * to read the text of a book the caller has since lost access to.
 */
export async function markCounts(
  db: D1Database,
  email: string,
): Promise<Record<string, { notes: number; bookmarks: number }>> {
  const who = normalizeEmail(email);

  const [annotations, bookmarks] = await Promise.all([
    db
      .prepare(
        `SELECT slug, count(*) AS n FROM annotation
          WHERE user_email = ?1 AND deleted_at IS NULL GROUP BY slug`,
      )
      .bind(who)
      .all<{ slug: string; n: number }>(),
    db
      .prepare(
        `SELECT slug, count(*) AS n FROM bookmark
          WHERE user_email = ?1 AND deleted_at IS NULL GROUP BY slug`,
      )
      .bind(who)
      .all<{ slug: string; n: number }>(),
  ]);

  const out: Record<string, { notes: number; bookmarks: number }> = {};
  const slot = (slug: string) => (out[slug] ??= { notes: 0, bookmarks: 0 });
  for (const r of annotations.results) slot(r.slug).notes = r.n;
  for (const r of bookmarks.results) slot(r.slug).bookmarks = r.n;
  return out;
}
