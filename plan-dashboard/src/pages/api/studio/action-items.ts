/**
 * GET    /api/studio/action-items?book=<slug>&chapter=<id>
 *   Returns { ok, items: ActionItem[] }
 *
 * POST   /api/studio/action-items
 *   Body: { book, chapter, scope, paraOrdinal, termText?, anchorText?, actionKind, note? }
 *   Upserts one action item (re-stamping the same target+kind is a no-op).
 *   Returns { ok, item: ActionItem }
 *
 * DELETE /api/studio/action-items
 *   Body: { book, chapter, id }
 *   Returns { ok, removed: boolean }
 *
 * Deferred AI action-item queue: the editor stamps marks here; a later CLI pass
 * drains pending rows and writes results back. Mirrors section-depth.ts.
 */

import type { APIRoute } from "astro";
import {
  getActionItems,
  upsertActionItem,
  deleteActionItem,
  KnowledgeDbUnavailableError,
} from "../../../lib/db/knowledge";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

// A machine without knowledge.db is not a broken server — the database is built by
// the pipeline and is absent on a fresh clone by design. Reads already degrade to
// empty; a WRITE must say so distinguishably, so the UI can disable the control
// instead of showing the user a 500 it can do nothing about.
const failed = (e: unknown) =>
  e instanceof KnowledgeDbUnavailableError
    ? json({ ok: false, error: e.message, code: e.code }, 503)
    : json({ ok: false, error: String(e) }, 500);

const ALLOWED_KINDS = new Set([
  "etymology",
  "rewrite",
  "expand",
  "condense",
  "simplify",
  "define",
  "xref",
  "addcorpus",
  "visualize",
]);
const ALLOWED_SCOPES = new Set(["paragraph", "term"]);

export const GET: APIRoute = ({ request }) => {
  try {
    const url = new URL(request.url);
    const book = url.searchParams.get("book") ?? "";
    const chapter = url.searchParams.get("chapter") ?? "";
    if (!book || !chapter)
      return json(
        { ok: false, error: "book and chapter params required" },
        400,
      );
    return json({ ok: true, items: getActionItems(book, chapter) });
  } catch (e) {
    return failed(e);
  }
};

export const POST: APIRoute = async ({ request }) => {
  try {
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return json({ ok: false, error: "Invalid JSON" }, 400);
    }
    const {
      book,
      chapter,
      scope,
      paraOrdinal,
      termText,
      anchorText,
      actionKind,
      note,
    } = body as Record<string, unknown>;
    if (typeof book !== "string" || !book)
      return json({ ok: false, error: "book required" }, 400);
    if (typeof chapter !== "string" || !chapter)
      return json({ ok: false, error: "chapter required" }, 400);
    if (typeof scope !== "string" || !ALLOWED_SCOPES.has(scope))
      return json({ ok: false, error: "scope must be paragraph|term" }, 400);
    if (typeof paraOrdinal !== "number")
      return json({ ok: false, error: "paraOrdinal (number) required" }, 400);
    if (typeof actionKind !== "string" || !ALLOWED_KINDS.has(actionKind))
      return json(
        { ok: false, error: `unknown actionKind: ${String(actionKind)}` },
        400,
      );
    const item = upsertActionItem({
      bookSlug: book,
      chapterId: chapter,
      scope: scope as "paragraph" | "term",
      paraOrdinal,
      termText: typeof termText === "string" ? termText : "",
      anchorText: typeof anchorText === "string" ? anchorText : "",
      actionKind,
      note: typeof note === "string" ? note : undefined,
    });
    return json({ ok: true, item });
  } catch (e) {
    return failed(e);
  }
};

export const DELETE: APIRoute = async ({ request }) => {
  try {
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return json({ ok: false, error: "Invalid JSON" }, 400);
    }
    const { book, chapter, id } = body as Record<string, unknown>;
    if (typeof book !== "string" || !book)
      return json({ ok: false, error: "book required" }, 400);
    if (typeof chapter !== "string" || !chapter)
      return json({ ok: false, error: "chapter required" }, 400);
    if (typeof id !== "number")
      return json({ ok: false, error: "id (number) required" }, 400);
    return json({ ok: true, removed: deleteActionItem(book, chapter, id) });
  } catch (e) {
    return failed(e);
  }
};
