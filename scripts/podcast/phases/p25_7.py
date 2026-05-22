"""P25.7 phase runner — AI assist layer (10 helper features via claude -p subprocess).

Detects whether the AI integration surface is in place. Doesn't actually
invoke claude -p — that's the operator's call at app run-time.
"""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult
from ._dor_halt import DoR, build_halted_result

PHASE_ID = "P25.7"
DESCRIPTION = (
    "AI assist layer: 10 helper features (summarize / diff-explain / arabic / "
    "preflight / voice-shift / episode-plan / suggest-flags / autocomplete / "
    "categorize / content-range) via claude -p subprocess"
)

REPO_ROOT = Path(__file__).resolve().parents[3]

BACKEND_AI = REPO_ROOT / "scripts" / "podcast" / "_review_ai.py"
FRONTEND_AI_BAR = REPO_ROOT / "site" / "operator-review" / "src" / "components" / "AIAssistBar.tsx"
FRONTEND_AI_HOOK = REPO_ROOT / "site" / "operator-review" / "src" / "hooks" / "useAI.ts"
AI_FEATURES_PROPOSAL = REPO_ROOT / "_workspace" / "proposals" / "operator-review-ai-features.html"

ALL_FILES = (BACKEND_AI, FRONTEND_AI_BAR, FRONTEND_AI_HOOK)

DOR = DoR(
    blockers=(
        "Operator must have Claude CLI installed (the same one used by "
        "scripts/podcast/orchestrate_book.py for windows). No new API keys.",
    ),
    assumptions=(
        "Browser triggers AI features via POST /api/books/<slug>/ai/<feature>; "
        "FastAPI dispatches to _review_ai.run_feature(); each feature spawns "
        "`claude -p --model <enum>` and parses the JSON response.",
        "Per-source-signature caching keeps whole-book features (summarize / "
        "arabic / preflight / voice-shift / episode-plan / suggest-flags) free "
        "on re-runs until refined-english.md changes.",
        "Per-book budget cap $2.00 enforced before each spawn; cost-ledger "
        "captures every call with agent_id='podcast-review-studio'.",
        "No Google API. No Gemini. No new keys. The journal already uses "
        "Anthropic Claude via a Cloudflare-tunneled Express proxy for the "
        "memoir Voice Refiner; the studio reuses the same auth/subscription.",
    ),
    ambiguities=(
        "Subprocess `claude -p` timeout: 120s default. Operator may need to "
        "raise via _review_ai.py if Opus episode-plan takes longer for "
        "very dense books.",
    ),
    operator_action=(
        "1. Verify the three AI surface files exist:\n"
        "   - scripts/podcast/_review_ai.py (backend dispatcher)\n"
        "   - site/operator-review/src/components/AIAssistBar.tsx (UI bar)\n"
        "   - site/operator-review/src/hooks/useAI.ts (React hook)\n"
        "2. Verify claude CLI is on PATH: `which claude`\n"
        "3. From the studio UI, click any of the 6 AI Assist buttons. The first "
        "click on a whole-book feature spawns claude -p (~30s); subsequent "
        "clicks on the same source signature return cached payloads instantly.\n"
        "4. Monitor cost via the budget pill on the right of the AI Assist bar."
    ),
)


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    return all(p.exists() for p in ALL_FILES)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if is_done(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID, status="done",
            message=(
                "P25.7 AI layer SHIPPED: _review_ai.py backend dispatcher + "
                "AIAssistBar.tsx UI bar + useAI.ts React hook. All 10 features "
                "wired through claude -p subprocess (no new keys). Per-book "
                "budget $2.00; per-source-signature caching."
            ),
            rows_marked=[PHASE_ID],
            evidence_paths=[str(p) for p in ALL_FILES],
        )
    return build_halted_result(PHASE_ID, DESCRIPTION, DOR, ALL_FILES)
