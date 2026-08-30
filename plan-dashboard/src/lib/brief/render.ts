/**
 * render.ts — the ONE place a commission is turned into words.
 *
 * Both outputs of the Intake wizard come from this file: the requirements
 * document written to disk, and the hand-off prompt shown on screen for pasting
 * into Claude Code or Cowork. They are built by two functions over one input so
 * what you copy and what is stored cannot disagree — the same single-builder
 * discipline `_notebooklm_table.py` keeps for upload tables.
 *
 * Neither function reads the filesystem or the network. Callers resolve paths
 * and hand them in, which is what lets the API route and the browser render the
 * identical prompt.
 */
import { FIELDS, FIELDS_BY_KEY, STEPS, isVisible, type StepId } from "./fields";
import { humanizeToken } from "./humanize";

export interface StagedFileRef {
  filename: string;
  role: string;
}

export interface BriefInput {
  /** Answers keyed by field, plus the voice-picker's flat keys. */
  values: Record<string, string>;
  /** Bucket resolved from the content profile by the pipeline registry. */
  bucket: string;
  /** Absolute path of the brief's own folder. */
  briefDir: string;
  /** Absolute path of the repo root. */
  repoRoot: string;
  /** Files copied into the brief, with the durable absolute path of each. */
  sources: (StagedFileRef & { absolutePath: string })[];
  /** ISO timestamp; supplied by the caller so the two renders match exactly. */
  generatedAt: string;
  /** Human-readable option labels, keyed `<field>:<value>`, when known. */
  labels?: Record<string, string>;
}

/** A pipeline token as a reader should see it. Vocabulary fields carry a real
 *  label from their registry; the rest are humanised the same way the intake
 *  form humanises them, so the document never prints a bare snake_case token. */
function label(input: BriefInput, key: string, value: string): string {
  const known = input.labels?.[`${key}:${value}`];
  if (known) return known;
  const field = FIELDS_BY_KEY[key];
  if (field?.kind === "switch") return value === "true" ? "Yes" : "No";
  return humanizeToken(key, value);
}

/** Answered, currently-visible fields for one step, in definition order. */
function answered(input: BriefInput, step: StepId) {
  return FIELDS.filter(
    (f) =>
      f.step === step &&
      f.kind !== "textarea" &&
      isVisible(f, input.values) &&
      (input.values[f.key] ?? "").trim() !== "",
  );
}

/** Voice-picker and any other keys that carry no FieldDef of their own. */
function extraSettings(input: BriefInput): [string, string][] {
  return Object.entries(input.values)
    .filter(([k, v]) => !FIELDS_BY_KEY[k] && String(v ?? "").trim() !== "")
    .sort(([a], [b]) => a.localeCompare(b));
}

/** Every setting as the pipeline reads it: token keys, token values. */
export function settingsPairs(input: BriefInput): [string, string][] {
  const fromFields = FIELDS.filter(
    (f) =>
      f.kind !== "textarea" &&
      !f.formOnly &&
      isVisible(f, input.values) &&
      (input.values[f.key] ?? "").trim() !== "",
  ).map((f) => [f.key, input.values[f.key]] as [string, string]);
  return [...fromFields, ...extraSettings(input)];
}

/** The requirements document — what Asif and Claude read and refine together. */
export function renderDocument(input: BriefInput): string {
  const { values } = input;
  const title = values.title || values.slug || "Untitled";
  const out: string[] = [];

  out.push(`# ${title}`);
  out.push("");
  out.push(
    `A commission for the podcast factory, written from the Intake form on ${input.generatedAt}. ` +
      `Nothing has been created yet — this document is the brief, not the book.`,
  );
  out.push("");
  out.push(`- **Folder name:** \`${values.slug ?? ""}\``);
  out.push(`- **Shelf:** ${input.bucket}`);
  out.push(
    `- **Branch it will run on:** \`${input.bucket}/${values.slug ?? ""}\``,
  );
  out.push(`- **Brief folder:** \`${input.briefDir}\``);
  out.push("");

  out.push("## The source files");
  out.push("");
  if (input.sources.length === 0) {
    out.push("_No source file was supplied._");
  } else {
    for (const s of input.sources) {
      out.push(`- **${s.filename}** — ${label(input, "role", s.role)}`);
      out.push(`  - \`${s.absolutePath}\``);
    }
    out.push("");
    out.push(
      "These are copies kept with the brief, so the paths above stay valid. " +
        "The staging area they were uploaded to is swept after a day.",
    );
  }
  out.push("");

  for (const step of STEPS) {
    const rows = answered(input, step.id);
    if (rows.length === 0) continue;
    out.push(`## ${step.title}`);
    out.push("");
    out.push("| Decision | Answer | As the pipeline reads it |");
    out.push("|---|---|---|");
    for (const f of rows) {
      const raw = values[f.key];
      // A form-only question has no pipeline key to quote in the third column.
      const token = f.formOnly ? "—" : `\`${f.key}: ${raw}\``;
      out.push(`| ${f.label} | ${label(input, f.key, raw)} | ${token} |`);
    }
    out.push("");
  }

  const extras = extraSettings(input);
  if (extras.length) {
    out.push("## Voices and other settings");
    out.push("");
    out.push("| Setting | Value |");
    out.push("|---|---|");
    for (const [k, v] of extras) out.push(`| \`${k}\` | ${v} |`);
    out.push("");
  }

  if ((values.notes ?? "").trim()) {
    out.push("## In Asif's words");
    out.push("");
    out.push(values.notes.trim());
    out.push("");
  }

  out.push("## Still to settle");
  out.push("");
  out.push(
    "Claude fills this in when reviewing the brief: anything above that looks wrong for " +
      "this source, anything the form could not ask, and the questions worth answering " +
      "before the pipeline runs.",
  );
  out.push("");
  return out.join("\n");
}

/** The self-contained hand-off prompt. Paste into Claude Code or Cowork. */
export function renderPrompt(input: BriefInput): string {
  const { values } = input;
  const slug = values.slug ?? "";
  const branch = `${input.bucket}/${slug}`;
  const primary =
    input.sources.find((s) => s.role === "primary_source") ?? input.sources[0];

  const lines: string[] = [];
  lines.push(
    `I want to process a new piece of content through the podcast factory. ` +
      `The repo is at ${input.repoRoot} — read its CLAUDE.md first, then run ` +
      `\`bash scripts/start-session.sh\`.`,
  );
  lines.push("");
  lines.push(
    `The commission is written up at ${input.briefDir}/brief.md — read it.`,
  );
  lines.push("");
  lines.push("Here is the same thing in short:");
  lines.push("");
  lines.push(`- Title: ${values.title ?? ""}`);
  if (values.author) lines.push(`- Author: ${values.author}`);
  lines.push(`- Folder name: ${slug}`);
  lines.push(`- Shelf: ${input.bucket}`);
  lines.push(`- Branch to create off develop: ${branch}`);
  if (primary) lines.push(`- Source file: ${primary.absolutePath}`);
  for (const s of input.sources) {
    if (s === primary) continue;
    lines.push(`- Also supplied (${s.role}): ${s.absolutePath}`);
  }
  lines.push("");
  lines.push("Settings, exactly as the pipeline reads them:");
  lines.push("");
  for (const [k, v] of settingsPairs(input)) lines.push(`- ${k}: ${v}`);
  lines.push("");
  if ((values.notes ?? "").trim()) {
    lines.push("What I said I wanted:");
    lines.push("");
    lines.push(values.notes.trim());
    lines.push("");
  }
  lines.push(
    "Before anything runs: confirm these settings back to me, tell me anything that " +
      "looks wrong for this source, and ask about whatever the form could not. " +
      "The narrative frame in particular is a property of the source — check it " +
      "against how the text actually opens rather than trusting the form.",
  );
  lines.push("");
  lines.push(
    "Then take it from intake through the pipeline the way this repo does it, " +
      "stopping at the gates CLAUDE.md says are mine to clear.",
  );
  lines.push("");
  return lines.join("\n");
}
