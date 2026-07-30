/**
 * studio-editor-constants.ts — module-level constants, registries, and pure
 * helpers extracted from StudioEditor.tsx (R2 pass 1a — mechanical, verbatim).
 * Single source of truth for the action registry, marker patterns, editor
 * reading-comfort preference keys, surah map, depth levels, and section tags.
 */

// ── Reading-comfort controls (font · size · paper) ───────────────────────────
// EDITING-VIEW preferences shared with the Book Composer via the SAME
// localStorage keys, so a choice made in either editor applies to both. View
// only: the enrichment text and the printed book are unaffected.
// THE list, for both editors — the Book Composer imports it rather than keeping a
// copy. Adding a face means adding it here, plus a `--prose-font` stack in
// book-composer.css and studio-editor-core.css, plus a self-hosted @font-face; a
// face listed with no stack silently renders as the surface's default.
export const EDITOR_FONTS = [
  { id: "sans", name: "Sans" },
  { id: "serif", name: "Serif" },
  { id: "lato", name: "Lato" },
  { id: "inter", name: "Inter" },
  // Self-hosted 2026-07-30. Lexend is drawn for reading ease — wide apertures,
  // loose spacing. Cinzel is a Roman-inscription face whose lowercase is small
  // caps, which sets a chapter of dialogue very differently.
  { id: "lexend", name: "Lexend" },
  { id: "cinzel", name: "Cinzel" },
  { id: "mono", name: "Mono" },
  { id: "dyslexic", name: "Dyslexic" },
] as const;
export const EDITOR_FONT_IDS = EDITOR_FONTS.map(
  (f) => f.id,
) as readonly string[];
export const EDITOR_PAPERS = [
  { id: "light", name: "Light" },
  { id: "sepia", name: "Sepia" },
  { id: "dark", name: "Dark" },
] as const;
export const EDITOR_PAPER_IDS = EDITOR_PAPERS.map(
  (p) => p.id,
) as readonly string[];
export const EDITOR_SIZE_MIN = 13;
export const EDITOR_SIZE_MAX = 26;
export const EDITOR_SIZE_DEFAULT = 19; // ~ the ProseMirror 1rem default
export function readEditorPref(
  key: string,
  fallback: string,
  allowed: readonly string[],
): string {
  try {
    const v = localStorage.getItem(key);
    return v && allowed.includes(v) ? v : fallback;
  } catch {
    return fallback;
  }
}
export function readEditorSize(): number {
  try {
    const n = Number(localStorage.getItem("cx-editor-size"));
    return Number.isFinite(n) && n >= EDITOR_SIZE_MIN && n <= EDITOR_SIZE_MAX
      ? n
      : EDITOR_SIZE_DEFAULT;
  } catch {
    return EDITOR_SIZE_DEFAULT;
  }
}

// Inline reference markers: inspector inventory + inline chips for Hadith/Works.
// Quran verse refs are handled separately as FC-1 chips, so mk-quran is skipped here.
export const MARKER_PATTERNS: {
  re: RegExp;
  cls: string;
  kind: string;
  chip?: string;
}[] = [
  { re: /Surah [A-Z][\w'-]+/g, cls: "mk-quran", kind: "Quran" },
  {
    re: /verses? \d+(?:\s*(?:to|–|-)\s*\d+)?/gi,
    cls: "mk-quran",
    kind: "Quran",
  },
  {
    re: /Prophet Muhammad/gi,
    cls: "mk-hadith",
    kind: "Hadith",
    chip: "Hadith",
  },
  { re: /peace and blessings of Allah/gi, cls: "mk-hadith", kind: "Hadith" },
  {
    re: /Ihya(?:\s+Ulum\s+al-Din)?/g,
    cls: "mk-term",
    kind: "Work",
    chip: "Ihya",
  },
  {
    re: /Kimiya(?:\s+al-Sa'?ada)?/g,
    cls: "mk-term",
    kind: "Work",
    chip: "Kimiya",
  },
  { re: /Jawahir al-Quran/g, cls: "mk-term", kind: "Work", chip: "Jawahir" },
  { re: /Minhaj al-Abidin/g, cls: "mk-term", kind: "Work", chip: "Minhaj" },
];

export const ARABIC_SCRIPT_RUN =
  /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF](?:[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\s]*[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF])?/;
// A transliterated TERM immediately followed by its Arabic in parentheses.
// The roman side is capped at five words. It used to be unbounded (`+`), so it
// matched backwards to the start of the sentence: a whole clause ending in
// "...attributes to Jafar ibn Mansur al-Yaman (<arabic>)" was treated as the
// term and marked `ar-pair-hidden` -- meaning the Arabic toggle would hide a
// clause of English prose rather than one term. Latent until 2026-07-21, when
// the inline-Arabic pass (_book_inline_arabic.py) began writing these pairs
// into the book. Five words covers the longest real glossary name,
// "Jafar ibn Mansur al-Yaman".
export const ARABIC_PAIR_RE =
  /([A-Za-zāēīōūĀĒĪŌŪṣṢḍḌṭṬẓẒḥḤʿʾ'’.-]+(?:[\s-]+[A-Za-zāēīōūĀĒĪŌŪṣṢḍḌṭṬẓẒḥḤʿʾ'’.-]+){1,4})\s*\(([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF][^)]+)\)/gu;

// ── Deferred AI action-item registry ────────────────────────────────────────
// Single source of truth for every action the human can stamp on a paragraph or
// a selected term (edit mode only). A later CLI pass drains the queued marks.
// Add a button HERE and it appears in the palette, the queue, and the inline
// badges; the API allow-list in /api/studio/action-items mirrors these kinds.
// `scope` decides where the action shows: 'term' needs a text selection,
// 'paragraph' acts on the active paragraph, 'both' appears in either palette.
export type ActionScope = "paragraph" | "term" | "both";
export type ActionGroup = "core" | "transform" | "knowledge";
export interface ActionDef {
  kind: string;
  label: string;
  icon: string; // Font Awesome solid class
  scope: ActionScope;
  group: ActionGroup;
  hint: string; // tooltip — what the CLI will do with this mark
  // 'deferred' (default) = stamp a mark for the CLI drain pass; 'immediate' = run
  // AI now and apply in-place (e.g. Arabic term replacement), never queued.
  applyMode?: "deferred" | "immediate";
}
export const ACTION_REGISTRY: readonly ActionDef[] = [
  // Core
  {
    kind: "arabic",
    label: "Arabic",
    icon: "fa-language",
    scope: "term",
    group: "core",
    hint: "Replace this term with the correct contextual Arabic (AI, confirm first)",
    applyMode: "immediate",
  },
  {
    kind: "english",
    label: "English",
    icon: "fa-language",
    scope: "term",
    group: "core",
    hint: "Replace this term with the correct contextual English (AI or glossary, confirm first)",
    applyMode: "immediate",
  },
  {
    kind: "replace",
    label: "Replace",
    icon: "fa-right-left",
    scope: "term",
    group: "core",
    hint: "Find & replace this phrase across this chapter or the whole book",
    applyMode: "immediate",
  },
  {
    kind: "explain",
    label: "Explain",
    icon: "fa-lightbulb",
    scope: "term",
    group: "core",
    hint: "Replace the selection with a clearer, fuller explanation (AI, in chapter context)",
    applyMode: "immediate",
  },
  {
    kind: "noise",
    label: "Noise",
    icon: "fa-eraser",
    scope: "term",
    group: "core",
    hint: "Mark the selection as noise -> generalise to a pattern -> strip every match across this chapter or the whole book",
    applyMode: "immediate",
  },
  {
    kind: "etymology",
    label: "Etymology",
    icon: "fa-book-bookmark",
    scope: "term",
    group: "core",
    hint: "Resolve the root-history of this term (shared wisdom corpus)",
  },
  {
    kind: "rewrite",
    label: "Rewrite",
    icon: "fa-arrows-rotate",
    scope: "paragraph",
    group: "core",
    hint: "Rewrite this paragraph — reword, sharpen clarity, or redo it freely",
  },
  // Transform
  {
    kind: "expand",
    label: "Expand",
    icon: "fa-up-right-and-down-left-from-center",
    scope: "paragraph",
    group: "transform",
    hint: "Elaborate — add depth or an example",
  },
  {
    kind: "condense",
    label: "Condense",
    icon: "fa-compress",
    scope: "paragraph",
    group: "transform",
    hint: "Tighten without losing meaning",
  },
  {
    kind: "simplify",
    label: "Simplify",
    icon: "fa-feather",
    scope: "paragraph",
    group: "transform",
    hint: "Plain-language version for a lay listener",
  },
  // Knowledge
  {
    kind: "define",
    label: "Define",
    icon: "fa-spell-check",
    scope: "term",
    group: "knowledge",
    hint: "Short glossary gloss for this term",
  },
  {
    kind: "xref",
    label: "Cross-ref",
    icon: "fa-link",
    scope: "both",
    group: "knowledge",
    hint: "Find related passages in this book or the corpus",
  },
  {
    kind: "addcorpus",
    label: "Add to corpus",
    icon: "fa-database",
    scope: "both",
    group: "knowledge",
    hint: "Promote this passage or term into the wisdom knowledge base",
  },
  {
    kind: "visualize",
    label: "Visualization",
    icon: "fa-diagram-project",
    scope: "paragraph",
    group: "knowledge",
    hint: "Flag this passage for a visual diagram in the PDF reading edition",
  },
];
export const ACTION_BY_KIND: Record<string, ActionDef> = Object.fromEntries(
  ACTION_REGISTRY.map((a) => [a.kind, a]),
);

// One action-item mark as held client-side (mirrors the action_items table row).
export interface ClientActionItem {
  id: number; // negative = optimistic (not yet persisted)
  scope: "paragraph" | "term";
  para_ordinal: number;
  term_text: string; // '' for paragraph scope
  anchor_text: string;
  action_kind: string;
  status: string;
}

export function truncate(s: string, n = 40): string {
  const t = s.trim();
  return t.length > n ? `${t.slice(0, n - 1)}…` : t;
}

export interface GlossaryEntry {
  phonetic: string;
  transliteration: string;
  arabic_script: string;
  audio_phonetic?: string;
  decision?: string;
  corrected_arabic?: string;
  english_override?: string;
}

export function scanMarkers(text: string): { kind: string; text: string }[] {
  const out: { kind: string; text: string }[] = [];
  for (const { re, kind } of MARKER_PATTERNS) {
    re.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text))) out.push({ kind, text: m[0] });
  }
  return out;
}

// Surah name -> number (subset; expand to all 114 in the real build via the corpus).
export const SURAH_MAP: Record<string, number> = {
  "Al-Fatihah": 1,
  "Al-Baqarah": 2,
  "Al-A'raf": 7,
  "Al-Anfal": 8,
  "At-Tawbah": 9,
  Yusuf: 12,
  "Al-Isra": 17,
  "Al-Kahf": 18,
  Maryam: 19,
  "Ta-Ha": 20,
  "Al-Muminun": 23,
  "An-Nur": 24,
  "Al-Furqan": 25,
  Luqman: 31,
  "Ya-Sin": 36,
  "Adh-Dhariyat": 51,
  "Ar-Rahman": 55,
  "Al-Hashr": 59,
  "Al-Mulk": 67,
  "Al-A'la": 87,
  "Ash-Shams": 91,
  "Az-Zalzalah": 99,
  "Al-Asr": 103,
  "Al-Ikhlas": 112,
};
// "Surah X, verses 7 to 8" | "Surah X, verse 110". The verse-ref chip that REPLACES this
// phrase is built inside StudioDecos (so it can coordinate with the Arabic overlay).
export const SURAH_VERSE_RE =
  /Surah ([A-Z][\w'’-]+),?\s+verses?\s+(\d+)(?:\s*(?:to|–|-)\s*(\d+))?/g;

export type SaveDepthFn = (
  ord: number,
  slug: string,
  level: string,
  tags: string[],
) => void;
export type DepthLevel = { readonly key: string; readonly label: string };

export const DEPTH_LEVELS_BY_PROFILE: Record<string, readonly DepthLevel[]> = {
  islamic_scholarly: [
    { key: "narrative", label: "Narrative" },
    { key: "sharia", label: "Sharia" },
    { key: "esoteric", label: "Esoteric" },
    { key: "origins", label: "Origins" },
    { key: "reality", label: "Reality" },
  ],
  consumer_explainer: [
    { key: "website", label: "Website" },
    { key: "application", label: "Application" },
    { key: "platform", label: "Platform" },
    { key: "api", label: "API" },
  ],
  technical: [
    { key: "coding", label: "Coding" },
    { key: "agentic_ai", label: "Agentic AI" },
    { key: "architecture", label: "Architecture" },
    { key: "devops", label: "DevOps" },
    { key: "security", label: "Security" },
    { key: "data_ml", label: "Data / ML" },
  ],
  fiction: [
    { key: "narrative", label: "Narrative" },
    { key: "character", label: "Character" },
    { key: "theme", label: "Theme" },
    { key: "world", label: "World" },
    { key: "conflict", label: "Conflict" },
    { key: "voice", label: "Voice" },
  ],
};
export const DEFAULT_DEPTH_PROFILE = "islamic_scholarly";

// Section-level editorial tags — the content-classification vocabulary carried by
// the section depth picker on each h2 (distinct from the action-item registry above)
export const SECTION_TAGS = [
  { id: "esoteric", label: "Esoteric" },
  { id: "reality", label: "Reality" },
  { id: "sharia", label: "Sharia" },
  { id: "narrative", label: "Narrative" },
  { id: "origins", label: "Origins" },
  { id: "delete", label: "Delete" },
  { id: "improve", label: "Improve" },
];

export const CONTENT_SECTION_TAGS = SECTION_TAGS.filter(
  (t) => !["delete", "improve"].includes(t.id),
);
export const WORKFLOW_SECTION_TAGS = SECTION_TAGS.filter((t) =>
  ["delete", "improve"].includes(t.id),
);
