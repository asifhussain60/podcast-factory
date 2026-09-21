/**
 * Corrections — what a moderator says is wrong with a book, and what an admin decides.
 *
 * Reading is SHARED, writing is OWNED, and an admin overrides both:
 *
 *   | Action                       | Moderator, own      | Moderator, another's | Admin  |
 *   | See it                       | yes                 | yes                  | yes    |
 *   | Raise a new one              | yes                 | —                    | yes    |
 *   | Edit proposal / reason       | only while `open`   | no                   | always |
 *   | Withdraw / delete            | only while `open`   | no                   | always |
 *   | Accept / dismiss             | no                  | no                   | yes    |
 *
 * Every mutation calls `authority` FIRST. The panel hides controls a person cannot use, but
 * hiding is cosmetic — this is what refuses. A rule enforced in a component is a rule a
 * `.data` request walks straight past.
 *
 * Nothing here ever changes a book. A correction is CAPTURED; it is applied later, in the
 * repo, through the Book Composer (the one path by which chapter prose changes), and comes
 * back on the next publish. See migration 0023.
 *
 * Its own module, like `companion.server.ts`: `catalog.server.ts` states of itself that
 * nothing in it asks who may see what, and everything here does.
 */

import {
  isKind,
  type Occurrence,
  type AiReview,
  type Authority,
  type Correction,
  type CorrectionComment,
  type Kind,
  type Origin,
  type Status,
} from "~/lib/corrections";
import { sanitizeNote } from "~/lib/richNote";
import { event } from "./access.server";
import { normalizeEmail, tryNormalizeEmail } from "./email.server";

const MAX_TEXT = 8_000;
const MAX_QUOTE = 4_000;
const MAX_PREFIX = 200;
const MAX_RATIONALE = 10_000;
const MAX_DECISION_NOTE = 500;

/** The three things about the person acting that any rule here needs. */
export interface Actor {
  email: string;
  isAdmin: boolean;
  isModerator: boolean;
}

/** Why a request was refused — mapped to an HTTP status by the route, never shown raw. */
export { KINDS, isKind } from "~/lib/corrections";
export type {
  AiReview,
  Authority,
  Correction,
  Kind,
  Origin,
  Status,
} from "~/lib/corrections";

export class CorrectionError extends Error {
  constructor(
    readonly reason: "forbidden" | "stale" | "invalid" | "missing",
    message: string,
  ) {
    super(message);
  }
}

interface Row {
  id: string;
  slug: string;
  anchor_key: string;
  block_index: number;
  start_offset: number;
  end_offset: number;
  quote: string;
  prefix: string;
  proposed_text: string;
  rationale_html: string;
  kind: Kind;
  status: Status;
  origin: Origin;
  certainty: number | null;
  batch_id: string | null;
  raised_by: string;
  raised_at: string;
  updated_at: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_note: string | null;
  raiser_name: string | null;
  decider_name: string | null;
  r_verdict: AiReview["verdict"] | null;
  r_confidence: AiReview["confidence"] | null;
  r_summary: string | null;
  r_suggested: string | null;
  r_detail: string | null;
  r_source: AiReview["sourceKind"] | null;
  r_at: string | null;
}

/**
 * Whether two stored addresses are the same person. A pipeline suggestion is "raised by" the word
 * `pipeline`, which is not an address at all, so anything that cannot be normalised is simply
 * nobody — never an exception, which would take the whole list down with it.
 */
const sameAddress = (a: string, b: string): boolean => {
  const x = tryNormalizeEmail(a);
  const y = tryNormalizeEmail(b);
  return x !== null && y !== null && x === y;
};

/**
 * Who may change this row. The one place the table above is written as code.
 *
 * A person who is not a moderator has no authority over anything, whatever they are
 * holding — the route gate is the first wall and this is the second.
 */
export function authority(
  actor: Actor,
  row: { raised_by: string; status: Status },
): Authority {
  if (!actor.isModerator) return "none";
  if (actor.isAdmin) return "full";
  // A pipeline suggestion belongs to nobody, so any moderator may confirm or dismiss it —
  // that is the whole point of a sweep: people confirm errors instead of hunting for them.
  if (row.status === "suggested") return "triage";
  if (sameAddress(row.raised_by, actor.email) && row.status === "open")
    return "own";
  return "none";
}

/**
 * The name shown for somebody else's work: their recorded name, else the part of their
 * address before the `@`. An email is a privilege bit in this application and is not shown
 * for decoration.
 */
const nameOf = (name: string | null, email: string | null): string =>
  (name ?? "").trim() || (email ?? "").split("@")[0] || "Someone";

const DISPLAY = (alias: string) =>
  `NULLIF(TRIM(COALESCE(${alias}.first_name, '') || ' ' || COALESCE(${alias}.last_name, '')), '')`;

/** One database row as the client sees it, with what THIS viewer may do to it. */
const toCorrection = (
  r: Row,
  actor: Actor,
  comments: CorrectionComment[] = [],
): Correction => ({
  id: r.id,
  anchorKey: r.anchor_key,
  blockIndex: r.block_index,
  startOffset: r.start_offset,
  endOffset: r.end_offset,
  quote: r.quote,
  prefix: r.prefix,
  proposedText: r.proposed_text,
  rationaleHtml: r.rationale_html,
  kind: r.kind,
  status: r.status,
  origin: r.origin,
  certainty: r.certainty,
  batchId: r.batch_id,
  review: reviewOf(r),
  raisedByName:
    r.origin === "sweep"
      ? "Pipeline audit"
      : nameOf(r.raiser_name, r.raised_by),
  raisedAt: r.raised_at,
  updatedAt: r.updated_at,
  decidedByName: r.decided_by ? nameOf(r.decider_name, r.decided_by) : null,
  decisionNote: r.decision_note,
  mine: sameAddress(r.raised_by, actor.email),
  authority: authority(actor, r),
  comments,
});

/** The AI's opinion, if one was given for this version. Malformed detail is dropped, not shown. */
function reviewOf(r: Row): AiReview | null {
  if (r.r_verdict === null || r.r_confidence === null || r.r_summary === null)
    return null;

  let checks: AiReview["checks"] = [];
  try {
    const parsed = JSON.parse(r.r_detail ?? "{}") as { checks?: unknown };
    if (Array.isArray(parsed.checks))
      checks = parsed.checks.filter(
        (c): c is AiReview["checks"][number] =>
          typeof c === "object" &&
          c !== null &&
          typeof (c as { note?: unknown }).note === "string" &&
          ["ok", "warn", "no"].includes(
            (c as { result?: string }).result ?? "",
          ),
      );
  } catch {
    // A row the reviewer wrote badly shows its verdict without a checklist.
  }

  return {
    verdict: r.r_verdict,
    confidence: r.r_confidence,
    summary: r.r_summary,
    suggestedText: r.r_suggested,
    sourceKind: r.r_source ?? "none",
    checks,
    reviewedAt: r.r_at ?? "",
  };
}

/** Every live correction on one book — the SAME list for every moderator and admin. */
export async function listCorrections(
  db: D1Database,
  actor: Actor,
  slug: string,
): Promise<Correction[]> {
  if (!actor.isModerator) return [];

  const { results } = await db
    .prepare(
      `SELECT c.*, ${DISPLAY("ri")} AS raiser_name, ${DISPLAY("di")} AS decider_name,
              r.verdict AS r_verdict, r.confidence AS r_confidence, r.summary AS r_summary,
              r.suggested_text AS r_suggested, r.detail_json AS r_detail,
              r.source_kind AS r_source, r.reviewed_at AS r_at
         FROM correction c
         LEFT JOIN invite ri ON ri.email = c.raised_by
         LEFT JOIN invite di ON di.email = c.decided_by
         -- Only the review given for THIS version of the proposal. An edited proposal has a
         -- new updated_at, so it shows no verdict until it is reviewed again.
         LEFT JOIN correction_review r
                ON r.correction_id = c.id AND r.correction_updated = c.updated_at
        WHERE c.slug = ?1 AND c.deleted_at IS NULL
        ORDER BY c.block_index, c.start_offset, c.raised_at`,
    )
    .bind(slug)
    .all<Row>();

  const byCorrection = await commentsFor(db, actor, slug);
  return results.map((r) =>
    toCorrection(r, actor, byCorrection.get(r.id) ?? []),
  );
}

/* ---- Input, validated ---------------------------------------------------- */

const need = (v: unknown, max: number, what: string): string => {
  const s = typeof v === "string" ? v : "";
  if (s.trim() === "")
    throw new CorrectionError("invalid", `${what} is required`);
  if (s.length > max)
    throw new CorrectionError("invalid", `${what} is too long`);
  return s;
};
const index = (v: unknown, what: string): number => {
  const n = Number(v);
  if (!Number.isInteger(n) || n < 0)
    throw new CorrectionError("invalid", `${what} is not a position`);
  return n;
};
const rationale = (v: unknown): string => {
  const raw = typeof v === "string" ? v : "";
  if (raw.trim() === "") return "";
  // Stored markup is later rendered to a HIGHER-privileged account, so it is cleaned here on
  // write, by the same seven-tag allowlist a reader's note goes through — never trusted from
  // the editor that produced it.
  const clean = sanitizeNote(raw);
  if (clean.length > MAX_RATIONALE)
    throw new CorrectionError("invalid", "the reason is too long");
  return clean;
};

async function load(db: D1Database, slug: string, id: string) {
  const row = await db
    .prepare(
      `SELECT * FROM correction WHERE id = ?1 AND slug = ?2 AND deleted_at IS NULL`,
    )
    .bind(id, slug)
    .first<Row>();
  if (row === null) throw new CorrectionError("missing", "no such correction");
  return row;
}

const audit = (
  db: D1Database,
  now: string,
  actor: Actor,
  action: string,
  slug: string,
  id: string,
  detail: string | null,
) =>
  event(
    db,
    now,
    normalizeEmail(actor.email),
    action,
    slug,
    "correction",
    id,
    detail,
  );

/* ---- Mutations ------------------------------------------------------------ */

export interface ProposalInput {
  anchorKey: unknown;
  blockIndex: unknown;
  startOffset: unknown;
  endOffset: unknown;
  quote: unknown;
  prefix?: unknown;
  proposedText: unknown;
  rationale?: unknown;
  kind: unknown;
}

/** Raise a new correction. Any moderator, and any admin. */
export async function proposeCorrection(
  db: D1Database,
  actor: Actor,
  slug: string,
  input: ProposalInput,
  now: string,
): Promise<string> {
  if (!actor.isModerator)
    throw new CorrectionError("forbidden", "not a moderator");
  if (!isKind(input.kind)) throw new CorrectionError("invalid", "unknown kind");

  const start = index(input.startOffset, "selection start");
  const end = index(input.endOffset, "selection end");
  if (end <= start) throw new CorrectionError("invalid", "selection is empty");

  const quote = need(input.quote, MAX_QUOTE, "the passage");
  const proposed = need(input.proposedText, MAX_TEXT, "the replacement");
  if (proposed.trim() === quote.trim())
    throw new CorrectionError(
      "invalid",
      "the replacement is the same as the book",
    );

  const id = crypto.randomUUID();
  const raisedBy = normalizeEmail(actor.email);

  await db.batch([
    db
      .prepare(
        `INSERT INTO correction
           (id, slug, anchor_key, block_index, start_offset, end_offset, quote, prefix,
            proposed_text, rationale_html, kind, status, raised_by, raised_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, 'open', ?12, ?13, ?13)`,
      )
      .bind(
        id,
        slug,
        need(input.anchorKey, 400, "the chapter"),
        index(input.blockIndex, "paragraph"),
        start,
        end,
        quote,
        typeof input.prefix === "string"
          ? input.prefix.slice(0, MAX_PREFIX)
          : "",
        proposed,
        rationale(input.rationale),
        input.kind,
        raisedBy,
        now,
      ),
    audit(db, now, actor, "raise-correction", slug, id, null),
  ]);

  return id;
}

/** Edit a proposal. The raiser while it is `open`; an admin at any time. */
export async function reviseCorrection(
  db: D1Database,
  actor: Actor,
  slug: string,
  id: string,
  input: { proposedText: unknown; rationale?: unknown; kind: unknown },
  now: string,
): Promise<void> {
  const row = await load(db, slug, id);
  const can = authority(actor, row);
  if (can === "none")
    throw new CorrectionError("forbidden", "not yours to change");
  if (!isKind(input.kind)) throw new CorrectionError("invalid", "unknown kind");

  const proposed = need(input.proposedText, MAX_TEXT, "the replacement");
  if (proposed.trim() === row.quote.trim())
    throw new CorrectionError(
      "invalid",
      "the replacement is the same as the book",
    );

  // An admin rewriting SOMEBODY ELSE'S proposal leaves the previous text in the audit row, so
  // the change is never invisible to the person who raised it.
  const detail =
    can === "full" &&
    normalizeEmail(row.raised_by) !== normalizeEmail(actor.email)
      ? JSON.stringify({ was: row.proposed_text })
      : null;

  await db.batch([
    db
      .prepare(
        `UPDATE correction
            SET proposed_text = ?3, rationale_html = ?4, kind = ?5, updated_at = ?6
          WHERE id = ?1 AND slug = ?2 AND deleted_at IS NULL`,
      )
      .bind(id, slug, proposed, rationale(input.rationale), input.kind, now),
    audit(db, now, actor, "revise-correction", slug, id, detail),
  ]);
}

/**
 * Take a correction away. The raiser may WITHDRAW their own while it is `open`; an admin may
 * DELETE any. Both are soft — the row stays, gone from every view, like every other removal
 * in this database. `deleted_by` records which.
 */
export async function removeCorrection(
  db: D1Database,
  actor: Actor,
  slug: string,
  id: string,
  now: string,
): Promise<void> {
  const row = await load(db, slug, id);
  const can = authority(actor, row);
  if (can === "none")
    throw new CorrectionError("forbidden", "not yours to remove");

  await db.batch([
    db
      .prepare(
        `UPDATE correction SET deleted_at = ?3, deleted_by = ?4
          WHERE id = ?1 AND slug = ?2 AND deleted_at IS NULL`,
      )
      .bind(id, slug, now, normalizeEmail(actor.email)),
    audit(
      db,
      now,
      actor,
      can === "full" ? "delete-correction" : "withdraw-correction",
      slug,
      id,
      null,
    ),
  ]);
}

/**
 * Accept or dismiss. Admin only.
 *
 * `expectedUpdatedAt` is the concurrency token the admin SAW. If the proposal has changed
 * since — a moderator edited it in the instant the admin pressed Accept — the decision is
 * refused as stale, so what ships is what was read and not what it became.
 */
export async function decideCorrection(
  db: D1Database,
  actor: Actor,
  slug: string,
  id: string,
  decision: "accepted" | "dismissed",
  expectedUpdatedAt: unknown,
  note: unknown,
  now: string,
): Promise<void> {
  const row = await load(db, slug, id);
  if (authority(actor, row) !== "full")
    throw new CorrectionError("forbidden", "only an admin decides");
  if (row.status !== "open" && row.status !== "suggested")
    throw new CorrectionError("stale", "already decided");
  if (
    typeof expectedUpdatedAt !== "string" ||
    expectedUpdatedAt !== row.updated_at
  )
    throw new CorrectionError("stale", "changed since you looked");

  const said =
    typeof note === "string" && note.trim() !== ""
      ? note.trim().slice(0, MAX_DECISION_NOTE)
      : null;

  await db.batch([
    // The WHERE repeats the checks above, so a concurrent change between the read and this
    // write matches no row — and the audit row is then not written either (`changes()`).
    db
      .prepare(
        `UPDATE correction
            SET status = ?3, decided_by = ?4, decided_at = ?5, decision_note = ?6,
                updated_at = ?5
          WHERE id = ?1 AND slug = ?2 AND deleted_at IS NULL
            AND status IN ('open', 'suggested') AND updated_at = ?7`,
      )
      .bind(
        id,
        slug,
        decision,
        normalizeEmail(actor.email),
        now,
        said,
        expectedUpdatedAt,
      ),
    db
      .prepare(
        `INSERT INTO access_event (at, actor, action, subject, scope_type, scope_id, detail)
         SELECT ?1, ?2, ?3, ?4, 'correction', ?5, NULL WHERE changes() > 0`,
      )
      .bind(
        now,
        normalizeEmail(actor.email),
        decision === "accepted" ? "accept-correction" : "dismiss-correction",
        slug,
        id,
      ),
  ]);

  // A no-op UPDATE is not an error to D1, so confirm it landed.
  const after = await load(db, slug, id);
  if (after.status !== decision)
    throw new CorrectionError("stale", "changed since you looked");
}

/**
 * Confirm or dismiss a pipeline SUGGESTION. Any moderator may — that is the point of a sweep:
 * the audit already found the error, so a person confirms it instead of hunting for it.
 *
 * Confirming does NOT accept it. It turns the suggestion into an ordinary OPEN correction, which
 * an admin still decides. Carries the same concurrency token as an accept, so a suggestion an
 * admin edited in the meantime is never confirmed unseen.
 */
export async function triageSuggestion(
  db: D1Database,
  actor: Actor,
  slug: string,
  id: string,
  action: "confirm" | "dismiss",
  expectedUpdatedAt: unknown,
  note: unknown,
  now: string,
): Promise<void> {
  const row = await load(db, slug, id);
  if (!actor.isModerator)
    throw new CorrectionError("forbidden", "not yours to triage");
  // Checked BEFORE authority: a second moderator racing to confirm the same suggestion should
  // hear "already handled", not "forbidden" — they were entitled to try.
  if (row.status !== "suggested")
    throw new CorrectionError("stale", "not a suggestion any more");
  const can = authority(actor, row);
  if (can !== "triage" && can !== "full")
    throw new CorrectionError("forbidden", "not yours to triage");
  if (
    typeof expectedUpdatedAt !== "string" ||
    expectedUpdatedAt !== row.updated_at
  )
    throw new CorrectionError("stale", "changed since you looked");

  const said =
    typeof note === "string" && note.trim() !== ""
      ? note.trim().slice(0, MAX_DECISION_NOTE)
      : null;
  const who = normalizeEmail(actor.email);

  await db.batch([
    action === "confirm"
      ? db
          .prepare(
            `UPDATE correction SET status = 'open', updated_at = ?3
              WHERE id = ?1 AND slug = ?2 AND deleted_at IS NULL
                AND status = 'suggested' AND updated_at = ?4`,
          )
          .bind(id, slug, now, expectedUpdatedAt)
      : db
          .prepare(
            `UPDATE correction
                SET status = 'dismissed', decided_by = ?3, decided_at = ?4,
                    decision_note = ?5, updated_at = ?4
              WHERE id = ?1 AND slug = ?2 AND deleted_at IS NULL
                AND status = 'suggested' AND updated_at = ?6`,
          )
          .bind(id, slug, who, now, said, expectedUpdatedAt),
    db
      .prepare(
        `INSERT INTO access_event (at, actor, action, subject, scope_type, scope_id, detail)
         SELECT ?1, ?2, ?3, ?4, 'correction', ?5, NULL WHERE changes() > 0`,
      )
      .bind(
        now,
        who,
        action === "confirm" ? "confirm-suggestion" : "dismiss-suggestion",
        slug,
        id,
      ),
  ]);

  const after = await load(db, slug, id);
  if (after.status === "suggested")
    throw new CorrectionError("stale", "changed since you looked");
}

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

export interface UndecidedCorrection extends Correction {
  slug: string;
  bookTitle: string;
}

/**
 * Every correction still waiting on a decision, across every book — the admin's triage queue.
 * Admin only; anyone else gets nothing without a query. AI-supported ones first, then by the
 * audit's own certainty, so the quick, safe decisions come first.
 */
export async function listUndecided(
  db: D1Database,
  actor: Actor,
): Promise<UndecidedCorrection[]> {
  if (!actor.isAdmin) return [];

  const { results } = await db
    .prepare(
      `SELECT c.*, u.title AS book_title,
              ${DISPLAY("ri")} AS raiser_name, ${DISPLAY("di")} AS decider_name,
              r.verdict AS r_verdict, r.confidence AS r_confidence, r.summary AS r_summary,
              r.suggested_text AS r_suggested, r.detail_json AS r_detail,
              r.source_kind AS r_source, r.reviewed_at AS r_at
         FROM correction c
         JOIN content_unit u ON u.slug = c.slug
         LEFT JOIN invite ri ON ri.email = c.raised_by
         LEFT JOIN invite di ON di.email = c.decided_by
         LEFT JOIN correction_review r
                ON r.correction_id = c.id AND r.correction_updated = c.updated_at
        WHERE c.deleted_at IS NULL AND c.status IN ('suggested', 'open')
        ORDER BY u.title, (r.verdict = 'supports') DESC, c.certainty DESC, c.raised_at`,
    )
    .all<Row & { book_title: string }>();

  return results.map((r) => ({
    ...toCorrection(r, actor),
    slug: r.slug,
    bookTitle: r.book_title,
  }));
}

/**
 * Accept several at once, each carrying the concurrency token the admin SAW. One that changed
 * since is skipped and reported, never applied — "accept all" cannot ship what was not read.
 */
export async function decideMany(
  db: D1Database,
  actor: Actor,
  picks: { slug: string; id: string; expectedUpdatedAt: string }[],
  now: string,
): Promise<{ accepted: number; skipped: number }> {
  let accepted = 0;
  let skipped = 0;
  for (const pick of picks.slice(0, 200)) {
    try {
      await decideCorrection(
        db,
        actor,
        pick.slug,
        pick.id,
        "accepted",
        pick.expectedUpdatedAt,
        null,
        now,
      );
      accepted++;
    } catch (error) {
      if (!(error instanceof CorrectionError)) throw error;
      skipped++;
    }
  }
  return { accepted, skipped };
}

/* ---- Comments -------------------------------------------------------------- */

const MAX_COMMENT = 2_000;

interface CommentRow {
  id: string;
  correction_id: string;
  author: string;
  author_name: string | null;
  body: string;
  created_at: string;
}

/**
 * Every live comment on one book's corrections, grouped by correction, oldest first.
 *
 * SHARED between moderators like the corrections themselves: every moderator and admin sees every
 * comment. Empty for anyone else without a query.
 */
export async function commentsFor(
  db: D1Database,
  actor: Actor,
  slug: string,
): Promise<Map<string, CorrectionComment[]>> {
  const grouped = new Map<string, CorrectionComment[]>();
  if (!actor.isModerator) return grouped;

  const { results } = await db
    .prepare(
      `SELECT c.id, c.correction_id, c.author, c.body, c.created_at, ${DISPLAY("i")} AS author_name
         FROM correction_comment c
         LEFT JOIN invite i ON i.email = c.author
        WHERE c.slug = ?1 AND c.deleted_at IS NULL
        ORDER BY c.created_at, c.id`,
    )
    .bind(slug)
    .all<CommentRow>();

  for (const r of results) {
    const mine = sameAddress(r.author, actor.email);
    const list = grouped.get(r.correction_id) ?? [];
    list.push({
      id: r.id,
      authorName: nameOf(r.author_name, r.author),
      body: r.body,
      createdAt: r.created_at,
      mine,
      canDelete: mine || actor.isAdmin,
    });
    grouped.set(r.correction_id, list);
  }
  return grouped;
}

/**
 * Comment on a correction. ANY moderator or admin, on ANY correction, whatever its status — a
 * correction an admin has decided can still be discussed. Commenting is not changing: it never
 * touches the correction, so it needs no authority over it.
 */
export async function addComment(
  db: D1Database,
  actor: Actor,
  slug: string,
  correctionId: string,
  body: unknown,
  now: string,
): Promise<string> {
  if (!actor.isModerator)
    throw new CorrectionError("forbidden", "not a moderator");
  await load(db, slug, correctionId); // 'missing' for another book's id or a deleted one
  const text = need(body, MAX_COMMENT, "the comment").trim();

  const id = crypto.randomUUID();
  await db.batch([
    db
      .prepare(
        `INSERT INTO correction_comment (id, correction_id, slug, author, body, created_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)`,
      )
      .bind(id, correctionId, slug, normalizeEmail(actor.email), text, now),
    audit(db, now, actor, "comment-correction", slug, correctionId, null),
  ]);
  return id;
}

/** Remove a comment. Its author, or an admin. Soft, like every other removal. */
export async function removeComment(
  db: D1Database,
  actor: Actor,
  slug: string,
  commentId: string,
  now: string,
): Promise<void> {
  if (!actor.isModerator)
    throw new CorrectionError("forbidden", "not a moderator");

  const row = await db
    .prepare(
      `SELECT author, correction_id FROM correction_comment
        WHERE id = ?1 AND slug = ?2 AND deleted_at IS NULL`,
    )
    .bind(commentId, slug)
    .first<{ author: string; correction_id: string }>();
  if (row === null) throw new CorrectionError("missing", "no such comment");
  if (!actor.isAdmin && !sameAddress(row.author, actor.email))
    throw new CorrectionError("forbidden", "not your comment");

  await db.batch([
    db
      .prepare(
        `UPDATE correction_comment SET deleted_at = ?2, deleted_by = ?3
          WHERE id = ?1 AND deleted_at IS NULL`,
      )
      .bind(commentId, now, normalizeEmail(actor.email)),
    audit(
      db,
      now,
      actor,
      "uncomment-correction",
      slug,
      row.correction_id,
      null,
    ),
  ]);
}
