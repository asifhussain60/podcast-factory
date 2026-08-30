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

export type StepId = 1 | 2 | 3 | 4 | 5;

export type FieldKind =
  "text" | "number" | "select" | "combo" | "switch" | "textarea";

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
    title: "The edition",
    blurb: "Who narrates it, and what we are making.",
  },
  {
    id: 4,
    title: "The podcast",
    blurb: "How it will sound and how it is classified.",
  },
  { id: 5, title: "Review", blurb: "Check it over, then generate." },
];

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
    step: 3,
    kind: "select",
    vocab: "narrative_frame",
    required: true,
    fullRow: true,
    hint: "Read how the SOURCE opens. This is a property of the text, never a preference.",
  },
  {
    key: "narrator_subject",
    label: "The narrator's name",
    step: 3,
    kind: "text",
    required: true,
    showIf: { key: "narrative_frame", equals: ["participant_narrator"] },
    hint: "One named person, for the whole book.",
  },
  {
    key: "deliverable_mode",
    label: "Kind of edition",
    step: 3,
    kind: "select",
    vocab: "deliverable_mode",
  },
  {
    key: "book_voice",
    label: "Voice of the edition",
    step: 3,
    kind: "select",
    vocab: "book_voice",
  },
  {
    key: "enable_book_branch",
    label: "Produce a reading edition (PDF)",
    step: 3,
    kind: "switch",
    defaultOn: true,
    hint: "Off, and none of the book-building steps will run at all.",
  },
  {
    key: "book_augmentation",
    label: "What may be added",
    step: 3,
    kind: "select",
    vocab: "book_augmentation",
    advanced: true,
  },
  {
    key: "book_visuals",
    label: "Figures",
    step: 3,
    kind: "select",
    vocab: "book_visuals",
    advanced: true,
  },
  {
    key: "autonomy",
    label: "How far it may run unattended",
    step: 3,
    kind: "select",
    vocab: "autonomy",
    advanced: true,
    fullRow: true,
  },

  // ── 4 · The podcast ───────────────────────────────────────────────────────
  {
    key: "audience_profile",
    label: "Audience",
    step: 4,
    kind: "select",
    options: "audience_profile",
  },
  {
    key: "host_dynamic",
    label: "Conversation style",
    step: 4,
    kind: "select",
    options: "host_dynamic",
  },
  {
    key: "length_tier",
    label: "Episode length",
    step: 4,
    kind: "select",
    options: "length_tier",
  },
  {
    key: "video_style",
    label: "Video style",
    step: 4,
    kind: "select",
    options: "video_style",
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
    key: "enable_slide_decks",
    label: "Produce slide decks",
    step: 4,
    kind: "switch",
    defaultOn: true,
  },
  {
    key: "episode_planning_mode",
    label: "How episodes are planned",
    step: 4,
    kind: "select",
    options: "episode_planning_mode",
    advanced: true,
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
    key: "archetype",
    label: "Archetype",
    step: 4,
    kind: "combo",
    vocab: "archetype",
    advanced: true,
    hint: "The authoring doctrine that governs how episodes are written.",
  },
  {
    key: "content_level",
    label: "Depth of the material",
    step: 4,
    kind: "select",
    vocab: "content_level",
    advanced: true,
  },
  {
    key: "density",
    label: "Density",
    step: 4,
    kind: "select",
    vocab: "density",
    advanced: true,
  },

  // ── 5 · Review ────────────────────────────────────────────────────────────
  {
    key: "notes",
    label: "In your words",
    step: 5,
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
