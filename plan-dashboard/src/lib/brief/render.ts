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
  /** The book ALREADY EXISTS in the repo. Resolved from disk by the endpoint,
   *  never asserted by the caller. Changes what the prompt asks for: an
   *  existing book's folder and branch are facts to work in, not things to
   *  create. */
  existing?: boolean;
  /** Chapters the source lists that the recordings do NOT reach, so the reader
   *  is told why the list starts where it does rather than at chapter one. */
  uncovered?: string[];
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
      f.kind !== "chapters" &&
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
      // Printed as its own numbered section, never as a settings row: a
      // newline-joined list of 24 titles in a table cell is unreadable.
      f.kind !== "chapters" &&
      !f.formOnly &&
      isVisible(f, input.values) &&
      (input.values[f.key] ?? "").trim() !== "",
  ).map((f) => [f.key, input.values[f.key]] as [string, string]);
  return [...fromFields, ...extraSettings(input)];
}

/** The chapter breakdown as a list: one trimmed title per non-blank line.
 *  Numbering the operator may have typed ("1. Envy") is stripped, so a list
 *  pasted from a table of contents renumbers cleanly instead of ending up
 *  double-numbered. */
export function chapterList(input: BriefInput): string[] {
  return (input.values.chapter_list ?? "")
    .split("\n")
    .map((l) =>
      l
        .trim()
        .replace(/^\d+\s*[.)]\s*/, "")
        .trim(),
    )
    .filter(Boolean);
}

/**
 * The processing rules this commission implies, in the order they run.
 *
 * ONE builder, used by both the document and the hand-off prompt, for the same
 * reason the rest of this file is: what is stored and what is pasted must not
 * disagree. Every line is DERIVED from an answer above it -- nothing here is a
 * preference restated, so a rule can never contradict the setting it came from.
 *
 * Written as instructions rather than description: the prompt's reader acts on
 * them.
 */
export function processingRules(input: BriefInput): string[] {
  const { values } = input;
  const isSession = values.source_medium === "audio_lecture";
  const decks = values.enable_slide_decks !== "false";
  const deckMode = values.slide_deck_mode || "per-chapter";
  const rules: string[] = [];

  if (isSession) {
    rules.push(
      "This is a recorded session, not a text being adapted. The recording is " +
        "the work. Its prose is PROOFREAD only -- spelling, punctuation, " +
        "paragraph breaks, and words the transcriber dropped -- and never " +
        "rewritten, re-voiced, summarised or enriched. A pass that starts " +
        "improving the wording is reverted to the raw transcription.",
    );
    // All THREE answers, since 2026-08-31: `from_source_toc` was added to the
    // vocabulary but not here, so a book set to follow its source's chapter
    // list was told "one chapter per recording" -- the rule contradicting the
    // setting it was derived from, in the document that IS the instruction.
    rules.push(
      values.chapter_segmentation === "from_transcript"
        ? "Chapters are worked out from the transcript, cut at the topic " +
            "boundaries the speaker actually moves between. There may be more " +
            "or fewer chapters than there are recordings."
        : values.chapter_segmentation === "from_source_toc"
          ? "The sessions teach through a published work chapter by chapter. " +
            "Cut the chapters where that book does and keep its own chapter " +
            "names. A recording is NOT one chapter: a single sitting may cover " +
            "several, and the count follows the book rather than the audio."
          : "One chapter per recording. Each audio file becomes exactly one " +
            "chapter; the recordings are not split or merged.",
    );
    const listed = chapterList(input);
    if (listed.length) {
      rules.push(
        `There are ${listed.length} chapters, named in the list of chapters ` +
          `that accompanies this. Use those ` +
          "names exactly. Do not invent chapter titles, and do not merge two of " +
          "them into one chapter or split one into two.",
      );
    } else if ((values.chapter_count_hint ?? "").trim()) {
      rules.push(
        `Expect roughly ${values.chapter_count_hint} chapters. This is a guide, ` +
          "not a target -- but a result far from it is worth stopping to " +
          "question before the run continues.",
      );
    }
    rules.push(
      "Restore the Arabic the transcriber wrote out phonetically -- Qur'an, " +
        "hadith, poetry and quotations -- back into Arabic script. Qur'anic " +
        "runs are set from the canonical mushaf's own wording, never from a " +
        "reconstruction." +
        (values.arabic_restoration === "text_only"
          ? " Resolve from the transcript and the canonical sources only; leave " +
            "a run that cannot be settled that way unresolved rather than guessing."
          : " Where the text alone is ambiguous, check that moment of the " +
            "recording to settle what was actually said."),
    );
    rules.push(
      "All Arabic carries its diacritics. There is no unvowelled Arabic in the " +
        "finished edition.",
    );
    rules.push(
      "Qur'an, hadith, poetry and quotations are set in their own styled " +
        "blocks, not run into the surrounding prose.",
    );
    if (input.uncovered?.length) {
      // Asif, 2026-08-31. The material the recordings never reach is NOT left
      // as a hole and NOT authored as chapters of its own: it is condensed into
      // the edition's single introduction, the same way the Sessions lane
      // already replaces a spoken opening with one (`_book_frontmatter`). A
      // reader who opens at "Love of the World" with no idea what came before
      // is the thing this prevents.
      rules.push(
        `The ${input.uncovered.length} chapter` +
          `${input.uncovered.length === 1 ? "" : "s"} the recordings do not ` +
          `reach — ${input.uncovered.join(", ")} — together with the book's ` +
          "own front matter, history and preface, are condensed into ONE " +
          "introduction chapter. Author it the way this pipeline authors an " +
          "edition's introduction: denoised, well articulated, and brief. Do " +
          "NOT write them as chapters of their own, and do not leave the " +
          "reader to start at the middle of the book with no orientation.",
      );
    }
    rules.push(
      "NO podcast is generated. There are no episodes, no NotebookLM upload " +
        "bundle and no synthesised voices -- the audio already exists and is " +
        "the lecture itself.",
    );
  } else if (chapterList(input).length) {
    rules.push(
      `There are ${chapterList(input).length} chapters, named in the list that ` +
        "accompanies this. " +
        "Use those names exactly rather than titling them afresh.",
    );
  } else if ((values.chapter_count_hint ?? "").trim()) {
    rules.push(
      `Expect roughly ${values.chapter_count_hint} chapters. The chapter design ` +
        "step settles the real count from the source; this is the figure to " +
        "measure that against.",
    );
  }

  rules.push(
    decks
      ? deckMode === "book"
        ? "Produce ONE slide deck covering the whole work."
        : "Produce a slide deck for each chapter."
      : "Produce no slide decks.",
  );
  return rules;
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

  const chapters = chapterList(input);
  if (chapters.length) {
    // Not "The chapters": that is the STEP's own heading, and two sections
    // under one name in a document meant to be read is a defect.
    out.push(`## Chapters, in order (${chapters.length})`);
    out.push("");
    chapters.forEach((c, i) => out.push(`${i + 1}. ${c}`));
    out.push("");
  }

  out.push("## How this will be processed");
  out.push("");
  out.push(
    "Worked out from the answers above, in the order the steps run. " +
      "These are the instructions, not a summary of them.",
  );
  out.push("");
  for (const r of processingRules(input)) out.push(`- ${r}`);
  out.push("");

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
/**
 * The hand-off prompt for a book that ALREADY EXISTS, after its settings were
 * saved. Separate from `renderPrompt` rather than a flag on it, because almost
 * every line differs: there is no brief.md to read, no branch to create, no
 * staged source to point at, and the ask is not "commission this" but "the
 * settings changed, here is what they now are."
 *
 * `changed` names only the fields this save actually wrote. The full settings
 * list still follows, because the reader needs the state, not the diff — but
 * saying which ones moved is what makes the prompt worth pasting rather than
 * re-describing the book from memory.
 */
export function renderSavedPrompt(input: {
  slug: string;
  dir: string;
  bucket: string;
  repoRoot: string;
  values: Record<string, string>;
  changed: string[];
}): string {
  const { values, slug } = input;
  const lines: string[] = [];
  lines.push(
    `I have just updated the settings for an existing piece in the podcast ` +
      `factory. The repo is at ${input.repoRoot} — read its CLAUDE.md first, ` +
      `then run \`bash scripts/start-session.sh\`.`,
  );
  lines.push("");
  lines.push(`- Title: ${values.title ?? slug}`);
  if (values.author) lines.push(`- Author: ${values.author}`);
  lines.push(`- Folder name: ${slug}`);
  lines.push(`- Shelf: ${input.bucket}`);
  lines.push(`- It lives at: ${input.dir}`);
  lines.push(`- Branch: ${input.bucket}/${slug}`);
  lines.push("");
  if (input.changed.length) {
    lines.push(`What I just changed: ${input.changed.join(", ")}.`);
    lines.push("");
  }
  lines.push("Settings as they now stand on disk:");
  lines.push("");
  for (const [k, v] of settingsPairs({
    values,
    bucket: input.bucket,
    briefDir: "",
    repoRoot: input.repoRoot,
    sources: [],
    generatedAt: "",
  } as BriefInput)) {
    lines.push(`- ${k}: ${v}`);
  }
  lines.push("");
  if ((values.notes ?? "").trim()) {
    lines.push("What I said I wanted:");
    lines.push("");
    lines.push(values.notes.trim());
    lines.push("");
  }
  lines.push(
    "Read these back to me and say whether any of them look wrong for this " +
      "source before acting on them. The narrative frame especially is a " +
      "property of the source — check it against how the text actually opens " +
      "rather than trusting the form, which cannot know.",
  );
  lines.push("");
  lines.push(
    "Then carry on with this piece from wherever it currently stands, stopping " +
      "at the gates CLAUDE.md says are mine to clear.",
  );
  lines.push("");
  return lines.join("\n");
}

export function renderPrompt(input: BriefInput): string {
  const { values } = input;
  const slug = values.slug ?? "";
  const branch = `${input.bucket}/${slug}`;
  const primary =
    input.sources.find((s) => s.role === "primary_source") ?? input.sources[0];

  const lines: string[] = [];
  lines.push(
    input.existing
      ? `I want to carry on with a piece of content that is already in the ` +
          `podcast factory. The repo is at ${input.repoRoot} — read its ` +
          `CLAUDE.md first, then run \`bash scripts/start-session.sh\`.`
      : `I want to process a new piece of content through the podcast factory. ` +
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
  // An existing book's branch and folder are facts, not instructions. Telling a
  // fresh session to "create off develop" a branch that already exists is how
  // you get a second copy of a book on a second branch.
  lines.push(
    input.existing
      ? `- It already exists on the branch ${branch} — work there; do not ` +
          `create it, and do not scaffold the folder again.`
      : `- Branch to create off develop: ${branch}`,
  );
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
  const chapters = chapterList(input);
  if (chapters.length) {
    lines.push(`The ${chapters.length} chapters, in order and named:`);
    lines.push("");
    chapters.forEach((c, i) => lines.push(`${i + 1}. ${c}`));
    lines.push("");
    if (input.uncovered?.length) {
      lines.push(
        `The source also contains ${input.uncovered.length} chapter` +
          `${input.uncovered.length === 1 ? "" : "s"} the recordings do not ` +
          `reach — ${input.uncovered.join(", ")}. That is why the list above ` +
          `starts where it does.`,
      );
      lines.push("");
    }
  }
  lines.push("How this is to be processed:");
  lines.push("");
  for (const r of processingRules(input)) lines.push(`- ${r}`);
  lines.push("");
  lines.push(
    "Before anything runs: confirm these settings back to me, tell me anything that " +
      "looks wrong for this source, and ask about whatever the form could not. " +
      "The narrative frame in particular is a property of the source — check it " +
      "against how the text actually opens rather than trusting the form.",
  );
  lines.push("");
  lines.push(
    input.existing
      ? "Then carry on from wherever this piece currently stands — read its " +
          "orchestrator state before assuming a phase still needs running — " +
          "stopping at the gates CLAUDE.md says are mine to clear."
      : "Then take it from intake through the pipeline the way this repo does it, " +
          "stopping at the gates CLAUDE.md says are mine to clear.",
  );
  lines.push("");
  return lines.join("\n");
}
