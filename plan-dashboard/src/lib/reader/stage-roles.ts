/**
 * stage-roles.ts — what each transformation stage DOES, in plain English.
 *
 * Drives the left-rail role badges and the centre-pane stage header card so the
 * editor shows the *work* a stage performed, not just its name. Stage ids mirror
 * `STAGE_DEFS` in book-workspace.ts (and Python `_stage_gate.STAGE_ORDER`).
 *
 * `kind` maps onto the existing theme swimlane tokens (--c-kind-mechanical /
 * -agentic / -hybrid / -gate) — no new colours.
 */
export type StageKind = "mechanical" | "agentic" | "hybrid" | "gate";

export interface StageRole {
  /** Short plain-English label of the transformation this stage performs. */
  role: string;
  /** Visual accent kind (maps to --c-kind-* tokens). */
  kind: StageKind;
  /** The tool/agent that performs it (shown on the centre-pane card). */
  tool: string;
}

export const STAGE_ROLES: Record<string, StageRole> = {
  source: { role: "Raw OCR", kind: "mechanical", tool: "Azure OCR" },
  core: { role: "Bilingual align", kind: "mechanical", tool: "Azure" },
  denoised: { role: "Noise stripped", kind: "agentic", tool: "Gemini" },
  normalized: { role: "Re-voiced", kind: "agentic", tool: "Gemini" },
  augmented: {
    role: "Wisdom woven in",
    kind: "hybrid",
    tool: "Enrichment corpus",
  },
  literary: {
    role: "Literary prose",
    kind: "agentic",
    tool: "Gemini literary",
  },
  narrator: {
    role: "Lecture additions",
    kind: "hybrid",
    tool: "Shaykh additions",
  },
};

/** Resilient lookup — unknown ids fall back to an empty, neutral role. */
export function stageRole(id: string): StageRole {
  return STAGE_ROLES[id] ?? { role: "", kind: "mechanical", tool: "" };
}
