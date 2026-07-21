/**
 * /studio/<slug>/arabic-review — RETIRED 2026-07-21, redirects to the Composer.
 *
 * This page used to be a second place to change what the printed edition
 * contains: its term decisions persist to `_system/glossary.yml` (read by
 * `_book_frontmatter` during composition) and an accepted vowelling is written
 * into `book.md`. That makes it book-lane work, and the Book Composer is the
 * singular path for anything book-lane — a rule the WRITE layer already obeyed
 * (the vowelling apply has always gone through the Composer's own chapter
 * writer) while the UI did not. Both panels now live in the Composer's drawer as
 * its Arabic surface, beside the chapter they are about.
 *
 * A redirect rather than a plain deletion: the URL was linked from nothing in
 * the app — no subnav entry, no button, no inbound href anywhere in the source —
 * but it is exactly the kind of page someone keeps in a bookmark, and a 404
 * would read as the feature having been removed rather than moved. Without this
 * file the path does not 404 anyway: it falls through to `[step].astro`, which
 * bounces every unknown step to `/edit` — the wrong destination and a silent one.
 *
 * 302, not 301: a permanent redirect is cached by the browser indefinitely, and
 * this decision is one session old.
 *
 * NOT retired: /studio/<slug>/edit. That surface edits `chapters/*.txt`, the
 * NotebookLM source, which never reaches the PDF — a different text for a
 * different deliverable, deliberately left its own editor.
 *
 * Precedent: `/studio/<slug>/style` was retired the same way on 2026-07-19 (see
 * the note in scripts/site-health-smoke.mjs) for the same reason — a standalone
 * duplicate of a Composer surface with zero inbound links.
 */
import type { APIRoute } from "astro";

export const prerender = false;

export const GET: APIRoute = ({ params, redirect }) =>
  redirect(`/studio/${params.slug}/compose`, 302);
