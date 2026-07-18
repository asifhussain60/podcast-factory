/**
 * halts.ts — the pipeline's human-review halts, surfaced in the Studio cockpit.
 *
 * Mirrors the halt phases in scripts/podcast/_progress.py PHASES (the entries
 * whose comments mark a "halt" / "human gate"): 0ci, 06a, 0f, finalize. Each
 * halt names the artifact(s) a reviewer reads before approving the pipeline
 * past that gate. Data-driven: adding a halt is one array entry, so the cockpit
 * extends without code edits (extensibility-first).
 *
 * The decision a reviewer records here is persisted to
 * BOOK_DIR/_system/halt-reviews.json by /api/studio/halt-decision; the
 * orchestrator can read that file to know whether a halt was approved.
 */
import { statSync } from "node:fs";
import { join } from "node:path";

export interface HaltArtifact {
  label: string;
  /** Path relative to the book directory. */
  relPath: string;
}

export interface HaltDef {
  /** Stable id used as the persistence key + decision routing. */
  id: string;
  /** Orchestrator phase this halt fires at — MUST match _progress.py PHASES. */
  phase: string;
  label: string;
  blurb: string;
  /** Candidate artifacts; the loader keeps only those present on disk. */
  artifacts: HaltArtifact[];
}

export const HALTS: HaltDef[] = [
  {
    id: "gap-analysis",
    phase: "0ci",
    label: "Gap analysis & corpus cross-reference",
    blurb:
      "Before chapters are designed, review what the source covers, the open questions it raises, " +
      "and how the wisdom corpus will enrich it. Approve to let chapter design proceed.",
    artifacts: [
      {
        label: "Open questions",
        relPath: "_system/source/text/_open-questions.md",
      },
      {
        label: "Teaching-ledger coverage",
        relPath: "_system/source/text/_teaching-ledger-coverage.md",
      },
      {
        label: "Reorganization map",
        relPath: "_system/source/text/_reorg-map.md",
      },
      {
        label: "Curation log",
        relPath: "_system/source/text/_curation-log.md",
      },
      {
        label: "Refined edition",
        relPath: "_system/source/text/refined-english.md",
      },
    ],
  },
  {
    id: "source-review",
    phase: "06a",
    label: "Source review",
    blurb: "Approve the refined source text before the series plan is drawn.",
    artifacts: [
      {
        label: "Refined edition",
        relPath: "_system/source/text/refined-english.md",
      },
      { label: "Review gate", relPath: "_system/review-gate.json" },
    ],
  },
  {
    id: "series-plan",
    phase: "0f",
    label: "Series plan",
    blurb:
      "Confirm the chapter list and length tier before per-chapter authoring begins.",
    artifacts: [
      { label: "Series config", relPath: "_system/series-config.yaml" },
      { label: "Chapter-set report", relPath: "_system/chapter-set-report.md" },
    ],
  },
  {
    id: "finalize",
    phase: "finalize",
    label: "Finalize review",
    blurb:
      "The clean version is ready. Review the quality gates and the finalized content before publishing.",
    artifacts: [
      {
        label: "Final review report",
        relPath: "audits/final-review-report.md",
      },
      { label: "Challenger report", relPath: "audits/challenger-report.md" },
      { label: "Review gate", relPath: "_system/review-gate.json" },
    ],
  },
];

export interface ResolvedArtifact extends HaltArtifact {
  exists: boolean;
}

/** The halt (if any) whose phase matches the book's current phase. */
export function haltForPhase(phase: string | null | undefined): HaltDef | null {
  return HALTS.find((h) => h.phase === phase) ?? null;
}

/** Resolve a halt's candidate artifacts to those that actually exist on disk. */
export function resolveArtifacts(
  bookDir: string,
  def: HaltDef,
): ResolvedArtifact[] {
  return def.artifacts.map((a) => ({
    ...a,
    exists: safeIsFile(join(bookDir, a.relPath)),
  }));
}

function safeIsFile(p: string): boolean {
  try {
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

export interface HaltDecision {
  decision: "approved" | "changes";
  notes?: string;
  ts?: string;
}
export type HaltReviews = Record<string, HaltDecision>;
