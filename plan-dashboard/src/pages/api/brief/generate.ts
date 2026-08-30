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
import { copyFileSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { basename, join } from "node:path";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { getRepoRoot } from "../../../lib/content-paths";
import { runPythonJson } from "../../../lib/intake-cli";
import {
  FIELDS,
  STEPS,
  isVisible,
  type StepId,
} from "../../../lib/brief/fields";
import {
  renderDocument,
  renderPrompt,
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
  if (errors.length) return apiError(errors.join(" "), 422);

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

  // Human labels so the document reads in words, not tokens.
  const labels: Record<string, string> = {};
  for (const [field, opts] of Object.entries(vocab.vocabularies)) {
    for (const o of opts) {
      for (const f of FIELDS)
        if (f.vocab === field) labels[`${f.key}:${o.value}`] = o.label;
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
