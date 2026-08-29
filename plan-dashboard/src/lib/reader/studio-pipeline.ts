/**
 * studio-pipeline.ts — the sequential Studio flow model.
 *
 * The content pipeline is one ordered journey over a single chosen book:
 *   Intake → Source Review → Edit & Enrich → Publish
 *
 * Each step's status is derived from the book's orchestrator-state.json and
 * (for the review gate) review-gate.json on disk. This is the single source of
 * truth the StudioShell stepper renders from, so the on-screen flow always
 * matches the real pipeline state.
 */
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { findContent } from "../content-paths";

export type StepId = "intake" | "review" | "edit" | "publish";

/**
 * Lifecycle bucket for the Studio picker's status filter:
 *   'in-the-works' — real authoring/pipeline work has happened (default view)
 *   'up-next'      — scaffolded/batch-ingested only; active work not begun
 *   'published'    — status field flipped to published
 */
export type StatusBucket = "in-the-works" | "up-next" | "published";

export type StepState = "done" | "active" | "pending" | "blocked";

export interface StudioStep {
  id: StepId;
  label: string;
  blurb: string;
  state: StepState;
  detail: string;
}

export const STUDIO_STEPS: { id: StepId; label: string; blurb: string }[] = [
  {
    id: "intake",
    label: "Intake",
    blurb: "Create the workshop and set editorial decisions.",
  },
  {
    id: "review",
    label: "Source Review",
    blurb: "Approve the refined source before authoring.",
  },
  {
    id: "edit",
    label: "Edit & Enrich",
    blurb: "Review stages, edit chapters, plan enrichment.",
  },
  {
    id: "publish",
    label: "Publish",
    blurb: "Finalize and promote to the published catalog.",
  },
];

/**
 * Canonical phase order — index used to compare progress. Mirrors the PHASES
 * tuple in `scripts/podcast/_progress.py`, the real single source of truth
 * (every phase id passed to that script's `update_phase()` must appear there
 * or it raises). This array must be kept in sync with it by hand — there is
 * no fixture pinning this pair yet — because a phase name absent here makes
 * `phaseIndex()` return -1 for a book that has actually reached it, which
 * `Math.max(phaseIndex(last_completed_phase), phaseIndex(phase))` then reads
 * as "barely started" (see reader-narration, fixed 2026-08-29: two published
 * books' Studio cards showed "Intake" for months because of this).
 */
const PHASE_ORDER = [
  "pre-flight",
  "branch",
  "scaffold",
  "0a",
  "0b",
  "0c",
  "0ci",
  "0d",
  "0e",
  "0literary",
  "06a",
  "0f",
  "0g",
  "per-chapter",
  "per-chapter-optimize",
  "per-chapter-slides",
  "audio-script",
  "audio-render",
  "finalize",
  "audio-ingest",
  "0book-design",
  "0book-compose",
  "0book-illustrate",
  "0book-slide-import",
  "0book-render",
  "reader-narration",
  "publish",
  "trainer",
  "merge",
  "done",
];

function phaseIndex(phase: string | null | undefined): number {
  if (!phase) return -1;
  const i = PHASE_ORDER.indexOf(phase);
  return i;
}

/**
 * The Sessions lane's own phase vocabulary (scripts/podcast/sessions/*.py) —
 * a lecture transcript being ingested, transcribed, articulated, prefaced and
 * apparatus-annotated, never any of the orchestrator's 0a-0g/per-chapter/
 * finalize phases above. A Sessions-lane book's `phase`/`last_completed_phase`
 * is ALWAYS one of these six strings (per `_phase_vocabulary.py`), never one
 * from PHASE_ORDER, so it was
 * appending these onto the SAME shared index, not using a parallel one, that
 * would be the bug: `sessions-ingest` sorted anywhere in PHASE_ORDER would
 * either always or never satisfy `reached >= idxOf("0a")`-style comparisons
 * against phases that book never has, which is a coincidence of array
 * position, not a real answer. Kept as its own index instead (see
 * `buildSessionsSteps`), read from the SAME state-file shape the orchestrator
 * writes (`phase`, `phase_status`, `last_completed_phase`, plus
 * `pipeline_mode: "sessions_lane"`, which is what selects this branch).
 */
const SESSIONS_PHASE_ORDER = [
  "sessions-ingest",
  "sessions-transcribe",
  "sessions-articulate",
  "sessions-read-along",
  "sessions-preface",
  "sessions-apparatus",
];

function sessionsPhaseIndex(phase: string | null | undefined): number {
  if (!phase) return -1;
  return SESSIONS_PHASE_ORDER.indexOf(phase);
}

interface RawState {
  phase?: string;
  phase_status?: string;
  last_completed_phase?: string;
  pipeline_mode?: string;
  status?: string;
}

async function readJson<T>(path: string): Promise<T | null> {
  try {
    return JSON.parse(await readFile(path, "utf-8")) as T;
  } catch {
    return null;
  }
}

/**
 * Classify a book into a Studio-picker filter bucket.
 *
 * Rule order matters:
 *   1. published status wins outright;
 *   2. no completed phase → up-next;
 *   3. a completed phase the canonical order doesn't know (e.g. 0book-render)
 *      still proves real work → in-the-works;
 *   4. only the automated ingest/refine ran (≤ 0b) → up-next — this is the
 *      batch-scaffolded-volume case;
 *   5. anything further along → in-the-works.
 */
export function classifyStatusBucket(
  status: string | undefined,
  lastCompletedPhase: string | null | undefined,
): StatusBucket {
  if (status === "published") return "published";
  if (!lastCompletedPhase) return "up-next";
  const idx = phaseIndex(lastCompletedPhase);
  if (idx === -1) return "in-the-works";
  if (idx <= phaseIndex("0b")) return "up-next";
  return "in-the-works";
}

/** Read a book's state file and classify it. `status` comes from listContent(). */
export async function loadStatusBucket(
  slug: string,
  status: string | undefined,
): Promise<StatusBucket> {
  const ref = await findContent(slug);
  const state = ref?.dir
    ? await readJson<RawState>(
        join(ref.dir, "_system", "orchestrator-state.json"),
      )
    : null;
  return classifyStatusBucket(status, state?.last_completed_phase);
}

/**
 * The Sessions lane's own four-step model — same StepId/StudioStep shape the
 * orchestrator lane renders, so the shared stepper component needs no branch
 * of its own, but derived from SESSIONS_PHASE_ORDER rather than PHASE_ORDER.
 * There is no review-gate.json equivalent here (no automated pre-authoring
 * source-refine step to approve) — the transcript itself, once transcribed,
 * IS the reviewed source a lecture-based book articulates from, and the
 * standing "Compose tab is the review gate" rule covers the human checkpoint
 * that matters, same as it does for every other bucket.
 */
function buildSessionsSteps(state: RawState | null): StudioStep[] {
  const completed = sessionsPhaseIndex(state?.last_completed_phase);
  const current = sessionsPhaseIndex(state?.phase);
  const reached = Math.max(completed, current);
  const idxOf = (p: string) => SESSIONS_PHASE_ORDER.indexOf(p);

  const intakeDone = reached >= idxOf("sessions-ingest");
  const intake: StudioStep = {
    id: "intake",
    label: "Intake",
    blurb: STUDIO_STEPS[0].blurb,
    state: intakeDone ? "done" : "active",
    detail: intakeDone
      ? "Transcript ingested"
      : state
        ? "Ingest in progress"
        : "Not started",
  };

  const reviewDone = reached >= idxOf("sessions-transcribe");
  const review: StudioStep = {
    id: "review",
    label: "Source Review",
    blurb: STUDIO_STEPS[1].blurb,
    state: reviewDone ? "done" : intakeDone ? "active" : "pending",
    detail: reviewDone
      ? "Transcribed"
      : intakeDone
        ? "Transcribing"
        : "Waiting on intake",
  };

  const editDone = reached >= idxOf("sessions-apparatus");
  let editState: StepState = "pending";
  let editDetail = "Waiting on source review";
  if (editDone) {
    editState = "done";
    editDetail = "Articulated and composed";
  } else if (reviewDone) {
    editState = "active";
    editDetail =
      state?.phase === "sessions-articulate"
        ? "Articulating chapters"
        : state?.phase === "sessions-read-along"
          ? "Timing the read-along"
          : state?.phase === "sessions-preface"
            ? "Writing front matter"
            : state?.phase === "sessions-apparatus"
              ? "Applying citations & vowelling"
              : "In progress";
  }
  const edit: StudioStep = {
    id: "edit",
    label: "Edit & Enrich",
    blurb: STUDIO_STEPS[2].blurb,
    state: editState,
    detail: editDetail,
  };

  let pubState: StepState = "pending";
  let pubDetail = "Waiting on authoring";
  if (state?.status === "published") {
    pubState = "done";
    pubDetail = "Published";
  } else if (editDone) {
    pubState = "active";
    pubDetail = "Ready for Compose review";
  }
  const publish: StudioStep = {
    id: "publish",
    label: "Publish",
    blurb: STUDIO_STEPS[3].blurb,
    state: pubState,
    detail: pubDetail,
  };

  return [intake, review, edit, publish];
}

/**
 * Build the four-step status model for a book. Resilient: a book with no state
 * file is treated as "intake active, everything else pending".
 */
export async function loadStudioPipeline(slug: string): Promise<StudioStep[]> {
  const ref = await findContent(slug);
  const dir = ref?.dir ?? "";

  const state = dir
    ? await readJson<RawState>(join(dir, "_system", "orchestrator-state.json"))
    : null;

  if (state?.pipeline_mode === "sessions_lane") {
    return buildSessionsSteps(state);
  }

  const gate = dir
    ? await readJson<{
        approved?: boolean;
        warnings?: { severity?: string }[];
      }>(join(dir, "_system", "review-gate.json"))
    : null;

  const completed = phaseIndex(state?.last_completed_phase);
  const current = phaseIndex(state?.phase);
  const reached = Math.max(completed, current);

  const idxOf = (p: string) => PHASE_ORDER.indexOf(p);

  // ── Intake: scaffold + Azure ingest (0a) ──────────────────
  const intakeDone = reached >= idxOf("0a");
  const intake: StudioStep = {
    id: "intake",
    label: "Intake",
    blurb: STUDIO_STEPS[0].blurb,
    state: intakeDone ? "done" : reached >= 0 ? "active" : "active",
    detail: intakeDone
      ? "Source ingested"
      : state
        ? "Ingest in progress"
        : "Not started",
  };

  // ── Source Review: 06a gate ───────────────────────────────
  const p0 = (gate?.warnings ?? []).filter((w) => w?.severity === "P0").length;
  let reviewState: StepState;
  let reviewDetail: string;
  if (gate?.approved || reached >= idxOf("0f")) {
    // Either explicitly approved, or the pipeline has progressed past the 06a
    // gate (reaching 0f+ implies the source review was cleared).
    reviewState = "done";
    reviewDetail = gate?.approved ? "Source approved" : "Source cleared";
  } else if (gate) {
    reviewState = p0 > 0 ? "blocked" : "active";
    reviewDetail =
      p0 > 0
        ? `${p0} blocking issue${p0 === 1 ? "" : "s"}`
        : "Awaiting approval";
  } else if (reached >= idxOf("06a")) {
    reviewState = "active";
    reviewDetail = "Ready to review";
  } else {
    reviewState = intakeDone ? "active" : "pending";
    reviewDetail = intakeDone ? "Ready to review" : "Waiting on intake";
  }
  const review: StudioStep = {
    id: "review",
    label: "Source Review",
    blurb: STUDIO_STEPS[1].blurb,
    state: reviewState,
    detail: reviewDetail,
  };

  // ── Edit & Enrich: 0b..0e + per-chapter authoring ─────────
  const editStarted = reached >= idxOf("0b");
  const editDone = reached >= idxOf("finalize");
  let editState: StepState = "pending";
  let editDetail = "Waiting on source review";
  if (editDone) {
    editState = "done";
    editDetail = "Authoring complete";
  } else if (editStarted) {
    editState = "active";
    editDetail =
      state?.phase === "per-chapter" ? "Per-chapter authoring" : "In progress";
  } else if (reviewState === "done") {
    editState = "active";
    editDetail = "Ready to author";
  }
  const edit: StudioStep = {
    id: "edit",
    label: "Edit & Enrich",
    blurb: STUDIO_STEPS[2].blurb,
    state: editState,
    detail: editDetail,
  };

  // ── Publish: finalize halt + publish ──────────────────────
  // `status` (not `phase`) is the source of truth here: publish_to_library.py
  // flips `state.status` to "published" in place and never advances `phase`
  // to the literal "publish" step — draft/published is a status field, not a
  // pipeline phase, for the current status-flip publish model. A book whose
  // last recorded phase is e.g. "reader-narration" can already be published.
  let pubState: StepState = "pending";
  let pubDetail = "Waiting on authoring";
  if (state?.status === "published" || reached >= idxOf("publish")) {
    pubState = "done";
    pubDetail = "Published";
  } else if (state?.phase === "finalize") {
    pubState = "active";
    pubDetail = "Ready for publish review";
  } else if (editDone) {
    pubState = "active";
    pubDetail = "Ready to publish";
  }
  const publish: StudioStep = {
    id: "publish",
    label: "Publish",
    blurb: STUDIO_STEPS[3].blurb,
    state: pubState,
    detail: pubDetail,
  };

  return [intake, review, edit, publish];
}
