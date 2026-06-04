#!/usr/bin/env python3
"""_convergence.py — per-chapter convergence loop runner (Phase B).

The autonomous orchestrator's per-chapter loop, lifted into its own module so
`orchestrate_book.py` stays focused on phase sequencing. Per the v2 spec
(`docs/architecture/index.html#convergence`), each chapter goes through:

    extract → author framing → build episode .txt → CONVERGENCE LOOP → ship

The convergence loop here implements three layers of cap:

    Inner (per challenger invocation)  : 5 iterations  — enforced by the
                                                          challenger agent itself
    Middle (this module — per chapter) : 3 outer iterations
    Outer (per book)                   : 24h time cap, $50 cost cap
                                          — enforced by orchestrate_book.py

Decision rule (per chapter, per outer iteration):

    SHIP-READY                                      → break, ship
    SHIP-WITH-CAUTION, iter ≥ 2                     → ship + flag (no P0)
    SHIP-WITH-CAUTION, iter < 2                     → fixer on P1s, retry
    BLOCKED (any P0)                                → fixer on P0s (max 3
                                                       fixer attempts), retry
    iter == 3 still BLOCKED or SHIP-WITH-CAUTION    → HALT (FAILED) — surface
                                                       to orchestrator/user
                                                       with full finding carry-
                                                       over; never silently
                                                       downgrade a BLOCKED
                                                       verdict to a ship-state.

Returns a `ChapterOutcome` dataclass naming the verdict + iteration count
+ any P0/P1 carry-over for the orchestrator's log.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _authoring import (   # noqa: E402
    AuthoringError,
    invoke_challenger,
    invoke_fixer,
)

# Path to build_episode_txt.py (same directory as this module).
_BUILD_EPISODE_TXT = Path(__file__).resolve().parent / "build_episode_txt.py"

MAX_OUTER_ITERATIONS = 3
MAX_FIXER_ATTEMPTS_PER_P0 = 3
SHIP_WITH_CAUTION_MIN_ITER = 2  # iter ≥ this → accept SHIP-WITH-CAUTION
CONVERGENCE_VERSION = "1.0"


@dataclass
class ChapterOutcome:
    """The verdict-and-state of one chapter's convergence pass."""
    chapter_slug: str
    final_verdict: str               # "SHIP-READY" | "SHIP-WITH-CAUTION" | "FAILED"
    outer_iterations: int
    fixer_attempts: int
    p0_remaining: int
    p1_remaining: int
    p2_remaining: int
    peq_total: float | None = None   # last PEQ total recorded; None if not scored
    notes: list[str] = field(default_factory=list)


# ─── Episode-txt rebuild helper ──────────────────────────────────────────────

def _find_episode_id(book_dir: Path, chapter_slug: str) -> str | None:
    """Derive the EP##-<slug> id from the episode-drafts directory.

    Looks for a subdirectory of ``BOOK_DIR/_system/episode-drafts/`` whose
    name ends with ``-<chapter_slug>``.  Returns the directory name (e.g.
    ``EP02-will-command-and-the-seven``) or None if not found.
    """
    ep_root = book_dir / "_system" / "episode-drafts"
    if not ep_root.exists():
        return None
    for d in ep_root.iterdir():
        if d.is_dir() and d.name.endswith(f"-{chapter_slug}"):
            return d.name
    return None


def _rebuild_episode_txt(book_dir: Path, episode_id: str) -> bool:
    """Re-emit episodes/<episode_id>.txt from the current framing.

    Called after every invoke_fixer() pass so that episode.txt is never stale
    relative to the framing — which would cause the challenger to emit
    P0-EPISODE-STALE on the very next invocation, burning an outer iteration
    on a finding that is purely mechanical to fix.

    Returns True on success, False on any error (non-fatal: the convergence
    loop continues; the next challenger invocation may surface the staleness
    as a P0, which the fixer will handle in the following iteration).
    """
    try:
        result = subprocess.run(
            [sys.executable, str(_BUILD_EPISODE_TXT), str(book_dir), episode_id],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False


# ─── Verdict parsing ─────────────────────────────────────────────────────────

# Tolerant of two shapes the challenger LLM emits in real reports:
#   `**Verdict:** SHIP-READY`           ← canonical top-of-file form
#   `**Verdict: SHIP-WITH-CAUTION** —`  ← in-body per-iteration summary form
# Falling back to BLOCKED on unparseable verdicts (the prior behavior) is safe
# but expensive — convergence then exhausts the iteration cap re-running an
# already-passing chapter. This regex accepts either shape without falsely
# matching prose containing the word "verdict".
VERDICT_LINE_RE = re.compile(
    r"^\*\*Verdict:?\s*\*?\*?\s*:?\s*(SHIP-READY|SHIP-WITH-CAUTION|BLOCKED)",
    re.MULTILINE | re.IGNORECASE,
)
FINDING_COUNT_RE = re.compile(
    r"###\s+(P0|P1|P2)\b",
    re.MULTILINE,
)


def parse_challenger_report(report_path: Path) -> tuple[str, int, int, int]:
    """Read challenger-report.md and return (verdict, p0_count, p1_count, p2_count).

    Falls back to ("BLOCKED", 0, 0, 0) on a report whose Verdict line is missing
    so the convergence loop treats unparseable output as failure (safer than
    silently shipping).
    """
    if not report_path.exists():
        return "BLOCKED", 0, 0, 0
    text = report_path.read_text(encoding="utf-8")
    m = VERDICT_LINE_RE.search(text)
    verdict = m.group(1).upper() if m else "BLOCKED"

    # Count findings by counting `#### <ID>:` block markers under each severity
    # section. A more robust parser would walk the report's structure; this
    # uses the canonical Section 5 layout which keeps P0/P1/P2 in distinct
    # `### P0 (...)` / `### P1 (...)` / `### P2 (...)` blocks.
    severity_sections = re.split(r"^###\s+(P0|P1|P2)\b", text, flags=re.MULTILINE)
    # split returns [pre, "P0", body0, "P1", body1, "P2", body2] when all three exist
    counts = {"P0": 0, "P1": 0, "P2": 0}
    i = 1
    while i < len(severity_sections) - 1:
        sev = severity_sections[i]
        body = severity_sections[i + 1]
        # Stop at the next `## ` (which closes the findings section)
        body = body.split("\n## ", 1)[0]
        # Each finding starts with `#### <CHECK_ID>:` (per canonical spec Section 5).
        # CHECK_ID may carry hyphens (e.g., `A3-advisory`, `TX-MANGLE`).
        if "None." in body or "None\n" in body or body.strip() == "":
            counts[sev] = 0
        else:
            counts[sev] = len(re.findall(r"^####\s+[\w/.-]+:", body, re.MULTILINE))
        i += 2

    return verdict, counts["P0"], counts["P1"], counts["P2"]


# ─── Convergence loop ────────────────────────────────────────────────────────


def converge_chapter(book_dir: Path, chapter_slug: str) -> ChapterOutcome:
    """Drive the per-chapter convergence loop. Returns a ChapterOutcome.

    Pre-conditions:
    - `BOOK_DIR/chapters/ch##-<slug>.txt` exists (Phase 0d produced it)
    - `BOOK_DIR/_system/episode-drafts/EP##-<slug>/00-framing.md` exists
      (framing was authored before this is called)
    - `BOOK_DIR/episodes/EP##-<slug>.txt` exists (build_episode_txt.py emitted)

    Post-conditions:
    - `BOOK_DIR/_system/challenger-report.md` reflects the latest pass
    - findings emitted to `_learning/findings.jsonl` for every iteration
    - per-book `_system/health-trend.md` has one trend row per iteration
    """
    outcome = ChapterOutcome(
        chapter_slug=chapter_slug,
        final_verdict="FAILED",
        outer_iterations=0,
        fixer_attempts=0,
        p0_remaining=0,
        p1_remaining=0,
        p2_remaining=0,
    )
    report = book_dir / "_system" / "challenger-report.md"

    # Resolve the episode id once. Used to rebuild episode.txt after each
    # fixer pass so it stays in sync with the framing and never causes
    # P0-EPISODE-STALE on the following challenger invocation.
    episode_id = _find_episode_id(book_dir, chapter_slug)

    # F11 (2026-05-25): track best verdict seen across iterations. If a later
    # challenger pass times out / errors AFTER a prior iteration recorded a
    # ship-eligible verdict, fall back to that verdict rather than marking
    # the chapter FAILED (which loses the iter-1 ship signal even though
    # the episode artifact is intact on disk).
    best_verdict_so_far: str | None = None
    best_verdict_at_iter: int = 0
    for outer in range(1, MAX_OUTER_ITERATIONS + 1):
        outcome.outer_iterations = outer
        try:
            invoke_challenger(book_dir, chapter_slug)
        except AuthoringError as e:
            outcome.notes.append(f"iter {outer}: challenger invocation failed — {e}")
            # F11: if a prior iteration already established a ship-eligible
            # verdict at iter >= SHIP_WITH_CAUTION_MIN_ITER (2), preserve it.
            # SHIP-READY at any iter is also preserved. Only mark FAILED when
            # we have no prior ship signal to fall back on.
            if best_verdict_so_far == "SHIP-READY":
                outcome.final_verdict = "SHIP-READY"
                outcome.notes.append(
                    f"iter {outer}: preserved SHIP-READY from iter {best_verdict_at_iter} "
                    f"(later challenger timeout did not invalidate the prior ship signal)"
                )
                return outcome
            if (best_verdict_so_far == "SHIP-WITH-CAUTION"
                    and best_verdict_at_iter >= SHIP_WITH_CAUTION_MIN_ITER):
                outcome.final_verdict = "SHIP-WITH-CAUTION"
                outcome.notes.append(
                    f"iter {outer}: preserved SHIP-WITH-CAUTION from iter "
                    f"{best_verdict_at_iter} (later challenger timeout did not "
                    f"invalidate the prior ship signal)"
                )
                return outcome
            outcome.final_verdict = "FAILED"
            return outcome

        verdict, p0, p1, p2 = parse_challenger_report(report)
        outcome.p0_remaining = p0
        outcome.p1_remaining = p1
        outcome.p2_remaining = p2

        # Extract PEQ total from report for recording and gate enforcement.
        peq_m = re.search(
            r'\|\s*\*\*Total\*\*\s*\|\s*100%\s*\|\s*—\s*\|\s*\*\*(\d+(?:\.\d+)?)\*\*',
            report.read_text(encoding="utf-8") if report.exists() else "",
        )
        if peq_m:
            outcome.peq_total = float(peq_m.group(1))

        # K2: PEQ gate — enforce FAIL floor before any ship decision.
        # A chapter with peq_total < 70 is treated as BLOCKED regardless of
        # what the challenger verdict string says, so the fixer can act on
        # the enrichment / fidelity / structure gaps that drove the low score.
        if outcome.peq_total is not None and outcome.peq_total < 70.0:
            outcome.notes.append(
                f"iter {outer}: PEQ gate FAIL — total {outcome.peq_total:.1f} < 70; "
                f"overriding verdict {verdict!r} → BLOCKED"
            )
            verdict = "BLOCKED"
            p0 = p0 or 1  # ensure the fixer loop below is entered

        outcome.notes.append(
            f"iter {outer}: verdict={verdict} P0={p0} P1={p1} P2={p2}"
            + (f" PEQ={outcome.peq_total:.1f}" if outcome.peq_total is not None else "")
        )

        # F11: record the best verdict seen so far for timeout-fallback above.
        if verdict in ("SHIP-READY", "SHIP-WITH-CAUTION"):
            if best_verdict_so_far != "SHIP-READY":  # SHIP-READY dominates
                best_verdict_so_far = verdict
                best_verdict_at_iter = outer

        if verdict == "SHIP-READY":
            outcome.final_verdict = "SHIP-READY"
            return outcome

        if verdict == "SHIP-WITH-CAUTION":
            if outer >= SHIP_WITH_CAUTION_MIN_ITER:
                outcome.final_verdict = "SHIP-WITH-CAUTION"
                outcome.notes.append(
                    f"iter {outer}: SHIP-WITH-CAUTION accepted at iter ≥ {SHIP_WITH_CAUTION_MIN_ITER} threshold"
                )
                return outcome
            # iter < threshold: invoke fixer on P1 findings, retry
            outcome.notes.append(f"iter {outer}: fixer on P1 findings")
            try:
                invoke_fixer(book_dir, chapter_slug, severity="P1")
                outcome.fixer_attempts += 1
            except AuthoringError as e:
                outcome.notes.append(f"iter {outer}: fixer/P1 failed — {e}")
                # Don't abort the whole loop on a fixer failure — try another
                # outer iteration; the next challenger pass will surface the
                # same findings and we'll converge or hit the cap.
            # Rebuild episode.txt — fixer may have updated 00-framing.md.
            # Without this, the next challenger invocation flags P0-EPISODE-STALE.
            if episode_id:
                _rebuild_episode_txt(book_dir, episode_id)
            continue

        if verdict == "BLOCKED":
            # P0 findings present. Invoke fixer (max MAX_FIXER_ATTEMPTS_PER_P0).
            outcome.notes.append(f"iter {outer}: fixer on P0 findings (BLOCKED)")
            for attempt in range(1, MAX_FIXER_ATTEMPTS_PER_P0 + 1):
                try:
                    invoke_fixer(book_dir, chapter_slug, severity="P0")
                    outcome.fixer_attempts += 1
                except AuthoringError as e:
                    outcome.notes.append(
                        f"iter {outer}: fixer/P0 attempt {attempt} failed — {e}"
                    )
                    continue
                # After fixer, also clean up any P1s on the same attempt — cheap.
                try:
                    invoke_fixer(book_dir, chapter_slug, severity="P1")
                    outcome.fixer_attempts += 1
                except AuthoringError:
                    pass
                # Rebuild episode.txt — P0/P1 fixer may have updated 00-framing.md.
                # Without this, next challenger invocation sees stale episode.txt
                # and emits P0-EPISODE-STALE, burning the outer iteration cap.
                if episode_id:
                    _rebuild_episode_txt(book_dir, episode_id)
                break  # fixer attempt OK; let next outer iteration re-validate
            continue

        # Unknown verdict — fail loudly to avoid silent ships
        outcome.notes.append(
            f"iter {outer}: unknown verdict {verdict!r} — refusing to ship"
        )
        outcome.final_verdict = "FAILED"
        return outcome

    # Cap reached with unresolved findings — HALT, do not ship.
    # Prior behavior silently downgraded BLOCKED → FORCE-SHIP-CAUTION here,
    # which let chapters with unresolved P0 findings reach the audience.
    # Now: surface the failure to the orchestrator (which halts the per-chapter
    # loop at orchestrate_book.py:1267) and propagate the finding counts so
    # the user can decide whether to fix manually or relax a rule with intent.
    outcome.notes.append(
        f"iter {MAX_OUTER_ITERATIONS} cap reached with unresolved findings "
        f"(P0={outcome.p0_remaining} P1={outcome.p1_remaining}); HALT — "
        f"user review required, no silent ship."
    )
    outcome.final_verdict = "FAILED"
    return outcome


# ─── Render a per-chapter outcome line ───────────────────────────────────────


def render_outcome(outcome: ChapterOutcome) -> str:
    """Single-line render for orchestrator logs."""
    return (
        f"  {outcome.chapter_slug:<35} "
        f"{outcome.final_verdict:<22} "
        f"iter={outcome.outer_iterations} "
        f"fix={outcome.fixer_attempts} "
        f"P0={outcome.p0_remaining} P1={outcome.p1_remaining} P2={outcome.p2_remaining}"
    )
