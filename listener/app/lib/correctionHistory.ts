/**
 * Correction history, safe to import from the browser: the shape one entry has, the plain words
 * for each action, and the Markdown a moderator copies to hand a correction (or a whole book's
 * worth) to an AI. Nothing here reads anything — `correctionHistory.server.ts` does that.
 */
import type { Correction } from "./corrections";

export interface CorrectionEvent {
  correctionId: string;
  at: string;
  action: string;
  actorName: string;
  mine: boolean;
  /** Parsed audit detail: `{was, now}` for a revision, `{now}` for a raise, `{note}`, `{body}`. */
  detail: Record<string, unknown> | null;
}

export const ACTION_WORDS: Record<string, string> = {
  "raise-correction": "raised it",
  "revise-correction": "changed the wording",
  "withdraw-correction": "withdrew it",
  "delete-correction": "deleted it",
  "accept-correction": "accepted it",
  "dismiss-correction": "dismissed it",
  "confirm-suggestion": "confirmed the audit's suggestion",
  "dismiss-suggestion": "said it is not an error",
  "comment-correction": "commented",
  "uncomment-correction": "removed a comment",
};

interface Wording {
  text?: string;
  kind?: string;
  reason?: string;
}
const asWording = (v: unknown): Wording | null =>
  typeof v === "object" && v !== null ? (v as Wording) : null;

/** Stored rationale is sanitised markup; the handoff wants plain text. */
const plain = (html: string) =>
  html
    .replace(/<\/(p|li|div)>/gi, "\n")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .trim();

const stamp = (iso: string) => iso.replace("T", " ").slice(0, 16) + " UTC";

/** What a history line says beyond who did what. */
export function describe(event: CorrectionEvent): string {
  const d = event.detail;
  if (d === null) return "";
  const was = asWording(d.was);
  const now = asWording(d.now);
  if (was !== null && now !== null) {
    const parts: string[] = [];
    if (was.text !== now.text) parts.push(`“${was.text}” → “${now.text}”`);
    if (was.kind !== now.kind) parts.push(`kind ${was.kind} → ${now.kind}`);
    if (plain(was.reason ?? "") !== plain(now.reason ?? ""))
      parts.push("reason edited");
    return parts.join("; ");
  }
  if (now !== null) return `“${now.text ?? ""}” (${now.kind ?? "other"})`;
  if (typeof d.note === "string") return d.note;
  if (typeof d.body === "string") return d.body;
  return "";
}

/**
 * The Markdown a moderator copies for an AI: each correction with its passage, its current
 * proposal and reason, then its timeline. Self-contained — an AI given only this can see what
 * the book says, what was proposed, who changed what and when, and what was decided.
 */
export function historyMarkdown(
  bookTitle: string,
  items: Correction[],
  events: CorrectionEvent[],
): string {
  const out = [
    `# Corrections — ${bookTitle}`,
    "",
    `${items.length} correction${items.length === 1 ? "" : "s"}. Each shows the passage as the book prints it, the proposed replacement, and the full history of changes, oldest first.`,
  ];
  items.forEach((c, n) => {
    out.push(
      "",
      `## ${n + 1}. ${c.kind} — ${c.status}`,
      `- Raised by: ${c.raisedByName} (${stamp(c.raisedAt)})`,
      `- Book prints: “${c.quote}”`,
      `- Proposed: “${c.proposedText}”`,
    );
    const why = plain(c.rationaleHtml);
    if (why !== "") out.push(`- Reason: ${why}`);
    if (c.decisionNote !== null) out.push(`- Decision note: ${c.decisionNote}`);
    if (c.review !== null)
      out.push(
        `- AI review (advisory): ${c.review.verdict}, ${c.review.confidence} confidence — ${c.review.summary}`,
      );
    out.push("", "### History");
    const mine = events.filter((e) => e.correctionId === c.id);
    if (mine.length === 0) out.push("- (no history recorded)");
    for (const e of mine) {
      const extra = describe(e);
      out.push(
        `- ${stamp(e.at)} — ${e.actorName} ${ACTION_WORDS[e.action] ?? e.action}${extra === "" ? "" : `: ${extra}`}`,
      );
    }
    // Comments made before the history kept their text are still on the correction itself.
    const said = new Set(mine.map((e) => e.detail?.body));
    for (const m of c.comments)
      if (!said.has(m.body))
        out.push(`- comment by ${m.authorName}: ${m.body}`);
  });
  return out.join("\n") + "\n";
}
