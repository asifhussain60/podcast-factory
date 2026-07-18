/**
 * save-stage.ts — POST /api/studio/save-stage
 *
 * Writes the editor's content back to the artifact the editor READ this stage
 * from. The target is resolved by mirroring book-workspace.loadStageText, so the
 * write always lands where the read came from — across both the canonical
 * `_stages/<chapter>/<stage>.md` layout AND bucket-layout books that have no
 * `_stages/` at all (e.g. content/Islamic/<slug>), where the editable
 * "augmented" stage is the plain `chapters/<chapter>.txt` source.
 *
 * Body: { slug, chapter, stage, content, comments? }
 *   content  — markdown text (from StudioPoc's simple PM serializer)
 *   comments — optional Record<string, string> (paragraph index → comment text)
 *
 * The existing artifact is preserved as <file>.bak before overwrite so the
 * original is always recoverable from disk (files are also git-tracked).
 */
import type { APIRoute } from "astro";
import { writeFileSync, existsSync, copyFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { deleteDraft } from "../../../lib/reader/stage-draft";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const ALLOWED_STAGES = new Set([
  "source",
  "core",
  "denoised",
  "normalized",
  "augmented",
  "narrator",
]);

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const slug = String(body.slug ?? "").trim();
  const chapter = String(body.chapter ?? "").trim();
  const stage = String(body.stage ?? "").trim();
  const content = String(body.content ?? "").trim();
  const comments = (body.comments ?? {}) as Record<string, string>;

  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!SLUG_RE.test(chapter)) return apiError("Invalid chapter slug");
  if (!ALLOWED_STAGES.has(stage)) return apiError(`Unknown stage "${stage}"`);
  if (!content) return apiError("Content is empty — nothing to save");

  // Resolve the book dir (bucket-aware, with legacy drafts/published fallback).
  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);

  // Mirror book-workspace.loadStageText: write back to the artifact the editor
  // read this stage from.
  const stagesChapterDir = join(bookDir, "_stages", chapter);
  const resolveTarget = (): string | null => {
    if (stage === "narrator") {
      const clean = join(stagesChapterDir, "additions-narrator-clean.md");
      if (existsSync(clean)) return clean;
      if (existsSync(stagesChapterDir))
        return join(stagesChapterDir, "additions-narrator.md");
      return null;
    }
    for (const ext of ["md", "txt"]) {
      const p = join(stagesChapterDir, `${stage}.${ext}`);
      if (existsSync(p)) return p;
    }
    // Augmented fallback to the canonical chapter source — matches the read path
    // for books with no _stages/ artifact for this chapter.
    if (stage === "augmented") {
      const chapterTxt = join(bookDir, "chapters", `${chapter}.txt`);
      if (existsSync(chapterTxt)) return chapterTxt;
    }
    // Otherwise the canonical _stages artifact, but only if that chapter dir exists.
    if (existsSync(stagesChapterDir))
      return join(stagesChapterDir, `${stage}.md`);
    return null;
  };

  try {
    const targetPath = resolveTarget();
    if (!targetPath) {
      return apiError(
        `No writable artifact for stage "${stage}" in chapter "${chapter}"`,
        404,
      );
    }

    // Backup original before overwrite (idempotent — only if .bak doesn't exist yet).
    const backupPath = `${targetPath}.bak`;
    if (existsSync(targetPath) && !existsSync(backupPath)) {
      copyFileSync(targetPath, backupPath);
    }

    writeFileSync(targetPath, content, "utf8");

    // Approval promotes the draft to the canonical artifact, so the draft is now
    // spent — remove it. Subsequent loads read the canonical (committed) text.
    deleteDraft(slug, chapter, stage);

    // Comments side-file (write-only today): kept out of the content tree under
    // _system/, chapter+stage-scoped, alongside the review/ records.
    if (Object.keys(comments).length > 0) {
      const commentsDir = join(bookDir, "_system", "stage-comments");
      mkdirSync(commentsDir, { recursive: true });
      writeFileSync(
        join(commentsDir, `${chapter}-${stage}.json`),
        JSON.stringify({ slug, chapter, stage, comments }, null, 2) + "\n",
        "utf8",
      );
    }

    return apiOk({
      slug,
      chapter,
      stage,
      path: targetPath.slice(bookDir.length + 1), // relative to the book dir
      backed_up: existsSync(backupPath),
    });
  } catch (e) {
    return apiServerError(`Failed to write stage file: ${String(e)}`);
  }
};
