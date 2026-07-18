/**
 * stage-draft.ts — per-chapter, per-stage DRAFT content for the Studio editor.
 *
 * A draft is the "retained but not yet permanent" layer between editing and
 * approval. The editor autosaves the reviewer's in-progress edits here on every
 * change; `loadStageText` prefers a draft over the canonical artifact so the
 * draft is what the editor shows on return; and approval (`save-stage`) promotes
 * the draft to the real `chapters/<id>.txt` and deletes it.
 *
 * Drafts live at content/<bucket>/<slug>/_system/drafts/<chapter>/<stage>.md and
 * are git-ignored. They are visible ONLY through the Studio editor's workspace
 * loader — the public reader (lib/reader/chapters) and the publish/NotebookLM
 * path both read chapters/<id>.txt directly, so an unapproved draft can never
 * reach the published book, the audio upload, or the orchestrator.
 *
 * Mirrors the shape of stage-review.ts (the sibling approval-record store).
 */
import {
  readFileSync,
  writeFileSync,
  existsSync,
  mkdirSync,
  rmSync,
} from "node:fs";
import { join, dirname } from "node:path";
import { findContentDirSync, getRepoRoot } from "../content-paths";

function draftPath(slug: string, chapter: string, stage: string): string {
  // Resolve via the type-first resolver; fall back to the canonical Islamic path.
  const dir =
    findContentDirSync(slug) ?? join(getRepoRoot(), "content", "Islamic", slug);
  return join(dir, "_system", "drafts", chapter, `${stage}.md`);
}

/** Read the draft for a stage, or null when none exists. */
export function readDraft(
  slug: string,
  chapter: string,
  stage: string,
): string | null {
  const p = draftPath(slug, chapter, stage);
  if (!existsSync(p)) return null;
  try {
    return readFileSync(p, "utf8");
  } catch {
    return null;
  }
}

/** Write (create or overwrite) the draft for a stage. */
export function writeDraft(
  slug: string,
  chapter: string,
  stage: string,
  content: string,
): void {
  const p = draftPath(slug, chapter, stage);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, content, "utf8");
}

/** Delete a stage's draft. Returns true if a draft existed and was removed. */
export function deleteDraft(
  slug: string,
  chapter: string,
  stage: string,
): boolean {
  const p = draftPath(slug, chapter, stage);
  if (!existsSync(p)) return false;
  try {
    rmSync(p);
    return true;
  } catch {
    return false;
  }
}

/** Cheap existence check (used to seed the editor's on-load draft state). */
export function hasDraft(
  slug: string,
  chapter: string,
  stage: string,
): boolean {
  return existsSync(draftPath(slug, chapter, stage));
}
