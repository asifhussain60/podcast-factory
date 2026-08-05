/**
 * /studio/<slug>/live — the LIVE Session, RETIRED 2026-08-01, redirects to the
 * Composer.
 *
 * It was a second surface doing the Composer's Read-mode job: a reading column
 * over the composed `book.md` with the companion explanations beside it. Once
 * Read mode gained the same read-only cards, the same passage tint and the same
 * follow-the-chapter scroll sync (locked 2026-07-30 — `GemCompanionPanel` takes
 * `readOnly` / `inViewIds` / `anchoredIds` so both surfaces rendered identical
 * cards), the two were one feature maintained twice. The cross-book picker it
 * also carried is `/studio` itself, which shelves books by bucket with volumes
 * nested.
 *
 * A redirect rather than a plain deletion, for the reason `arabic-review.ts`
 * records: the path falls through to `[step].astro` otherwise, which bounces
 * every unknown step to `/edit`. That is the wrong destination and a silent one —
 * `/edit` is the NotebookLM chapter lane, a different text for a different
 * deliverable, and someone following an old LIVE Session bookmark to it would
 * land in an editor over prose that never reaches the PDF.
 *
 * 302, not 301: a permanent redirect is cached by the browser indefinitely, and
 * this decision is one session old.
 *
 * Precedents: `/studio/<slug>/arabic-review` (2026-07-21) and
 * `/studio/<slug>/style` (2026-07-19), both retired the same way for the same
 * reason — a standalone duplicate of a Composer surface.
 */
import type { APIRoute } from "astro";

export const prerender = false;

export const GET: APIRoute = ({ params, redirect }) =>
  redirect(`/studio/${params.slug}/compose`, 302);
