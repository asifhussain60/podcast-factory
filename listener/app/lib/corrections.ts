/**
 * The shapes a correction has, safe to import from the browser.
 *
 * Kept apart from `corrections.server.ts` because a `.server` module may not be pulled into a
 * client bundle, and the panel needs these types (and `KINDS`, for its chips). Nothing here
 * decides anything about who may do what — that is `authority`, on the server.
 */

export const KINDS = [
  "typo",
  "arabic",
  "meaning",
  "citation",
  "formatting",
  "other",
] as const;
export type Kind = (typeof KINDS)[number];
export const isKind = (v: unknown): v is Kind =>
  typeof v === "string" && (KINDS as readonly string[]).includes(v);

export type Status =
  "suggested" | "open" | "accepted" | "applied" | "dismissed";

/** Where a correction came from: a person, or the pipeline's own audit (a "sweep"). */
export type Origin = "moderator" | "sweep";

/** The AI reviewer's opinion. ADVISORY ONLY — it never decides anything. */
export interface AiReview {
  verdict: "supports" | "revise" | "reject" | "needs_human";
  confidence: "high" | "medium" | "low";
  summary: string;
  suggestedText: string | null;
  sourceKind: "scan" | "extracted" | "none";
  checks: { id: string; result: "ok" | "warn" | "no"; note: string }[];
  reviewedAt: string;
}

/**
 * `full`   an admin: everything.
 * `own`    the raiser, while it is still open: edit and withdraw.
 * `triage` any moderator, on a pipeline SUGGESTION only: confirm it or dismiss it.
 * `none`   nothing.
 */
export type Authority = "full" | "own" | "triage" | "none";

/** What the client is sent. Other people's addresses are never in it — see `nameOf`. */
/** One comment on a correction. Plain text; never markup. */
export interface CorrectionComment {
  id: string;
  authorName: string;
  body: string;
  createdAt: string;
  mine: boolean;
  /** Whether THIS viewer may remove it: its author, or an admin. */
  canDelete: boolean;
}

export interface Correction {
  id: string;
  anchorKey: string;
  blockIndex: number;
  startOffset: number;
  endOffset: number;
  quote: string;
  prefix: string;
  proposedText: string;
  rationaleHtml: string;
  kind: Kind;
  status: Status;
  origin: Origin;
  /** The audit's own confidence, 0-100, for a sweep suggestion. */
  certainty: number | null;
  /** Shared by every correction raised together by "fix everywhere". */
  batchId: string | null;
  /** The AI's opinion, present only when it was given for THIS version of the proposal. */
  review: AiReview | null;
  raisedByName: string;
  raisedAt: string;
  /** The concurrency token an accept must carry back. */
  updatedAt: string;
  decidedByName: string | null;
  decisionNote: string | null;
  /** Whether the person asking raised this one. Computed here, so no address is exposed. */
  mine: boolean;
  /** What THIS person may do to it, so the panel draws the right controls. */
  authority: Authority;
  /** Every moderator and admin may comment on any correction, whatever its status. */
  comments: CorrectionComment[];
}

/** How far one chapter's review has got. */
export interface ChapterProgress {
  anchorKey: string;
  title: string;
  reviewedByName: string | null;
  claimedByName: string | null;
  /** So the panel can offer "undo" on your own mark and "release" on your own claim. */
  reviewedByMe: boolean;
  claimedByMe: boolean;
}

/** Another place the same wording appears, offered so it can be fixed in one go. */
export interface Occurrence {
  anchorKey: string;
  heading: string;
  blockIndex: number;
  startOffset: number;
  endOffset: number;
  quote: string;
  prefix: string;
}

export interface SourcePage {
  page: number;
  text: string;
}

/** One kind of source for a chapter — the scan, or the pipeline's own extraction. */
export interface SourceView {
  kind: "scan" | "extracted";
  firstPage: number;
  lastPage: number;
  /** How far to trust it: a handwritten scan is not presented with a clean scan's confidence. */
  quality: "clean" | "noisy" | "unreliable";
  pages: SourcePage[];
}
