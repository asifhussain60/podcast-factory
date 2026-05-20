"""P24.1 phase runner — podcast-blueprint agent spec + skill scaffold + schema + handbook.

P24.1 ships the integration SURFACE for podcast-blueprint:
  • agent spec (dual-homed: infra/claude-agents/ + .github/agents/)
  • skill scaffold (skills-staging/podcast-blueprint/SKILL.md)
  • JSON-Schema for classification.json
  • arc-conventions.md template
  • operator handbook (blueprint-protocol.md)
  • pydantic-style dataclass models + schema validator (_blueprint_schema.py)
  • schema-validation tests (test_blueprint_schema.py)
  • this runner

P24.1 does NOT implement the three layers (those are P24.2 + P24.3, BLOCKED on
the truncated three-layer architecture body from Air session 7768a31c
2026-05-20). When the Air handoff arrives, P24.2 unblocks Layer 1 and P24.3
unblocks Layers 2 + 3.

is_done() returns True when every surface artifact is in place AND the schema
test suite is green.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ._base import PhaseResult
from ._dor_halt import DoR, build_halted_result

PHASE_ID = "P24.1"
DESCRIPTION = (
    "podcast-blueprint surface: agent spec + skill scaffold + classification "
    "schema + arc-conventions template + handbook + pydantic models + tests"
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# Every artifact that P24.1 ships. Each must exist and (for files with content
# requirements) contain the locked-decision markers.
AGENT_SPEC_CANONICAL = REPO_ROOT / "infra" / "claude-agents" / "podcast-blueprint.md"
AGENT_SPEC_MIRROR    = REPO_ROOT / ".github" / "agents" / "podcast-blueprint.agent.md"
SKILL_SCAFFOLD       = REPO_ROOT / "skills-staging" / "podcast-blueprint" / "SKILL.md"
HANDBOOK             = REPO_ROOT / "content" / "podcast" / ".skill" / "handbook" / "blueprint-protocol.md"
CLASSIFICATION_SCHEMA = REPO_ROOT / "content" / "podcast" / ".skill" / "handbook" / "_schemas" / "classification.schema.json"
ARC_CONVENTIONS_TEMPLATE = REPO_ROOT / "content" / "podcast" / ".skill" / "handbook" / "_templates" / "arc-conventions.template.md"
SCHEMA_MODULE        = REPO_ROOT / "scripts" / "podcast" / "_blueprint_schema.py"
SCHEMA_TESTS         = REPO_ROOT / "scripts" / "podcast" / "tests" / "test_blueprint_schema.py"

ALL_ARTIFACTS = (
    AGENT_SPEC_CANONICAL, AGENT_SPEC_MIRROR, SKILL_SCAFFOLD, HANDBOOK,
    CLASSIFICATION_SCHEMA, ARC_CONVENTIONS_TEMPLATE,
    SCHEMA_MODULE, SCHEMA_TESTS,
)

# Marker substrings that must appear in each artifact to prove the locked
# decisions are reflected (not just the file existing as a stub).
LOCKED_MARKER_PHRASES = (
    "podcast-blueprint",           # locked decision 1: name
    "05.5-blueprint",              # locked decision 2: orchestrator slug
)

# The four locked decisions from the 2026-05-20 Air handoff. The DoR prints
# these every tick so the human reviewing the launchd log knows what is
# pending vs already settled.
DOR = DoR(
    blockers=(
        "P24.2 (Layer 1 scan/classify prompt skeleton) is BLOCKED on receipt of "
        "the truncated three-layer architecture body from Air session 7768a31c "
        "(2026-05-20). The pasted design ended at '### Three-layer architecture' "
        "without describing the layer prompts.",
        "P24.3 (Layer 2 episode planner + Layer 3 convention emitter prompts) is "
        "BLOCKED on the same Air handoff.",
    ),
    assumptions=(
        "The four LOCKED decisions stand and will not be re-debated: "
        "(1) name=podcast-blueprint; "
        "(2) slot=phase 0b.5 (orchestrator slug 05.5-blueprint); "
        "(3) Layer 1 auto-upgrades the model for Layers 2-3 via "
        "classification.recommended_model_for_layer_2 unless --force-model overrides; "
        "(4) arc-conventions.md is OPTIONAL input, agent-seeded DRAFT on first run, "
        "operator-editable thereafter, Layer 3 NEVER overwrites.",
        "P24.1 is the integration SURFACE only — no layer prompts authored here. "
        "The orchestrator slot reservation, schemas, agent spec, and tests are "
        "what unblock P24.4 (orchestrator slot wiring) to start landing the shell.",
        "Books past slot 05.5 at protocol-introduction time (asaas-al-taveel "
        "mid-0b, kitab-al-riyad at 0d→0e) are NOT replanned by blueprint.",
    ),
    ambiguities=(
        "Exact word-count target per episode planning_mode: defaults will be "
        "documented in arc-conventions.md after the first live blueprint run "
        "on tiny-book.",
        "Whether Layer 1 self-classification should be run in TWO passes (cheap "
        "scan → confidence score → conditional Sonnet re-scan if confidence "
        "low) — resolution deferred to P24.2 design.",
    ),
    operator_action=(
        "1. Retransmit the truncated three-layer architecture body from Air "
        "session 7768a31c (the section beginning '### Three-layer architecture' "
        "and continuing through Layer 1, Layer 2, Layer 3 prompt skeletons).\n"
        "2. Review the P24.1 surface artifacts:\n"
        "   - infra/claude-agents/podcast-blueprint.md\n"
        "   - .github/agents/podcast-blueprint.agent.md\n"
        "   - content/podcast/.skill/handbook/blueprint-protocol.md\n"
        "   - content/podcast/.skill/handbook/_schemas/classification.schema.json\n"
        "   - content/podcast/.skill/handbook/_templates/arc-conventions.template.md\n"
        "   - skills-staging/podcast-blueprint/SKILL.md\n"
        "   - scripts/podcast/_blueprint_schema.py\n"
        "   - scripts/podcast/tests/test_blueprint_schema.py\n"
        "3. Confirm the four locked decisions are correctly encoded. If any "
        "wording in the agent spec or handbook is wrong, edit IN PLACE — the "
        "test suite enforces the schema, not the prose.\n"
        "4. Once the truncated handoff arrives, P24.2 + P24.3 (Layer 1/2/3 "
        "prompts) can be authored against this handbook."
    ),
)


def is_done(repo_root: Path | None = None) -> bool:
    """Every surface artifact exists, locked markers present, schema tests green."""
    if repo_root is None:
        repo_root = REPO_ROOT
    for path in ALL_ARTIFACTS:
        if not path.exists():
            return False
    # Locked-decision markers must appear in the agent spec + handbook + SKILL.
    # JSON / Python files have their own structure; we don't grep them for
    # the literal phrases.
    text_files_with_markers = (AGENT_SPEC_CANONICAL, AGENT_SPEC_MIRROR, HANDBOOK, SKILL_SCAFFOLD)
    for path in text_files_with_markers:
        text = path.read_text(encoding="utf-8")
        for marker in LOCKED_MARKER_PHRASES:
            if marker not in text:
                return False
    # Schema tests must be green.
    rc = subprocess.run(
        [sys.executable, "-m", "unittest", "scripts.podcast.tests.test_blueprint_schema"],
        cwd=repo_root, capture_output=True, timeout=60,
    ).returncode
    return rc == 0


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="done",
            message=(
                "podcast-blueprint surface SHIPPED: agent spec + skill scaffold + "
                "JSON-Schema + arc-conventions template + handbook + pydantic models "
                "+ 28 schema tests green. Awaiting Air handoff (P24.2 + P24.3 "
                "Layer 1/2/3 prompt skeletons)."
            ),
            rows_marked=[PHASE_ID],
            evidence_paths=[str(p) for p in ALL_ARTIFACTS],
        )
    return build_halted_result(PHASE_ID, DESCRIPTION, DOR, ALL_ARTIFACTS)
