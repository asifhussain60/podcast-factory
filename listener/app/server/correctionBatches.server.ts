/**
 * "Fix everywhere": find the other places the same wording appears, and raise the same correction at
 * several of them as ONE batch that is reviewed and decided together.
 *
 * Split out of `corrections.server.ts` (size ceiling). Moderators and admins only; every function
 * refuses anyone else before touching the database.
 */

import { isKind, type Occurrence } from "~/lib/corrections";
import {
  CorrectionError,
  MAX_PREFIX,
  MAX_QUOTE,
  MAX_TEXT,
  audit,
  index,
  need,
  rationale,
  type Actor,
} from "./correctionKit.server";
import { normalizeEmail } from "./email.server";

/* ---- "Fix everywhere" ------------------------------------------------------ */

const MAX_OCCURRENCES = 40;

/**
 * Every OTHER place in the book where exactly this wording appears.
 *
 * Read from the search index, which already holds each chapter block's plain text, so no
 * chapter HTML is loaded or parsed. `ordinal` there is the same block number the reader anchors
 * on (both walk the chapter's top-level blocks). A block that holds the wording TWICE is left
 * out rather than guessed at — the reader refuses an ambiguous anchor for the same reason — and
 * so is any place a live correction already covers.
 */
export async function findOccurrences(
  db: D1Database,
  actor: Actor,
  slug: string,
  quote: string,
  from: { anchorKey: string; blockIndex: number },
): Promise<Occurrence[]> {
  if (!actor.isModerator || quote.trim().length < 3) return [];

  const { results } = await db
    .prepare(
      `SELECT anchor_key, heading, ordinal, quote AS text FROM search_passage
        WHERE slug = ?1 AND kind = 'chapter' AND instr(quote, ?2) > 0
        ORDER BY anchor_key, ordinal LIMIT 200`,
    )
    .bind(slug, quote)
    .all<{
      anchor_key: string;
      heading: string;
      ordinal: number;
      text: string;
    }>();

  const covered = await db
    .prepare(
      `SELECT anchor_key, block_index, start_offset, end_offset FROM correction
        WHERE slug = ?1 AND deleted_at IS NULL AND status IN ('suggested', 'open', 'accepted')`,
    )
    .bind(slug)
    .all<{
      anchor_key: string;
      block_index: number;
      start_offset: number;
      end_offset: number;
    }>();

  const found: Occurrence[] = [];
  for (const row of results) {
    if (row.anchor_key === from.anchorKey && row.ordinal === from.blockIndex)
      continue;

    const first = row.text.indexOf(quote);
    if (first < 0 || row.text.indexOf(quote, first + 1) >= 0) continue;
    const end = first + quote.length;

    const overlaps = covered.results.some(
      (c) =>
        c.anchor_key === row.anchor_key &&
        c.block_index === row.ordinal &&
        c.start_offset < end &&
        c.end_offset > first,
    );
    if (overlaps) continue;

    found.push({
      anchorKey: row.anchor_key,
      heading: row.heading,
      blockIndex: row.ordinal,
      startOffset: first,
      endOffset: end,
      quote,
      prefix: row.text.slice(Math.max(0, first - 48), first),
    });
    if (found.length >= MAX_OCCURRENCES) break;
  }
  return found;
}

/**
 * Raise the same correction at several places at once, as ONE batch that is reviewed and decided
 * together. Every item must carry exactly the wording being replaced, so one replacement text can
 * never be applied to a quote it was not written for.
 */
export async function proposeMany(
  db: D1Database,
  actor: Actor,
  slug: string,
  quote: string,
  items: Omit<Occurrence, "quote">[],
  input: { proposedText: unknown; rationale?: unknown; kind: unknown },
  now: string,
): Promise<{ batchId: string; ids: string[] }> {
  if (!actor.isModerator)
    throw new CorrectionError("forbidden", "not a moderator");
  if (!isKind(input.kind)) throw new CorrectionError("invalid", "unknown kind");
  if (items.length === 0 || items.length > MAX_OCCURRENCES)
    throw new CorrectionError("invalid", "choose between 1 and 40 places");

  const proposed = need(input.proposedText, MAX_TEXT, "the replacement");
  const original = need(quote, MAX_QUOTE, "the passage");
  if (proposed.trim() === original.trim())
    throw new CorrectionError(
      "invalid",
      "the replacement is the same as the book",
    );

  const reason = rationale(input.rationale);
  const batchId = crypto.randomUUID();
  const who = normalizeEmail(actor.email);
  const ids: string[] = [];
  const statements: D1PreparedStatement[] = [];

  for (const item of items) {
    const start = index(item.startOffset, "selection start");
    const end = index(item.endOffset, "selection end");
    if (end <= start)
      throw new CorrectionError("invalid", "selection is empty");
    const id = crypto.randomUUID();
    ids.push(id);
    statements.push(
      db
        .prepare(
          `INSERT INTO correction
             (id, slug, anchor_key, block_index, start_offset, end_offset, quote, prefix,
              proposed_text, rationale_html, kind, status, batch_id, raised_by, raised_at, updated_at)
           VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, 'open', ?12, ?13, ?14, ?14)`,
        )
        .bind(
          id,
          slug,
          need(item.anchorKey, 400, "the chapter"),
          index(item.blockIndex, "paragraph"),
          start,
          end,
          original,
          typeof item.prefix === "string"
            ? item.prefix.slice(0, MAX_PREFIX)
            : "",
          proposed,
          reason,
          input.kind,
          batchId,
          who,
          now,
        ),
      audit(
        db,
        now,
        actor,
        "raise-correction",
        slug,
        id,
        JSON.stringify({ batch: batchId }),
      ),
    );
  }

  await db.batch(statements);
  return { batchId, ids };
}
