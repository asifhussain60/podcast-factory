/**
 * enrichment-ledger.ts — read the per-book enrichment summary written by the
 * Phase 0e augmenter to `content/drafts/books/<slug>/_system/augmentation-ledger.json`.
 *
 * Surfaces the "wisdom corpus integrated" + "data augmented" numbers the Studio
 * transformation dashboard charts. Book-level (one file per book), resilient:
 * returns null when the ledger is absent or malformed. Read-only — never writes.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../content-paths";

export interface EnrichmentSummary {
  /** Distinct wisdom atoms woven into the text. */
  atomsUsed: number;
  /** Sections that received at least one atom. */
  sectionsEnriched: number;
  /** Total atoms available in the knowledge corpus. */
  corpusSize: number;
  /** Atoms shortlisted as candidates for this book. */
  candidatePool: number;
  /** Word count before enrichment. */
  wordsBefore: number;
  /** Word count after enrichment. */
  wordsAfter: number;
  /** USD spent on the enrichment pass. */
  costUsd: number;
}

interface RawLedger {
  total_atoms_used?: number;
  sections_enriched?: number;
  total_atoms_in_corpus?: number;
  candidate_pool_size?: number;
  word_count_before?: number;
  word_count_after?: number;
  total_cost_usd?: number;
}

function num(v: unknown): number {
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
}

/** Load the enrichment summary for a book, or null when unavailable. */
export function loadEnrichment(slug: string): EnrichmentSummary | null {
  const dir = findContentDirSync(slug);
  if (!dir) return null;
  let raw: RawLedger;
  try {
    raw = JSON.parse(
      readFileSync(join(dir, "_system", "augmentation-ledger.json"), "utf8"),
    ) as RawLedger;
  } catch {
    return null;
  }
  return {
    atomsUsed: num(raw.total_atoms_used),
    sectionsEnriched: num(raw.sections_enriched),
    corpusSize: num(raw.total_atoms_in_corpus),
    candidatePool: num(raw.candidate_pool_size),
    wordsBefore: num(raw.word_count_before),
    wordsAfter: num(raw.word_count_after),
    costUsd: num(raw.total_cost_usd),
  };
}
