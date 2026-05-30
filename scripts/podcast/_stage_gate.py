"""_stage_gate.py — WC8 per-stage review gate (Phase 6 productionisation).

Reads and writes the per-chapter stage-review JSON that the Studio editor
produces when a reviewer approves a stage artifact.  The stage runner and the
Astro API both import from here — one schema, one reader.

Schema (mirrors stage-review.ts):
    content/drafts/books/<slug>/_system/review/<chapter>.json
    {
      "slug": "ayyuhal-walad",
      "chapter": "ch01-...",
      "stages": {
        "denoised": { "approved": true, "approved_at": "2026-05-30T...", "notes": "" },
        "normalized": { "approved": false, "approved_at": null },
        ...
      }
    }
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from _paths import REPO_ROOT  # noqa: E402

# Canonical stage order for Ayyuhal-Walad WC8 pipeline.
# source → core: produced by intake_stage.py / agent (Azure OCR + alignment)
# denoised:      produced by gemini_refine.py --mode denoise
# normalized:    produced by gemini_refine.py --mode normalize
# augmented:     produced by inline agent (knowledge + Quran refs)
# narrator:      produced by narrator_additions.py
STAGE_ORDER: list[str] = [
    "source",
    "core",
    "denoised",
    "normalized",
    "augmented",
    "narrator",
]

# File artifact emitted for each stage under _stages/<chapter>/
STAGE_ARTIFACTS: dict[str, str] = {
    "source": "source.md",
    "core": "core.md",
    "denoised": "denoised.md",
    "normalized": "normalized.md",
    "augmented": "augmented.md",
    "narrator": "additions-narrator.md",
}


def _review_path(slug: str, chapter: str) -> Path:
    return (
        REPO_ROOT
        / "content" / "drafts" / "books" / slug
        / "_system" / "review" / f"{chapter}.json"
    )


def _stages_dir(slug: str, chapter: str) -> Path:
    return REPO_ROOT / "content" / "drafts" / "books" / slug / "_stages" / chapter


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------

def read_stage_review(slug: str, chapter: str) -> dict:
    """Return the full review document, or an empty shell if none exists."""
    p = _review_path(slug, chapter)
    if not p.exists():
        return {"slug": slug, "chapter": chapter, "stages": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"slug": slug, "chapter": chapter, "stages": {}}


def is_stage_approved(slug: str, chapter: str, stage: str) -> bool:
    """Return True if the stage has been explicitly approved in the review JSON."""
    doc = read_stage_review(slug, chapter)
    entry = doc.get("stages", {}).get(stage, {})
    return bool(entry.get("approved", False))


def stage_artifact_exists(slug: str, chapter: str, stage: str) -> bool:
    """Return True if the stage's output artifact is present on disk."""
    artifact = STAGE_ARTIFACTS.get(stage)
    if not artifact:
        return False
    return (_stages_dir(slug, chapter) / artifact).exists()


# ---------------------------------------------------------------------------
# Stage state summary
# ---------------------------------------------------------------------------

def chapter_stage_summary(slug: str, chapter: str) -> list[dict]:
    """Return one dict per stage with artifact/approval state.

    Shape: [{"stage": str, "artifact": bool, "approved": bool, "status": str}, ...]
    status: "done_approved" | "done_pending" | "missing"
    """
    doc = read_stage_review(slug, chapter)
    stages_review = doc.get("stages", {})
    result = []
    for s in STAGE_ORDER:
        has_artifact = stage_artifact_exists(slug, chapter, s)
        approved = bool(stages_review.get(s, {}).get("approved", False))
        if has_artifact and approved:
            status = "done_approved"
        elif has_artifact:
            status = "done_pending"
        else:
            status = "missing"
        result.append({"stage": s, "artifact": has_artifact, "approved": approved, "status": status})
    return result


def next_runnable_stage(slug: str, chapter: str) -> str | None:
    """Return the next stage that can be run (all prerequisites approved).

    A stage is runnable when:
    - Its own artifact is missing (i.e. not yet produced), AND
    - The preceding stage's artifact exists AND is approved (or it's the first stage).

    Returns None when all stages are done, or when the next missing stage's
    prerequisite has not been approved yet (runner should wait).
    """
    summary = chapter_stage_summary(slug, chapter)
    for i, entry in enumerate(summary):
        if entry["status"] != "missing":
            continue
        # This stage needs to be produced.
        if i == 0:
            return entry["stage"]  # first stage — no prerequisite
        prev = summary[i - 1]
        if prev["status"] == "done_approved":
            return entry["stage"]
        # prerequisite not yet approved
        return None  # caller should surface "awaiting approval for {prev['stage']}"
    return None  # all stages present


def awaiting_approval_stage(slug: str, chapter: str) -> str | None:
    """Return the stage that is done but not yet approved (blocking the pipeline)."""
    summary = chapter_stage_summary(slug, chapter)
    for entry in summary:
        if entry["status"] == "done_pending":
            return entry["stage"]
    return None


# ---------------------------------------------------------------------------
# Writer (called by approve_book / Studio API)
# ---------------------------------------------------------------------------

def set_stage_approved(
    slug: str,
    chapter: str,
    stage: str,
    *,
    approved: bool = True,
    notes: str = "",
) -> dict:
    """Write an approval (or revoke) into the review JSON and return the full doc."""
    doc = read_stage_review(slug, chapter)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry: dict = {"approved": approved, "approved_at": now if approved else None}
    if notes:
        entry["notes"] = notes
    doc.setdefault("stages", {})[stage] = entry
    p = _review_path(slug, chapter)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc
