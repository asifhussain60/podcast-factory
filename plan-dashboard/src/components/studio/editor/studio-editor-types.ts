/**
 * studio-editor-types.ts — domain types for the Studio editor surface
 * (stages, chapters, lineages, pipeline rail). Extracted from StudioEditor.tsx
 * (R2 pass 1a — mechanical, verbatim).
 */

export interface Stage {
  id: string;
  label: string;
  slice: string;
  available: boolean;
  html: string;
  augMeta?: string | null;
}

export interface StageMetric {
  id: string;
  available: boolean;
  words: number;
  chars: number;
  sentences: number;
  deltaPct: number | null;
  comparedTo: string | null;
}

export interface Chapter {
  slug: string;
  title: string;
  stages: Stage[];
  metrics: StageMetric[];
  reviewed: Record<string, { approved: boolean; approved_at?: string | null }>;
  /** Which stages have an unapproved autosaved draft (mutated locally on approve). */
  drafted?: Record<string, boolean>;
  finalized?: { at: string } | null;
}

/** A coherent stage set under one root. 'current' is the live rebuild; archived
 *  lineages (earlier full-stage runs) are view-only and never editable. */
export interface Lineage {
  id: string;
  label: string;
  chapters: Chapter[];
}

/** A pipeline phase (Intake → Source Review → Edit & Enrich → Publish), shown
 *  as the top tier of the left rail so the rail is the single pipeline timeline
 *  (the top horizontal stepper is suppressed on the Edit page). */
export interface PipelineStep {
  id: string;
  label: string;
  state: string; // 'done' | 'active' | 'pending' | 'blocked'
  detail: string;
}
