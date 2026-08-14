/**
 * book-composer-ai-config.ts — the Refine & Notes panel's selection-based AI
 * action config, split out of book-composer.ts (DR-005 size ratchet) and
 * given its own module so the consolidation approved 2026-08-14 (four flat
 * rewrite buttons → one "Rewrite as" group; two duplicate "Explain" buttons
 * → one) is data a test can check directly, without standing up the whole
 * editor controller.
 *
 * REWRITE_MODES replaces the old AI_ACTIONS entries for Rewrite/Expand/
 * Condense/Simplify — same four `mode` values `runAiAction` already sends to
 * `/api/ai/rewrite`, same handler, just rendered as one segmented row
 * instead of four peer buttons. There is deliberately no "explain" entry
 * here any more: the vanilla row's Explain and ComposeAiTools.tsx's Explain
 * both called `/api/ai/explain` with the same body shape (confirmed by
 * reading both call sites) and differed only in which of two UIs showed the
 * result — an accidental duplicate, not two features. The React version
 * (useTermCuration's proposeExplain/applyExplain) is the one that survives:
 * it already guards against the selection changing between propose and
 * apply, which the vanilla popup never did.
 */
export interface RewriteMode {
  kind: string;
  label: string;
  mode: string;
  icon: string;
}

export const REWRITE_MODES: RewriteMode[] = [
  {
    kind: "rewrite",
    label: "Clearer",
    mode: "clarify",
    icon: "fa-solid fa-pen-nib",
  },
  {
    kind: "expand",
    label: "Longer",
    mode: "expand",
    icon: "fa-solid fa-up-right-and-down-left-from-center",
  },
  {
    kind: "condense",
    label: "Shorter",
    mode: "tighten",
    icon: "fa-solid fa-down-left-and-up-right-to-center",
  },
  {
    kind: "simplify",
    label: "Simpler",
    mode: "simplify",
    icon: "fa-solid fa-wand-magic-sparkles",
  },
];

export interface StandaloneTextAction {
  kind: string;
  label: string;
  icon: string;
  /** true → routed through `runEtymology`; the other → `runDiacritics`. Kept
   *  as two literal flags (matching AiAction's own shape in book-composer.ts)
   *  rather than a `handler` id, so this stays a plain, comparable value a
   *  test can assert on without importing the handlers themselves. */
  etymology?: boolean;
  diacritics?: boolean;
  arabicOnly?: boolean;
}

export const ETYMOLOGY_ACTION: StandaloneTextAction = {
  kind: "etymology",
  label: "Etymology",
  etymology: true,
  icon: "fa-solid fa-book-open",
};

/** Vowel the selected Arabic and replace it — the only action gated to stay
 *  disabled outside an Arabic selection (`arabicOnly`), which is what tells
 *  a person when it applies. */
export const DIACRITICS_ACTION: StandaloneTextAction = {
  kind: "diacritics",
  label: "Diacritics",
  diacritics: true,
  arabicOnly: true,
  icon: "fa-solid fa-marker",
};
