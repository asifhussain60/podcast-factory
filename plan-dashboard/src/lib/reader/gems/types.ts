/**
 * gems/types.ts — data model for "Gem" personas: saved system-prompt specs that
 * back the AI-generation tools available to the Companion Panel.
 *
 * A Gem is a named, persisted persona (e.g. the Ismaili Scholar Gem) with a full
 * system-instruction spec. New Gems are added as a single registry entry
 * (registry.ts) — no engine or route change required.
 */

/** A saved persona / system-prompt spec. */
export interface GemDef {
  id: string;
  label: string;
  description: string;
  /** Verbatim, as supplied by the author — persisted unmodified for traceability. */
  systemPrompt: string;
}

/** The result of one Gem generation call. */
export interface GemResult {
  /** The model's full raw text response, before any extraction. */
  raw: string;
  /** The main explanation/answer body. */
  body: string;
  /** The etymology, as DISCRETE ITEMS — one per term (2026-07-26). It used to be
   *  one prose blob; the reader curates these one at a time, adding and deleting
   *  entries, which a single string cannot express. Empty array = none. */
  etymology: string[];
  /** Source URLs, only populated when the call used grounded (web-search) mode. */
  sources?: string[];
}
