/**
 * vowel-fix.ts — the decision logic for the Composer's "fix and vowel"
 * action, kept pure (no network, no editor) so it is checkable directly.
 *
 * SCOPE, DELIBERATELY NARROW. This is the single-selection Diacritics button
 * ONLY (`/api/studio/vowelling` action "run"). The batch propose/decide/apply
 * flow and the compose-time vowelling pass keep the original byte-identical-
 * skeleton guarantee unchanged — that flow is a human-reviewed, whole-book
 * pipeline where a silent letter change is a much larger blast radius than
 * one person fixing one passage they are looking at right now.
 *
 * WHY THE GUARANTEE CHANGES HERE AND ONLY HERE (Asif, 2026-08-14, reversing
 * the 2026-07-29 "marks only" lock for this ONE call site). The lock existed
 * to stop a model from silently rewriting a religious quotation's letters
 * while claiming to only mark it. Asked directly whether the button should
 * also fix wrong Arabic — not just add missing marks — the answer was yes,
 * explicitly, for this button specifically, not a silent reinterpretation of
 * the whole file's policy. The batch pipeline's skeleton gate in
 * scripts/lib/vowelling.mjs is untouched by this file.
 *
 * TWO STAGES. `needsSearchFallback` decides whether the FIRST (fast, cheap,
 * non-grounded) reply is usable, or whether the caller should retry with
 * Google-Search grounding — either because the model said so directly
 * (`NEEDS_SEARCH`, when it is asked to admit uncertainty rather than guess
 * silently) or because the reply came back empty, non-Arabic, or otherwise
 * unusable. The grounded stage is asked to return its best answer even when
 * no exact source is found — "determine intelligently" — so this path never
 * ends in "nothing came back."
 */

/** The line-level Arabic-script test both the route and its caller already
 *  use — mirrored here as a plain constant, not re-derived, so a fix to one
 *  cannot silently miss the other. */
export const ARABIC_LINE_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;

/** The literal token the primary (non-grounded) prompt is told to return
 *  instead of guessing when it is not confident of the passage's accurate
 *  wording. Exported so the prompt text and the check that reads it can
 *  never drift onto two different strings. */
export const NEEDS_SEARCH_TOKEN = "NEEDS_SEARCH";

/**
 * Should the caller fall back to a grounded (web-search) retry instead of
 * using this reply as-is?
 *
 * True for: an empty/whitespace-only reply, the model's own admission of
 * uncertainty, or a reply that does not actually contain Arabic script (a
 * model that answers in English prose instead of returning the passage is
 * not a usable answer, whatever it says).
 */
export function needsSearchFallback(reply: string): boolean {
  const t = (reply ?? "").trim();
  if (!t) return true;
  if (t === NEEDS_SEARCH_TOKEN) return true;
  if (!ARABIC_LINE_RE.test(t)) return true;
  return false;
}

/**
 * Pull the actual passage out of a raw model reply: strip a code fence if
 * the model wrapped one around it, strip leading/trailing quote marks, and
 * take the first line that actually contains Arabic script — the same
 * "models like to wrap a one-line answer" cleanup the batch propose path
 * already does, lifted out so this file's own fallback decision can run on
 * the CLEANED text rather than duplicating the cleanup inline at each call
 * site. Returns null when no line contains Arabic at all (the caller then
 * treats this exactly like an empty reply).
 */
export function cleanModelReply(raw: string): string | null {
  const stripped = (raw ?? "")
    .replace(/^```[a-z]*\s*/i, "")
    .replace(/```$/, "")
    .replace(/^["'«»]+|["'«»]+$/g, "")
    .trim();
  const line = stripped
    .split("\n")
    .map((l) => l.trim())
    .find((l) => l && ARABIC_LINE_RE.test(l));
  return line ?? null;
}
