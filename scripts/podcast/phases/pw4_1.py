"""P4.1 (Wave 4) — design-system tokens and SPA shell.

Detects that the plan-dashboard has:
  - A single design-token stylesheet with all required CSS custom properties
  - A routed SPA entry page with the hub-grid navigation structure
"""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P4.1"
DESCRIPTION = (
    "plan-dashboard/src/styles/theme.css (design tokens) + "
    "plan-dashboard/src/pages/index.astro (SPA shell + hub routing)"
)

REPO_ROOT = Path(__file__).resolve().parents[3]

_TOKENS_FILE = REPO_ROOT / "plan-dashboard" / "src" / "styles" / "theme.css"
_SHELL_FILE = REPO_ROOT / "plan-dashboard" / "src" / "pages" / "index.astro"

# Design-token markers — CSS custom properties the rest of the SPA
# imports from this single stylesheet.
_TOKENS_MARKERS = (
    "--c-bg",
    "--c-accent",
    "--c-ink",
    "--c-planner",
    "--c-green",
    "--c-amber",
    "--c-red",
)

# SPA shell markers — hub-grid routing structure in the entry page.
_SHELL_MARKERS = (
    "hub-grid",
    "hub-card",
    "/architecture",
    "/library",
)


def is_done(repo_root: Path | None = None) -> bool:
    root = repo_root or REPO_ROOT
    tokens = root / "plan-dashboard" / "src" / "styles" / "theme.css"
    shell = root / "plan-dashboard" / "src" / "pages" / "index.astro"
    if not tokens.exists() or not shell.exists():
        return False
    tok_text = tokens.read_text()
    shell_text = shell.read_text()
    return (
        all(m in tok_text for m in _TOKENS_MARKERS)
        and all(m in shell_text for m in _SHELL_MARKERS)
    )


def execute(repo_root: Path | None = None) -> PhaseResult:
    root = repo_root or REPO_ROOT
    tokens = root / "plan-dashboard" / "src" / "styles" / "theme.css"
    shell = root / "plan-dashboard" / "src" / "pages" / "index.astro"

    missing: list[str] = []
    if not tokens.exists():
        missing.append(f"{tokens} not found")
    else:
        tok_text = tokens.read_text()
        for m in _TOKENS_MARKERS:
            if m not in tok_text:
                missing.append(f"theme.css missing token: {m}")

    if not shell.exists():
        missing.append(f"{shell} not found")
    else:
        shell_text = shell.read_text()
        for m in _SHELL_MARKERS:
            if m not in shell_text:
                missing.append(f"index.astro missing marker: {m}")

    if missing:
        return PhaseResult(
            phase_id=PHASE_ID, status="halted",
            message=(
                "Design-system tokens or SPA shell incomplete:\n  "
                + "\n  ".join(missing)
            ),
            evidence_paths=[str(tokens), str(shell)],
        )

    return PhaseResult(
        phase_id=PHASE_ID, status="done",
        message=(
            "Design-system tokens (theme.css) and SPA hub shell (index.astro) "
            "present with all required markers."
        ),
        rows_marked=[PHASE_ID],
        evidence_paths=[str(tokens), str(shell)],
    )
