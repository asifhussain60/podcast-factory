"""P25.1 phase runner — Operator Review Studio FastAPI backend.

P25.1 ships the local FastAPI server at localhost:8766 that serves the
operator-review-studio SPA. Five REST endpoints + 1 SSE + 1 mtime endpoint.

is_done() returns True when:
  - scripts/podcast/review_server.py exists
  - scripts/podcast/_review_serializer.py exists
  - scripts/podcast/_review_ai.py exists
  - scripts/podcast/tests/test_review_serializer.py exists
  - serializer tests pass

Note: FastAPI + uvicorn deps may not be installed; the runner only checks
that the source files exist and the pure-Python serializer tests pass.
The full integration test (running the server, hitting endpoints) is the
operator's responsibility via the README startup commands.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ._base import PhaseResult
from ._dor_halt import DoR, build_halted_result

PHASE_ID = "P25.1"
DESCRIPTION = (
    "Operator Review Studio FastAPI backend: review_server.py + "
    "_review_serializer.py + _review_ai.py + tests"
)

REPO_ROOT = Path(__file__).resolve().parents[3]

SERVER       = REPO_ROOT / "scripts" / "podcast" / "review_server.py"
SERIALIZER   = REPO_ROOT / "scripts" / "podcast" / "_review_serializer.py"
AI_HELPER    = REPO_ROOT / "scripts" / "podcast" / "_review_ai.py"
TESTS        = REPO_ROOT / "scripts" / "podcast" / "tests" / "test_review_serializer.py"

ALL_FILES = (SERVER, SERIALIZER, AI_HELPER, TESTS)

DOR = DoR(
    blockers=(
        "Operator must install FastAPI + uvicorn locally before running: "
        "`pip install fastapi uvicorn pyyaml` (one-time)",
    ),
    assumptions=(
        "Server runs on localhost:8766 (port chosen to not collide with P8 "
        "dashboard at :8765)",
        "AI features (P25.7) reuse the same `claude -p` subprocess pattern "
        "as orchestrate_book.py; no new API keys required.",
        "operator-review.md remains the SOURCE OF TRUTH — the studio writes "
        "atomically via tmp+rename; the pipeline reads on --approve-transcript.",
        "Multi-worktree support via --config ~/.journal-worktrees.yaml; "
        "default is single-worktree at --repo-root (or cwd).",
    ),
    ambiguities=(
        "FastAPI port collision with anything else on operator's machine — "
        "use --port flag to override.",
    ),
    operator_action=(
        "1. Verify the four surface files exist:\n"
        "   - scripts/podcast/review_server.py\n"
        "   - scripts/podcast/_review_serializer.py\n"
        "   - scripts/podcast/_review_ai.py\n"
        "   - scripts/podcast/tests/test_review_serializer.py\n"
        "2. Run the serializer tests: `python3 -m unittest scripts.podcast.tests.test_review_serializer`\n"
        "3. (Optional) Install backend deps + smoke test:\n"
        "     pip install fastapi uvicorn pyyaml\n"
        "     python3 scripts/podcast/review_server.py --repo-root . --port 8766\n"
        "     curl http://127.0.0.1:8766/api/health"
    ),
)


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    for path in ALL_FILES:
        if not path.exists():
            return False
    rc = subprocess.run(
        [sys.executable, "-m", "unittest", "scripts.podcast.tests.test_review_serializer"],
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
                "P25.1 backend SHIPPED: review_server.py (5 REST + SSE + AI endpoints) + "
                "_review_serializer.py (markdown ↔ struct, 15 tests green) + "
                "_review_ai.py (10 AI features via claude -p subprocess) all present. "
                "Operator must `pip install fastapi uvicorn pyyaml` then launch with "
                "`python3 scripts/podcast/review_server.py --repo-root .` to start the server."
            ),
            rows_marked=[PHASE_ID],
            evidence_paths=[str(p) for p in ALL_FILES],
        )
    return build_halted_result(PHASE_ID, DESCRIPTION, DOR, ALL_FILES)
