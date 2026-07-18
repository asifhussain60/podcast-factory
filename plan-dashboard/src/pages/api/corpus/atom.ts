/**
 * PATCH /api/corpus/atom  — update text_en / content_level / tags for an existing atom
 * POST  /api/corpus/atom  — create a new atom
 *
 * Both accept JSON bodies; both return { ok, atom } on success or { ok: false, error } on failure.
 */

import type { APIRoute } from "astro";
import { updateAtom, createAtom } from "../../../lib/db/knowledge";

function apiError(msg: string, status = 400): Response {
  return new Response(JSON.stringify({ ok: false, error: msg }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function apiOk(data: unknown): Response {
  return new Response(JSON.stringify({ ok: true, atom: data }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

export const PATCH: APIRoute = async ({ request }) => {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON");
  }
  const { id, text_en, content_level, tags } = body as Record<string, unknown>;
  if (typeof id !== "string" || !id) return apiError("id is required");
  try {
    const atom = updateAtom(id, {
      text_en: typeof text_en === "string" ? text_en : undefined,
      content_level:
        content_level === null
          ? null
          : typeof content_level === "string"
            ? content_level
            : undefined,
      tags: Array.isArray(tags) ? (tags as string[]) : undefined,
    });
    return apiOk(atom);
  } catch (e) {
    return apiError(String(e), 400);
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON");
  }
  const { type, text_en, tradition, content_level, tags } = body as Record<
    string,
    unknown
  >;
  if (typeof type !== "string") return apiError("type is required");
  if (typeof text_en !== "string" || !text_en.trim())
    return apiError("text_en must be a non-empty string");
  if (typeof tradition !== "string") return apiError("tradition is required");
  try {
    const atom = createAtom({
      type,
      text_en,
      tradition,
      content_level:
        typeof content_level === "string" ? content_level : undefined,
      tags: Array.isArray(tags) ? (tags as string[]) : [],
    });
    return new Response(JSON.stringify({ ok: true, atom }), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    return apiError(String(e), 400);
  }
};
