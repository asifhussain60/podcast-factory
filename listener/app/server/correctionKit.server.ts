/**
 * The pieces every correction module shares: who is acting, why a request is refused, how a stored
 * row is read, and how input is validated and audited.
 *
 * Split out of `corrections.server.ts` when that file outgrew the repo's size ceiling. Nothing here
 * decides who may do what - that is `authority()` - it is only the vocabulary the modules speak in.
 */

import type { AiReview, Kind, Origin, Status } from "~/lib/corrections";
import { sanitizeNote } from "~/lib/richNote";
import { event } from "./access.server";
import { normalizeEmail, tryNormalizeEmail } from "./email.server";

export const MAX_TEXT = 8_000;
export const MAX_QUOTE = 4_000;
export const MAX_PREFIX = 200;
export const MAX_RATIONALE = 10_000;
export const MAX_DECISION_NOTE = 500;

/** The three things about the person acting that any rule here needs. */
export interface Actor {
  email: string;
  isAdmin: boolean;
  isModerator: boolean;
}

/** Why a request was refused — mapped to an HTTP status by the route, never shown raw. */
export class CorrectionError extends Error {
  constructor(
    readonly reason: "forbidden" | "stale" | "invalid" | "missing",
    message: string,
  ) {
    super(message);
  }
}

export interface Row {
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
export const sameAddress = (a: string, b: string): boolean => {
  const x = tryNormalizeEmail(a);
  const y = tryNormalizeEmail(b);
  return x !== null && y !== null && x === y;
};

/**
 * The name shown for somebody else's work: their recorded name, else the part of their
 * address before the `@`. An email is a privilege bit in this application and is not shown
 * for decoration.
 */
export const nameOf = (name: string | null, email: string | null): string =>
  (name ?? "").trim() || (email ?? "").split("@")[0] || "Someone";

export const DISPLAY = (alias: string) =>
  `NULLIF(TRIM(COALESCE(${alias}.first_name, '') || ' ' || COALESCE(${alias}.last_name, '')), '')`;

/* ---- Input, validated ---------------------------------------------------- */

export const need = (v: unknown, max: number, what: string): string => {
  const s = typeof v === "string" ? v : "";
  if (s.trim() === "")
    throw new CorrectionError("invalid", `${what} is required`);
  if (s.length > max)
    throw new CorrectionError("invalid", `${what} is too long`);
  return s;
};
export const index = (v: unknown, what: string): number => {
  const n = Number(v);
  if (!Number.isInteger(n) || n < 0)
    throw new CorrectionError("invalid", `${what} is not a position`);
  return n;
};
export const rationale = (v: unknown): string => {
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

export async function load(db: D1Database, slug: string, id: string) {
  const row = await db
    .prepare(
      `SELECT * FROM correction WHERE id = ?1 AND slug = ?2 AND deleted_at IS NULL`,
    )
    .bind(id, slug)
    .first<Row>();
  if (row === null) throw new CorrectionError("missing", "no such correction");
  return row;
}

export const audit = (
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
