/**
 * GET  /api/brief/content/<slug> → that book's settings, as the form's fields.
 * POST /api/brief/content/<slug> { changes } → write the changed ones back.
 *
 * The store is the two YAML files on disk, not the Library's database: D1 has
 * columns for seven of these settings and is written one-way by the publish
 * step, so an edit here reaches the live site at the next publish and not before.
 *
 * The POST writes ONLY the fields it is given, patched line by line, so
 * comments and the many keys this form does not know about are left alone.
 * Structural fields are refused rather than silently ignored — moving a book
 * between shelves is a migration, not a form save.
 */
import type { APIRoute } from "astro";
import {
  apiOk,
  apiError,
  apiNotFound,
  apiServerError,
} from "../../../../lib/api-responses";
import {
  findContentDirSync,
  getRepoRoot,
  listContent,
} from "../../../../lib/content-paths";
import { runPythonJson } from "../../../../lib/intake-cli";
import { renderSavedPrompt } from "../../../../lib/brief/render";
import {
  FIELD_FILES,
  LOCKED_FOR_EXISTING,
  loadBook,
  saveBook,
} from "../../../../lib/brief/store";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

async function locate(slug: string) {
  const dir = findContentDirSync(slug);
  if (!dir) return null;
  const refs = await listContent();
  const ref = refs.find((r) => r.slug === slug);
  return {
    dir,
    bucket: ref?.bucket ?? "Islamic",
    status: ref?.status ?? "draft",
  };
}

export const GET: APIRoute = async ({ params }) => {
  const slug = params.slug ?? "";
  if (!SLUG_RE.test(slug)) return apiError("malformed slug");
  try {
    const at = await locate(slug);
    if (!at) return apiNotFound(`no content named ${slug}`);
    const book = await loadBook(slug, at.bucket, at.dir);
    return apiOk({
      ...book,
      status: at.status,
      locked: [...LOCKED_FOR_EXISTING],
    });
  } catch (e) {
    return apiServerError(`Could not read ${slug}: ${String(e)}`);
  }
};

export const POST: APIRoute = async ({ params, request }) => {
  const slug = params.slug ?? "";
  if (!SLUG_RE.test(slug)) return apiError("malformed slug");

  let body: { changes?: Record<string, string> };
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }
  const changes = body.changes ?? {};
  if (Object.keys(changes).length === 0) return apiError("no changes supplied");

  const unknown = Object.keys(changes).filter(
    (k) => !FIELD_FILES[k] && !LOCKED_FOR_EXISTING.has(k),
  );
  if (unknown.length) {
    return apiError(`not stored settings: ${unknown.join(", ")}`);
  }

  // Values are re-checked against the pipeline's own vocabularies, so a request
  // that did not come from the form cannot put a value on disk that the
  // pipeline would later reject.
  let allowed: Record<string, Set<string>>;
  try {
    const v = (await runPythonJson("brief_vocabularies.py", ["get"])) as {
      vocabularies?: Record<string, { value: string }[]>;
    };
    allowed = Object.fromEntries(
      Object.entries(v.vocabularies ?? {}).map(([k, opts]) => [
        k,
        new Set(opts.map((o) => o.value)),
      ]),
    );
  } catch (e) {
    return apiServerError(`Could not read the vocabularies: ${String(e)}`);
  }

  const VOCAB_OF: Record<string, string> = {
    study_track: "study_track",
    archetype: "archetype",
    content_level: "content_level",
    density: "density",
    category: "category",
    narrative_frame: "narrative_frame",
    autonomy: "autonomy",
    book_voice: "book_voice",
    book_augmentation: "book_augmentation",
    book_visuals: "book_visuals",
    deliverable_mode: "deliverable_mode",
    slide_deck_mode: "slide_deck_mode",
    source_fidelity: "source_fidelity",
  };
  for (const [field, value] of Object.entries(changes)) {
    const vocab = VOCAB_OF[field];
    if (!vocab || value === "") continue;
    if (allowed[vocab] && !allowed[vocab].has(value)) {
      return apiError(
        `${field}: "${value}" is not a value the pipeline accepts`,
        422,
      );
    }
  }

  try {
    const at = await locate(slug);
    if (!at) return apiNotFound(`no content named ${slug}`);
    const result = await saveBook(at.dir, changes);
    // Re-read rather than echoing `changes`: the prompt has to describe the
    // book as it now IS, and a field the save skipped must not appear in it as
    // though it had been written.
    const after = await loadBook(slug, at.bucket, at.dir);
    const prompt = renderSavedPrompt({
      slug,
      dir: at.dir,
      bucket: at.bucket,
      repoRoot: getRepoRoot(),
      values: after.values,
      changed: result.written.map((w) => w.field),
    });
    return apiOk({ slug, dir: at.dir, ...result, prompt });
  } catch (e) {
    return apiServerError(`Could not save ${slug}: ${String(e)}`);
  }
};
