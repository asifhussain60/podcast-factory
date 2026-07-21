/**
 * citation-style.ts — the Citation & Quote style-family endpoint (Book Pipeline v2).
 *
 *   GET  /api/studio/citation-style?slug=
 *        → { slug, schema, family, translation_font, arabic_font }
 *   PUT  /api/studio/citation-style
 *        body { slug, family?, translation_font?, arabic_font? }
 *        Validates each field it is given against its fixed set, carries the other
 *        over from what is on disk, and writes book/citation-style.json. The prior
 *        file is backed up as .bak before the first overwrite.
 *
 * Model (locked 2026-07-13): ONE global family per book skins every passage type.
 * Extended 2026-07-21 with `translation_font` — the face the English rendering
 * under an Arabic quotation is set in — chosen in the same Citations tab. Either
 * field may be sent alone, because the two chip groups save independently.
 *
 * The artifact is JSON so the Node renderer (render-book-pdf.mjs) reads it with
 * stdlib and stamps body.style-<family>, body.tr-<font> and body.ar-<font>. Modeled on
 * visual-layout.ts: SLUG_RE validation, findContentDirSync resolution, .bak
 * safety, apiOk/apiError envelopes.
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
/** Plain, not Scholarly (locked with Asif 2026-07-21). Plain is now the family
 *  that sets an Arabic quotation as a centred maroon couplet with its rendering
 *  in a distinct face — the intended house look — so a new book should arrive in
 *  it rather than having to be switched into it. Books with a family already
 *  saved are untouched; this only changes what an unset book reads as. */
const DEFAULT_FAMILY: (typeof FAMILIES)[number] = "plain";

/** The English rendering face under an Arabic quotation. Mirrors
 *  TRANSLATION_FONTS in scripts/lib/book-html.mjs (a plain .mjs the renderer
 *  shares — this route cannot import its types, so the two lists change
 *  together). The field is OPTIONAL in the artifact: books written before it
 *  existed read as DEFAULT_FONT, so none needed rewriting. */
const FONTS = [
  "eb-garamond",
  "cormorant-garamond",
  "crimson-pro",
  "lora",
] as const;
const DEFAULT_FONT: (typeof FONTS)[number] = "eb-garamond";

/** The NON-Qur'anic Arabic face. Mirrors ARABIC_FONTS in book-html.mjs. Scripture
 *  is deliberately absent from this list: a run the Arabic audit resolved against
 *  the canonical mushaf is set in the KFGQPC Uthmanic script because that is the
 *  orthography it is written in, and that is a correctness rule rather than a
 *  choice the book gets to make. Optional in the artifact, like translation_font. */
const ARABIC_FONTS = ["scheherazade-new", "amiri"] as const;
const DEFAULT_ARABIC: (typeof ARABIC_FONTS)[number] = "scheherazade-new";

type Family = (typeof FAMILIES)[number];
type Font = (typeof FONTS)[number];
type ArabicFont = (typeof ARABIC_FONTS)[number];
const isFamily = (v: unknown): v is Family =>
  typeof v === "string" && (FAMILIES as readonly string[]).includes(v);
const isFont = (v: unknown): v is Font =>
  typeof v === "string" && (FONTS as readonly string[]).includes(v);
const isArabicFont = (v: unknown): v is ArabicFont =>
  typeof v === "string" && (ARABIC_FONTS as readonly string[]).includes(v);

export const GET: APIRoute = async ({ url }) => {
  const slug = String(url.searchParams.get("slug") ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  const target = join(bookDir, "book", "citation-style.json");
  if (!existsSync(target))
    return apiOk({
      slug,
      schema: SCHEMA,
      family: DEFAULT_FAMILY,
      translation_font: DEFAULT_FONT,
      arabic_font: DEFAULT_ARABIC,
    });
  try {
    const raw = JSON.parse(readFileSync(target, "utf8"));
    const family = isFamily(raw?.family) ? raw.family : DEFAULT_FAMILY;
    const font = isFont(raw?.translation_font)
      ? raw.translation_font
      : DEFAULT_FONT;
    const arabic = isArabicFont(raw?.arabic_font)
      ? raw.arabic_font
      : DEFAULT_ARABIC;
    return apiOk({
      slug,
      schema: SCHEMA,
      family,
      translation_font: font,
      arabic_font: arabic,
    });
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

  // Either field may be sent alone — the two chip groups in the Citations tab
  // save independently, and a font-only save must not wipe the family (or the
  // reverse). Absent fields are carried over from what is already on disk.
  const hasFamily = body.family !== undefined;
  const hasFont = body.translation_font !== undefined;
  const hasArabic = body.arabic_font !== undefined;
  if (!hasFamily && !hasFont && !hasArabic)
    return apiError(
      "Nothing to save (expected family, translation_font and/or arabic_font)",
    );
  if (hasFamily && !isFamily(body.family))
    return apiError(`Invalid family (expected one of: ${FAMILIES.join(", ")})`);
  if (hasFont && !isFont(body.translation_font))
    return apiError(
      `Invalid translation_font (expected one of: ${FONTS.join(", ")})`,
    );
  if (hasArabic && !isArabicFont(body.arabic_font))
    return apiError(
      `Invalid arabic_font (expected one of: ${ARABIC_FONTS.join(", ")})`,
    );

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);

  try {
    const bookSubdir = join(bookDir, "book");
    mkdirSync(bookSubdir, { recursive: true });
    const target = join(bookSubdir, "citation-style.json");
    const backup = `${target}.bak`;
    if (existsSync(target) && !existsSync(backup)) copyFileSync(target, backup);

    let current: Record<string, unknown> = {};
    if (existsSync(target)) {
      try {
        current = JSON.parse(readFileSync(target, "utf8"));
      } catch {
        current = {}; // unreadable artifact: rewrite it rather than fail the save
      }
    }
    const family = hasFamily
      ? (body.family as Family)
      : isFamily(current.family)
        ? current.family
        : DEFAULT_FAMILY;
    const translationFont = hasFont
      ? (body.translation_font as Font)
      : isFont(current.translation_font)
        ? current.translation_font
        : DEFAULT_FONT;

    const arabicFont = hasArabic
      ? (body.arabic_font as ArabicFont)
      : isArabicFont(current.arabic_font)
        ? current.arabic_font
        : DEFAULT_ARABIC;

    writeFileSync(
      target,
      JSON.stringify(
        {
          schema: SCHEMA,
          family,
          translation_font: translationFont,
          arabic_font: arabicFont,
        },
        null,
        2,
      ) + "\n",
      "utf8",
    );
    return apiOk({
      slug,
      family,
      translation_font: translationFont,
      arabic_font: arabicFont,
    });
  } catch (e) {
    return apiServerError(`Failed to write citation-style.json: ${String(e)}`);
  }
};
