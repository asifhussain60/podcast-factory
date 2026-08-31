/**
 * POST /api/brief/generate → write a commission brief and return its hand-off prompt.
 *
 * The cheapest write on the site, deliberately. It validates, writes two text
 * files, copies the staged source files somewhere durable, and stops. It does
 * NOT scaffold a content folder, create a branch, call Azure, or start the
 * orchestrator — the multi-hour run still begins only at /studio/new, after the
 * brief has been reviewed.
 *
 * Why the source files are COPIED: intake_staging.sweep_stale() deletes a staging
 * session after 24 hours, so a path into staging would rot inside a prompt that
 * is meant to be pasted days later. The copy under the brief is what the prompt
 * names, which also makes the brief folder self-contained.
 */
import type { APIRoute } from "astro";
import {
  appendFileSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  writeFileSync,
} from "node:fs";
import { basename, join } from "node:path";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { findContent, getRepoRoot } from "../../../lib/content-paths";
import { readChapters } from "./chapter-sources";
import { runPythonJson } from "../../../lib/intake-cli";
import {
  FIELDS,
  STEPS,
  completenessProblems,
  isVisible,
  type StepId,
} from "../../../lib/brief/fields";
import {
  chapterList,
  renderDocument,
  renderPrompt,
  settingsPairs,
  type BriefInput,
  type StagedFileRef,
} from "../../../lib/brief/render";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

interface Vocab {
  vocabularies: Record<string, { value: string; label: string }[]>;
  profileBucket: Record<string, string>;
}

/** The brief's own folder. Never joined from anything but a validated slug. */
export function briefDirFor(slug: string): string {
  return join(getRepoRoot(), "content", "_system", "briefs", slug);
}

async function loadVocab(): Promise<Vocab> {
  const v = (await runPythonJson("brief_vocabularies.py", ["get"])) as {
    vocabularies?: Vocab["vocabularies"];
    profile_bucket?: Record<string, string>;
  };
  return {
    vocabularies: v.vocabularies ?? {},
    profileBucket: v.profile_bucket ?? {},
  };
}

async function loadFormOptions(): Promise<Record<string, string[]>> {
  const o = (await runPythonJson("intake_form_options.py", ["get"])) as {
    options?: Record<string, string[]>;
  };
  return o.options ?? {};
}

/**
 * Re-check every answer server-side. The browser already blocks these, but a
 * value the pipeline would reject must not be able to reach a brief just
 * because the request did not come from the wizard.
 */
function validate(
  values: Record<string, string>,
  vocab: Vocab,
  options: Record<string, string[]>,
): string[] {
  const errors: string[] = [];
  const stepName = (s: StepId) =>
    STEPS.find((x) => x.id === s)?.title ?? `step ${s}`;

  for (const f of FIELDS) {
    if (!isVisible(f, values)) continue;
    const raw = (values[f.key] ?? "").trim();
    if (f.required && !raw) {
      errors.push(`${stepName(f.step)}: "${f.label}" is required.`);
      continue;
    }
    if (!raw) continue;
    if (f.pattern && !new RegExp(f.pattern).test(raw)) {
      errors.push(
        `${stepName(f.step)}: "${f.label}" is not in the expected form.`,
      );
    }
    if (f.maxLength && raw.length > f.maxLength) {
      errors.push(`${stepName(f.step)}: "${f.label}" is too long.`);
    }
    const allowed = f.vocab
      ? vocab.vocabularies[f.vocab]?.map((o) => o.value)
      : f.options
        ? options[f.options]
        : undefined;
    // A combo field accepts a typed value the list does not carry; a select does not.
    if (allowed && f.kind === "select" && !allowed.includes(raw)) {
      errors.push(
        `${stepName(f.step)}: "${f.label}" — ${raw} is not a value the pipeline accepts.`,
      );
    }
  }
  return errors;
}

/**
 * One JSONL line per attempt, refusals included.
 *
 * The refusals are the point. A brief that was never written leaves no trace on
 * disk, so the questions people cannot get past were invisible — which is
 * exactly what you need to know to improve the form. Appended, never rewritten,
 * and a logging failure can never take the endpoint down with it.
 */
function logAttempt(entry: Record<string, unknown>): void {
  try {
    const dir = join(getRepoRoot(), "content", "_system", "briefs");
    mkdirSync(dir, { recursive: true });
    appendFileSync(
      join(dir, "_log.jsonl"),
      JSON.stringify({ at: new Date().toISOString(), ...entry }) + "\n",
      "utf8",
    );
  } catch {
    /* the log is a diagnostic, never a reason to fail a request */
  }
}

export const POST: APIRoute = async ({ request }) => {
  let body: { values?: Record<string, string>; stagingToken?: string | null };
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const values = body.values ?? {};
  const slug = (values.slug ?? "").trim();
  if (!SLUG_RE.test(slug))
    return apiError("Folder name is missing or malformed");

  let vocab: Vocab;
  let options: Record<string, string[]>;
  try {
    [vocab, options] = await Promise.all([loadVocab(), loadFormOptions()]);
  } catch (e) {
    return apiServerError(
      `Could not read the pipeline vocabularies: ${String(e)}`,
    );
  }

  const errors = validate(values, vocab, options);
  if (errors.length) {
    logAttempt({ slug, ok: false, kind: "invalid", problems: errors });
    return apiError(errors.join(" "), 422);
  }

  const bucket = vocab.profileBucket[values.content_profile ?? ""] ?? "Islamic";
  const briefDir = briefDirFor(slug);
  const sourceDir = join(briefDir, "source");

  // Copy the staged files somewhere that outlives the 24-hour staging sweep.
  const sources: (StagedFileRef & { absolutePath: string })[] = [];
  const token = body.stagingToken ?? null;
  if (token) {
    try {
      const [pathOut, listOut] = await Promise.all([
        runPythonJson("intake_staging.py", ["path", token]) as Promise<{
          path: string;
        }>,
        runPythonJson("intake_staging.py", ["list", token]) as Promise<{
          files: { filename: string; stored_name: string; role: string }[];
        }>,
      ]);
      mkdirSync(sourceDir, { recursive: true });
      for (const f of listOut.files ?? []) {
        const from = join(pathOut.path, f.stored_name);
        if (!existsSync(from)) continue;
        const to = join(sourceDir, basename(f.filename));
        copyFileSync(from, to);
        sources.push({ filename: f.filename, role: f.role, absolutePath: to });
      }
    } catch (e) {
      return apiServerError(`Could not copy the staged files: ${String(e)}`);
    }
  }

  // The pipeline-readiness gate. Deliberately AFTER the staged files are known,
  // because half of what makes a commission complete is what was uploaded, and
  // deliberately BEFORE anything is written: a brief that exists is a brief
  // somebody will paste.
  // Whether the book already exists is RESOLVED FROM DISK, never taken from the
  // request: it decides whether a gate applies, and a gate a caller can switch
  // off by asserting something is not a gate.
  const existing = (await findContent(slug)) !== null;
  const incomplete = completenessProblems(values, {
    sourceCount: sources.length,
    roles: sources.map((f) => f.role),
    existing,
  });
  if (incomplete.length) {
    logAttempt({
      slug,
      ok: false,
      kind: "incomplete",
      profile: values.content_profile,
      medium: values.source_medium,
      existing,
      problems: incomplete.map((p) => p.reason),
    });
    return apiError(
      "The commission is not ready for the pipeline yet: " +
        incomplete.map((p) => p.reason).join("; ") +
        ".",
      422,
    );
  }

  // Human labels so the document reads in words, not tokens.
  const labels: Record<string, string> = {};
  for (const [field, opts] of Object.entries(vocab.vocabularies)) {
    for (const o of opts) {
      for (const f of FIELDS)
        if (f.vocab === field) labels[`${f.key}:${o.value}`] = o.label;
    }
  }

  // An existing book's sources are its OWN files. Nothing is staged when you
  // merely open it, so without this the prompt listed no source at all and a
  // fresh session had no idea where the recordings and transcripts were.
  if (existing && sources.length === 0) {
    const ref = await findContent(slug);
    if (ref) {
      for (const [sub, role] of [
        ["source", "source_recording"],
        ["transcripts", "timestamped_transcript"],
      ] as const) {
        try {
          for (const name of readdirSync(join(ref.dir, sub)).sort()) {
            if (name.startsWith(".")) continue;
            sources.push({
              filename: name,
              role,
              absolutePath: join(ref.dir, sub, name),
            });
          }
        } catch {
          /* a book without that folder simply contributes nothing */
        }
      }
    }
  }

  const input: BriefInput = {
    values,
    bucket,
    briefDir,
    repoRoot: getRepoRoot(),
    sources,
    generatedAt: new Date().toISOString(),
    labels,
    existing,
    // Chapters the contents page lists that the recordings never reach, from
    // the same file the form's Load button reads.
    uncovered: (readChapters(join(briefDir, "chapter-sources"))?.chapters ?? [])
      .filter((c) => c.covered === false)
      .map((c) => c.title),
  };

  const existed = existsSync(join(briefDir, "brief.md"));
  try {
    mkdirSync(briefDir, { recursive: true });
    const prompt = renderPrompt(input);
    writeFileSync(join(briefDir, "brief.md"), renderDocument(input), "utf8");
    writeFileSync(
      join(briefDir, "brief.json"),
      JSON.stringify(
        { slug, bucket, values, sources, generatedAt: input.generatedAt },
        null,
        2,
      ) + "\n",
      "utf8",
    );
    logAttempt({
      slug,
      ok: true,
      kind: existed ? "regenerated" : "created",
      profile: values.content_profile,
      medium: values.source_medium,
      bucket,
      segmentation: values.chapter_segmentation,
      chapters: chapterList(input).length,
      chapter_count_hint: values.chapter_count_hint,
      sources: sources.length,
      answered: settingsPairs(input).length,
    });
    return apiOk(
      {
        slug,
        bucket,
        briefDir,
        prompt,
        files: sources.map((s) => s.absolutePath),
        replaced: existed,
      },
      existed ? 200 : 201,
    );
  } catch (e) {
    return apiServerError(`Failed to write the brief: ${String(e)}`);
  }
};
