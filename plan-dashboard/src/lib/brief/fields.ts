/**
 * fields.ts — the single definition of what the Intake wizard asks for.
 *
 * ONE array drives three things that would otherwise drift apart: the inputs on
 * each step, the read-back list on the review step, and the headings in the
 * generated requirements document. Adding a question means adding a row here and
 * nothing else.
 *
 * Option lists are never written here. A field names either a `vocab` key
 * (served by scripts/podcast/brief_vocabularies.py) or an `options` key (served
 * by the existing /api/intake/form-options), and the values come from the
 * pipeline registry that owns them.
 */

export type StepId = 1 | 2 | 3 | 4 | 5 | 6;

export type FieldKind =
  | "text"
  | "number"
  | "select"
  | "combo"
  | "switch"
  | "textarea"
  /** An ordered list of titles, one per row. Carried as a newline-joined
   *  string like any other field -- see ChapterListEditor for why. */
  | "chapters";

/**
 * Fields all render at one width -- they fill their grid cell -- so that labels,
 * boxes and hints line up down both columns. Content-proportional widths were
 * tried first and read as ragged: a 9ch box beside a 44ch one on the same row.
 * The only remaining distinction is whether a field takes the whole row.
 */

export interface FieldDef {
  key: string;
  label: string;
  step: StepId;
  kind: FieldKind;
  /** Option list from brief_vocabularies.py. */
  vocab?: string;
  /** Option list from the existing /api/intake/form-options. */
  options?: string;
  required?: boolean;
  /** Lives inside the step's "Advanced" accordion rather than on the surface. */
  advanced?: boolean;
  /** Spans both columns instead of one -- for long prose and long option lists. */
  fullRow?: boolean;
  hint?: string;
  /** Native constraint-validation pattern. */
  pattern?: string;
  patternHint?: string;
  maxLength?: number;
  /** Right-to-left script (Arabic titles). */
  rtl?: boolean;
  /** Rendered only when another field holds one of these values. */
  showIf?: { key: string; equals: string[] };
  /** Default for a switch. */
  defaultOn?: boolean;
  /** Offers a "Choose folder…" button that fills this field from a picked folder. */
  folderPicker?: boolean;
  /** A question the form asks to decide what else to ask. It shapes the brief
   *  but is not a key the pipeline reads, so it is kept out of the settings the
   *  hand-off prompt lists as pipeline configuration. */
  formOnly?: boolean;
}

export const STEPS: { id: StepId; title: string; blurb: string }[] = [
  { id: 1, title: "The work", blurb: "What it is and what to call it." },
  { id: 2, title: "The source", blurb: "What we are working from." },
  {
    id: 3,
    title: "The chapters",
    blurb: "How it is divided, and what each part is called.",
  },
  {
    id: 4,
    title: "The edition",
    blurb: "Who narrates it, and what we are making.",
  },
  {
    id: 5,
    title: "The podcast",
    blurb: "How it will sound and how it is classified.",
  },
  { id: 6, title: "Review", blurb: "Check it over, then generate." },
];

/**
 * The steps by name. Every consumer addresses a step through these rather than
 * by its number: inserting "The chapters" as step 3 on 2026-08-31 renumbered
 * three later steps, and a hard-coded `step === 5` for the review screen is
 * exactly the breakage that cannot be seen by reading the line that broke.
 */
export const WORK_STEP: StepId = 1;
export const SOURCE_STEP: StepId = 2;
export const CHAPTERS_STEP: StepId = 3;
export const EDITION_STEP: StepId = 4;
export const PODCAST_STEP: StepId = 5;
export const REVIEW_STEP: StepId = 6;

export const FIELDS: FieldDef[] = [
  // ── 1 · The work ──────────────────────────────────────────────────────────
  {
    key: "title",
    label: "Title",
    step: 1,
    kind: "text",
    required: true,
    maxLength: 160,
    hint: "The title as it will appear on the book.",
  },
  {
    key: "title_arabic",
    label: "Arabic title",
    step: 1,
    kind: "text",
    rtl: true,
    maxLength: 160,
    hint: "In Arabic script, vowelled if you have it that way.",
  },
  {
    key: "title_english",
    label: "English title",
    step: 1,
    kind: "text",
    maxLength: 160,
    hint: "The meaning in English, when the main title is not already English.",
  },
  {
    key: "author",
    label: "Author",
    step: 1,
    kind: "text",
    required: true,
    maxLength: 120,
  },
  {
    key: "slug",
    label: "Folder name",
    step: 1,
    kind: "text",
    required: true,
    folderPicker: true,
    pattern: "^[a-z0-9]+(?:-[a-z0-9]+)*$",
    patternHint:
      "Lower-case words joined by single hyphens, e.g. kitab-al-hikmah.",
    maxLength: 60,
    hint: "Suggested from the title. This names the folder and the branch.",
  },
  {
    key: "content_profile",
    label: "Pipeline profile",
    step: 1,
    kind: "select",
    options: "content_profile",
    advanced: true,
    hint: "Worked out from the two answers above. Change it only if you know you need to.",
  },
  {
    // The legacy tag. `_branching` states outright that it "does NOT reliably
    // determine the bucket" and content_profile supersedes it, but _paths,
    // _contract_validation and the explainer slide route still read it -- so it
    // is derived from the profile and kept overridable rather than dropped.
    key: "category",
    label: "Legacy category tag",
    step: 1,
    kind: "select",
    vocab: "category",
    advanced: true,
    hint: "Derived from the kind of content. Change it only if you know you need to.",
  },
  {
    // The pipeline's content_profile is RESOLVED from this plus source_medium
    // (see FAMILY_PROFILES in brief_vocabularies.py). Asking the profile
    // directly meant choosing between "Islamic scholarly" and "Islamic session"
    // with nothing on screen explaining the difference.
    key: "content_family",
    label: "What kind of content is this",
    step: 1,
    kind: "select",
    vocab: "content_family",
    required: true,
    formOnly: true,
    hint: "This decides the shelf it lives on and most of the defaults below.",
  },
  {
    key: "original_title",
    label: "Original title",
    step: 1,
    kind: "text",
    advanced: true,
    maxLength: 160,
  },
  {
    key: "short_name",
    label: "Short name",
    step: 1,
    kind: "text",
    advanced: true,
    maxLength: 60,
  },
  {
    key: "doctrinal_school",
    label: "School",
    step: 1,
    kind: "text",
    advanced: true,
    maxLength: 80,
  },
  {
    key: "doctrinal_period",
    label: "Period",
    step: 1,
    kind: "text",
    advanced: true,
    maxLength: 60,
  },
  {
    key: "doctrinal_genre",
    label: "Genre",
    step: 1,
    kind: "text",
    advanced: true,
    maxLength: 80,
  },

  // ── 2 · The source ────────────────────────────────────────────────────────
  {
    // On step 1 rather than step 2 since 2026-08-30: together with
    // content_family this resolves the pipeline profile, so it has to be
    // answered before the derived shelf and branch can be shown.
    key: "source_medium",
    label: "Where it came from",
    step: 1,
    kind: "select",
    vocab: "source_medium",
    required: true,
    hint: "A printed work and a recorded talk are handled differently.",
  },
  {
    key: "source_language",
    label: "Source language",
    step: 2,
    kind: "select",
    options: "source_language",
    required: true,
  },
  {
    key: "is_volume",
    label: "One volume of a larger work",
    step: 2,
    kind: "switch",
    formOnly: true,
    hint: "Turn on if this is, say, volume 3 of a six-volume set.",
  },
  {
    key: "work_slug",
    label: "The whole work's folder name",
    step: 2,
    kind: "text",
    pattern: "^[a-z0-9]+(?:-[a-z0-9]+)*$",
    patternHint: "Same shape as a folder name.",
    showIf: { key: "is_volume", equals: ["true"] },
  },
  {
    key: "volume",
    label: "Which volume",
    step: 2,
    kind: "number",
    showIf: { key: "is_volume", equals: ["true"] },
  },
  {
    // Asked, never derived. A file listing cannot tell a course of weekly
    // lectures (one chapter each) from one long sitting that moves through
    // several topics (cut at those boundaries), and guessing wrong reshapes
    // the whole edition.
    key: "chapter_segmentation",
    label: "How the chapters are decided",
    step: 3,
    kind: "select",
    vocab: "chapter_segmentation",
    required: true,
    fullRow: true,
    showIf: { key: "source_medium", equals: ["audio_lecture"] },
    hint: "A recording is usually one chapter. Choose the other option when one long sitting covers several distinct topics.",
  },
  {
    // The chapter breakdown, for EVERY route (Asif, 2026-08-31). A session
    // series usually teaches through a published work whose chapters are
    // already named and already in order, and a book being adapted has a table
    // of contents -- in both cases the list exists before the pipeline runs,
    // and typing it here is what stops the chapter-design step inventing its
    // own names for chapters that already have them.
    key: "chapter_list",
    label: "The chapters",
    step: 3,
    kind: "chapters",
    fullRow: true,
    maxLength: 8000,
    hint: "In order, exactly as they should be titled. Leave empty if the chapters are not known yet.",
  },
  {
    // A guide, never a decision. Phase 0d reads the source and settles the
    // real count; this is what the cost estimate is built on, and what a run
    // that comes back with three chapters instead of thirty is measured
    // against. Left blank it simply is not checked.
    key: "chapter_count_hint",
    label: "Roughly how many chapters",
    step: 3,
    kind: "number",
    hint: "Only needed when the chapters above are not listed. A guess is fine — it sizes the cost estimate and flags a run that comes back wildly different.",
    showIf: { key: "chapter_list", equals: [""] },
  },
  {
    key: "arabic_restoration",
    label: "Putting the Arabic back",
    step: 2,
    kind: "select",
    vocab: "arabic_restoration",
    fullRow: true,
    showIf: { key: "source_medium", equals: ["audio_lecture"] },
    hint: "Transcribers write Arabic phonetically. Qur'an is always restored from the canonical mushaf; this decides how hadith, poetry and quotations are settled.",
  },
  {
    key: "source_fidelity",
    label: "How exact the transcript is",
    step: 2,
    kind: "select",
    vocab: "source_fidelity",
    advanced: true,
    showIf: { key: "source_medium", equals: ["audio_lecture"] },
  },

  // ── 3 · The edition ───────────────────────────────────────────────────────
  {
    key: "narrative_frame",
    label: "Who narrates it",
    step: 4,
    kind: "select",
    vocab: "narrative_frame",
    required: true,
    fullRow: true,
    hint: "Read how the SOURCE opens. This is a property of the text, never a preference.",
  },
  {
    key: "narrator_subject",
    label: "The narrator's name",
    step: 4,
    kind: "text",
    required: true,
    showIf: { key: "narrative_frame", equals: ["participant_narrator"] },
    hint: "One named person, for the whole book.",
  },
  {
    key: "deliverable_mode",
    label: "Kind of edition",
    step: 4,
    kind: "select",
    vocab: "deliverable_mode",
  },
  {
    key: "book_voice",
    label: "Voice of the edition",
    step: 4,
    kind: "select",
    vocab: "book_voice",
  },
  {
    key: "enable_book_branch",
    label: "Produce a reading edition (PDF)",
    step: 4,
    kind: "switch",
    defaultOn: true,
    hint: "Off, and none of the book-building steps will run at all.",
  },
  {
    // On step 3 rather than step 4 since 2026-08-31: a deck is a DELIVERABLE,
    // not a podcast setting. Sessions produce decks and never produce episodes,
    // so leaving this among the podcast questions made it invisible for exactly
    // the route that still needs it (Asif, 2026-08-31).
    key: "enable_slide_decks",
    label: "Produce slide decks",
    step: 4,
    kind: "switch",
    defaultOn: true,
    hint: "Decks are produced for both books and recorded sessions.",
  },
  {
    key: "slide_deck_mode",
    label: "Decks per",
    step: 4,
    kind: "select",
    vocab: "slide_deck_mode",
    advanced: true,
    showIf: { key: "enable_slide_decks", equals: ["true"] },
  },
  {
    key: "book_augmentation",
    label: "What may be added",
    step: 4,
    kind: "select",
    vocab: "book_augmentation",
    advanced: true,
  },
  {
    key: "book_visuals",
    label: "Figures",
    step: 4,
    kind: "select",
    vocab: "book_visuals",
    advanced: true,
  },
  {
    key: "autonomy",
    label: "How far it may run unattended",
    step: 4,
    kind: "select",
    vocab: "autonomy",
    advanced: true,
    fullRow: true,
  },

  // ── 4 · The podcast ───────────────────────────────────────────────────────
  {
    key: "audience_profile",
    label: "Audience",
    step: 5,
    kind: "select",
    options: "audience_profile",
    showIf: { key: "source_medium", equals: ["printed_text"] },
  },
  {
    key: "host_dynamic",
    label: "Conversation style",
    step: 5,
    kind: "select",
    options: "host_dynamic",
    showIf: { key: "source_medium", equals: ["printed_text"] },
  },
  {
    key: "length_tier",
    label: "Episode length",
    step: 5,
    kind: "select",
    options: "length_tier",
    showIf: { key: "source_medium", equals: ["printed_text"] },
  },
  {
    key: "video_style",
    label: "Video style",
    step: 5,
    kind: "select",
    options: "video_style",
    showIf: { key: "source_medium", equals: ["printed_text"] },
  },
  {
    // Moved from step 4 to step 1 (Asif, 2026-08-30): it is the shelf the
    // Library's "Browse by track" chips are built from, so it belongs with the
    // work's identity rather than buried among the podcast production settings.
    key: "study_track",
    label: "Study track",
    step: 1,
    kind: "select",
    vocab: "study_track",
    hint: "The shelf readers browse it under on the Library.",
  },
  {
    key: "episode_planning_mode",
    label: "How episodes are planned",
    step: 5,
    kind: "select",
    options: "episode_planning_mode",
    advanced: true,
    showIf: { key: "source_medium", equals: ["printed_text"] },
  },
  {
    key: "archetype",
    label: "Archetype",
    step: 5,
    kind: "combo",
    vocab: "archetype",
    advanced: true,
    hint: "The authoring doctrine that governs how episodes are written.",
    showIf: { key: "source_medium", equals: ["printed_text"] },
  },
  {
    key: "content_level",
    label: "Depth of the material",
    step: 5,
    kind: "select",
    vocab: "content_level",
    advanced: true,
  },
  {
    key: "density",
    label: "Density",
    step: 5,
    kind: "select",
    vocab: "density",
    advanced: true,
  },

  // ── 5 · Review ────────────────────────────────────────────────────────────
  {
    key: "notes",
    label: "In your words",
    step: 6,
    kind: "textarea",
    fullRow: true,
    maxLength: 4000,
    hint: "What you want this edition to be, anything unusual about the source, anything I should ask you about.",
  },
];

export const FIELDS_BY_KEY: Record<string, FieldDef> = Object.fromEntries(
  FIELDS.map((f) => [f.key, f]),
);

export function fieldsForStep(step: StepId): FieldDef[] {
  return FIELDS.filter((f) => f.step === step);
}

/** Is a conditional field currently in play? Hidden fields are never required. */
export function isVisible(
  f: FieldDef,
  values: Record<string, string>,
): boolean {
  if (!f.showIf) return true;
  return f.showIf.equals.includes(values[f.showIf.key] ?? "");
}

/**
 * Everything the PIPELINE needs that a per-field `required` flag cannot express,
 * because each one depends on another answer.
 *
 * Kept here, beside the fields themselves, so the wizard's own blocker list and
 * the server's refusal to write a brief are computed by ONE function. They were
 * two checks for one question until 2026-08-31, and the browser's was the looser
 * of the two — which is the wrong way round for a document that starts a
 * multi-hour, paid run.
 *
 * Each entry names the step to jump to, so a problem found on the review screen
 * is one click from the question that fixes it.
 */
export function completenessProblems(
  values: Record<string, string>,
  opts: {
    sourceCount: number;
    roles: readonly string[];
    /** The book already exists on disk, so its sources are its own files and
     *  nothing needs staging. The upload checks below are skipped for it. */
    existing?: boolean;
  },
): { step: StepId; reason: string }[] {
  const out: { step: StepId; reason: string }[] = [];
  const has = (k: string) => (values[k] ?? "").trim() !== "";
  const chapters = (values.chapter_list ?? "")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean).length;

  if (!opts.existing) {
    if (opts.sourceCount === 0) {
      out.push({
        step: SOURCE_STEP,
        reason:
          "no source file has been added — the pipeline has nothing to work from",
      });
    }

    if (values.source_medium === "audio_lecture") {
      // The lane's own rule: a recording is the witness, and its transcript is
      // what becomes the chapter text. One without the other cannot be
      // processed.
      if (opts.sourceCount > 0 && !opts.roles.includes("source_recording")) {
        out.push({
          step: SOURCE_STEP,
          reason:
            "a recorded session needs its recording added, marked Source recording",
        });
      }
    }
  }

  if (values.chapter_segmentation === "from_source_toc" && chapters === 0) {
    out.push({
      step: CHAPTERS_STEP,
      reason:
        "the chapters are set to follow the book's own list, but no list has been given",
    });
  }

  if (chapters === 0 && !has("chapter_count_hint")) {
    out.push({
      step: CHAPTERS_STEP,
      reason:
        "list the chapters, or give a rough number — otherwise nothing measures what the run comes back with",
    });
  }

  return out;
}

/** Every required field on a step that is visible and still empty. */
export function missingOn(
  step: StepId,
  values: Record<string, string>,
): FieldDef[] {
  return fieldsForStep(step).filter(
    (f) => f.required && isVisible(f, values) && !(values[f.key] ?? "").trim(),
  );
}

/** Fields whose value fails their own pattern. Empty values are missingOn's job. */
export function invalidOn(
  step: StepId,
  values: Record<string, string>,
): FieldDef[] {
  return fieldsForStep(step).filter((f) => {
    if (!f.pattern || !isVisible(f, values)) return false;
    const v = (values[f.key] ?? "").trim();
    return v !== "" && !new RegExp(f.pattern).test(v);
  });
}

/** The folder name suggested from a title: lower-case, hyphenated, ASCII. */
export function slugify(title: string): string {
  return title
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)
    .replace(/-+$/g, "");
}

/**
 * Why a field cannot be edited on an EXISTING piece of content. Shown beside
 * the locked value: a control that refuses without saying why reads as a bug.
 * The set itself is the server's (LOCKED_FOR_EXISTING in store.ts) — this is
 * only the prose for it, and the save refuses these regardless of the UI.
 */
export const LOCK_REASONS: Record<string, string> = {
  slug: "This is the book's identity. Renaming moves the folder and the git branch — use Rename on the book's Studio page.",
  content_family:
    "Changing this would move the book to a different shelf, which means a new folder path and a new branch.",
  content_profile:
    "Worked out from the kind of content and where it came from, both of which are locked here.",
  source_medium:
    "Together with the kind of content this decides the shelf, so it is locked for the same reason.",
};
