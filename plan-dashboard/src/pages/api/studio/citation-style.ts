/**
 * citation-style.ts — the Citation & Quote style-family endpoint (Book Pipeline v2).
 *
 *   GET  /api/studio/citation-style?slug=   → { slug, family }
 *   PUT  /api/studio/citation-style  body { slug, family }
 *        Validates family against the fixed set and writes book/citation-style.json.
 *        The prior file is backed up as .bak before the first overwrite.
 *
 * Model (locked 2026-07-13): ONE global family per book skins every passage type.
 * The artifact is JSON so the Node renderer (render-book-pdf.mjs) reads it with
 * stdlib and stamps body.style-<family>. Modeled on visual-layout.ts: SLUG_RE
 * validation, findContentDirSync resolution, .bak safety, apiOk/apiError envelopes.
 */
import type { APIRoute } from "astro";
import {
  writeFileSync,
  readFileSync,
  existsSync,
  copyFileSync,
  mkdirSync,
} from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const SCHEMA = "book.citation-style/v1";
const FAMILIES = ["plain", "scholarly", "elegant"] as const;
const DEFAULT_FAMILY: (typeof FAMILIES)[number] = "scholarly";

type Family = (typeof FAMILIES)[number];
const isFamily = (v: unknown): v is Family =>
  typeof v === "string" && (FAMILIES as readonly string[]).includes(v);

export const GET: APIRoute = async ({ url }) => {
  const slug = String(url.searchParams.get("slug") ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  const target = join(bookDir, "book", "citation-style.json");
  if (!existsSync(target))
    return apiOk({ slug, schema: SCHEMA, family: DEFAULT_FAMILY });
  try {
    const raw = JSON.parse(readFileSync(target, "utf8"));
    const family = isFamily(raw?.family) ? raw.family : DEFAULT_FAMILY;
    return apiOk({ slug, schema: SCHEMA, family });
  } catch (e) {
    return apiServerError(`Failed to read citation-style.json: ${String(e)}`);
  }
};

export const PUT: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const slug = String(body.slug ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!isFamily(body.family))
    return apiError(`Invalid family (expected one of: ${FAMILIES.join(", ")})`);

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);

  try {
    const bookSubdir = join(bookDir, "book");
    mkdirSync(bookSubdir, { recursive: true });
    const target = join(bookSubdir, "citation-style.json");
    const backup = `${target}.bak`;
    if (existsSync(target) && !existsSync(backup)) copyFileSync(target, backup);

    writeFileSync(
      target,
      JSON.stringify({ schema: SCHEMA, family: body.family }, null, 2) + "\n",
      "utf8",
    );
    return apiOk({ slug, family: body.family });
  } catch (e) {
    return apiServerError(`Failed to write citation-style.json: ${String(e)}`);
  }
};
