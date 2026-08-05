/**
 * POST /api/studio/denoise
 *
 * Pattern-based "noise" removal across a book's canonical chapter text files
 * (content/<Bucket>/<slug>/chapters/<id>.txt — the same source the Studio editor
 * reads and the reader renders). The Studio "Noise" action selects a recurring
 * artifact (a page header, an OCR scar, a stray marker), generalises it into a
 * regular-expression PATTERN, then removes every match book-wide.
 *
 * Body: {
 *   slug:    string,
 *   scope:   'chapter' | 'book',
 *   chapter?: string,                 // required when scope === 'chapter'
 *   pattern: string,                  // a JS regular-expression source (no //)
 *   flags?:  string,                  // default 'g'; 'g' is always forced on
 *   apply?:  boolean,                 // false (default) = preview/count only, no writes
 *   allowArabic?: boolean             // false blocks patterns that would remove Arabic script
 * }
 * Returns: {
 *   ok, applied, total,
 *   results: { chapter, count, samples: string[] }[]   // up to 3 distinct hits per chapter
 * }
 *
 * SAFETY: this is a destructive, potentially book-wide delete, so the caller is
 * expected to PREVIEW first — the per-chapter `samples` show exactly what would be
 * removed. On apply each changed file is copied to <id>.txt.bak (one-step local
 * undo) before overwrite; the files are git-tracked, so git is the deeper net.
 * Patterns that match the empty string are rejected (they would "match" endlessly
 * without removing anything meaningful).
 */

import type { APIRoute } from "astro";
import {
  readFileSync,
  writeFileSync,
  copyFileSync,
  existsSync,
  readdirSync,
} from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";

export const prerender = false;

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const ALLOWED_FLAGS = /^[gimsuy]*$/;
const ARABIC_RE =
  /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;

/** Remove every match of `re` from `text`, counting hits and sampling up to 3
 *  distinct matched strings (for the preview). `re` must carry the global flag. */
function denoiseText(
  text: string,
  re: RegExp,
): { text: string; count: number; samples: string[] } {
  let count = 0;
  const samples: string[] = [];
  const out = text.replace(re, (m: string) => {
    if (m === "") return m; // belt-and-suspenders; empty-matching patterns are rejected earlier
    count += 1;
    if (samples.length < 3 && !samples.includes(m)) samples.push(m);
    return "";
  });
  return { text: out, count, samples };
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "Invalid JSON" }, 400);
  }

  const slug = String(body.slug ?? "").trim();
  const scope = String(body.scope ?? "").trim();
  const chapter = String(body.chapter ?? "").trim();
  const apply = body.apply === true;
  const allowArabic = body.allowArabic === true;
  const pattern = String(body.pattern ?? "");
  let flags = String(body.flags ?? "g");

  if (!SLUG_RE.test(slug))
    return json({ ok: false, error: "Invalid slug" }, 400);
  if (scope !== "chapter" && scope !== "book")
    return json({ ok: false, error: "scope must be chapter|book" }, 400);
  if (pattern.trim() === "")
    return json({ ok: false, error: "pattern is required" }, 400);
  if (!ALLOWED_FLAGS.test(flags))
    return json({ ok: false, error: "invalid regex flags" }, 400);
  if (!flags.includes("g")) flags += "g";

  try {
    new RegExp(pattern, flags);
  } catch (e) {
    return json({ ok: false, error: `invalid pattern: ${String(e)}` }, 400);
  }
  // Reject patterns that can match the empty string — they "remove" nothing but
  // count at every position, which is never what a noise-strip intends.
  if (new RegExp(pattern).test("")) {
    return json(
      {
        ok: false,
        error: "pattern matches an empty string — make it more specific",
      },
      400,
    );
  }

  const dir = findContentDirSync(slug);
  if (!dir) return json({ ok: false, error: `book not found: ${slug}` }, 404);
  const chaptersDir = join(dir, "chapters");
  if (!existsSync(chaptersDir))
    return json(
      { ok: false, error: "no chapters/ directory for this book" },
      404,
    );

  // Resolve the target file(s).
  let files: string[];
  if (scope === "chapter") {
    if (!SLUG_RE.test(chapter))
      return json({ ok: false, error: "Invalid chapter slug" }, 400);
    const f = join(chaptersDir, `${chapter}.txt`);
    if (!existsSync(f))
      return json(
        { ok: false, error: `chapter file not found: ${chapter}.txt` },
        404,
      );
    files = [f];
  } else {
    files = readdirSync(chaptersDir)
      .filter((n) => n.endsWith(".txt") && !n.endsWith(".bak"))
      .sort()
      .map((n) => join(chaptersDir, n));
  }

  try {
    const results: { chapter: string; count: number; samples: string[] }[] = [];
    let total = 0;
    for (const f of files) {
      const id = f.slice(f.lastIndexOf("/") + 1).replace(/\.txt$/, "");
      const text = readFileSync(f, "utf8");
      // Fresh regex per file so lastIndex never leaks between iterations.
      const fileRe = new RegExp(pattern, flags);
      const { text: next, count, samples } = denoiseText(text, fileRe);
      if (count > 0) {
        if (!allowArabic && samples.some((sample) => ARABIC_RE.test(sample))) {
          return json(
            {
              ok: false,
              error:
                "pattern would remove Arabic script; Arabic terms are preserved for pronunciation review",
              chapter: id,
              samples,
            },
            400,
          );
        }
        results.push({ chapter: id, count, samples });
        total += count;
        if (apply && next !== text) {
          copyFileSync(f, `${f}.bak`); // one-step local undo (gitignored)
          writeFileSync(f, next, "utf8");
        }
      }
    }
    return json({ ok: true, applied: apply, total, results });
  } catch (e) {
    return json({ ok: false, error: String(e) }, 500);
  }
};
