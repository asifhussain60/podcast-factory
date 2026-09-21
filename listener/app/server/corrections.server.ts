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
  type AiReview,
  type Authority,
  type Correction,
  type CorrectionComment,
  type Status,
} from "~/lib/corrections";
import { commentsFor } from "./correctionComments.server";
import {
  CorrectionError,
  DISPLAY,
  MAX_DECISION_NOTE,
  MAX_PREFIX,
  MAX_QUOTE,
  MAX_TEXT,
  audit,
  index,
  load,
  nameOf,
  need,
  rationale,
  sameAddress,
  type Actor,
  type Row,
  wording,
} from "./correctionKit.server";
import { normalizeEmail } from "./email.server";

// Re-exported, so everything that imports from here keeps working.
export { CorrectionError, type Actor } from "./correctionKit.server";
export {
  addComment,
  commentsFor,
  removeComment,
} from "./correctionComments.server";
export { findOccurrences, proposeMany } from "./correctionBatches.server";

export { KINDS, isKind } from "~/lib/corrections";
export type {
  AiReview,
  Authority,
  Correction,
  Kind,
  Origin,
  Status,
} from "~/lib/corrections";

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
  const reason = rationale(input.rationale);

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
        reason,
        input.kind,
        raisedBy,
        now,
      ),
    audit(
      db,
      now,
      actor,
      "raise-correction",
      slug,
      id,
      JSON.stringify({ now: wording(proposed, input.kind, reason) }),
    ),
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

  // Every revision records the wording before AND after, whoever made it: a moderator's own edit
  // is as much a part of the history as an admin's rewrite of somebody else's, and the copy-for-AI
  // handoff is only as good as what was kept.
  const reason = rationale(input.rationale);
  const detail = JSON.stringify({
    was: wording(row.proposed_text, row.kind, row.rationale_html),
    now: wording(proposed, input.kind, reason),
  });

  await db.batch([
    db
      .prepare(
        `UPDATE correction
            SET proposed_text = ?3, rationale_html = ?4, kind = ?5, updated_at = ?6
          WHERE id = ?1 AND slug = ?2 AND deleted_at IS NULL`,
      )
      .bind(id, slug, proposed, reason, input.kind, now),
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
         SELECT ?1, ?2, ?3, ?4, 'correction', ?5, ?6 WHERE changes() > 0`,
      )
      .bind(
        now,
        normalizeEmail(actor.email),
        decision === "accepted" ? "accept-correction" : "dismiss-correction",
        slug,
        id,
        said === null ? null : JSON.stringify({ note: said }),
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
         SELECT ?1, ?2, ?3, ?4, 'correction', ?5, ?6 WHERE changes() > 0`,
      )
      .bind(
        now,
        who,
        action === "confirm" ? "confirm-suggestion" : "dismiss-suggestion",
        slug,
        id,
        action === "dismiss" && said !== null
          ? JSON.stringify({ note: said })
          : null,
      ),
  ]);

  const after = await load(db, slug, id);
  if (after.status === "suggested")
    throw new CorrectionError("stale", "changed since you looked");
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
