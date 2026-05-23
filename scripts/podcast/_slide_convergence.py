#!/usr/bin/env python3
"""_slide_convergence.py — per-chapter slide-deck convergence loop runner.

The slide-deck analogue of `_convergence.py`. For each chapter we:

    author deck pair → invoke Slide Deck Challenger → parse verdict →
    re-author with findings (if needed) → loop until SHIP-READY,
    cautioned-ship at iter ≥ 2, or stall at the iteration cap.

A density-gauge pre-flight short-circuits the loop when the chapter's
discussion spine carries `density = [VISUAL CANDIDATE] beats / total beats < 0.25`.
In that case we author a justified-skip note and run the Challenger ONLY
to verify Probe 7 (Justified Skip) accepts the justification.

Contract with `_slide_authoring` (parallel module):

    from _slide_authoring import author_deck_pair, AuthoringResult
    result = author_deck_pair(book_dir, slug, prior_findings=[...])
    # result.success: bool
    # result.deck_path: Path | None
    # result.framing_path: Path | None
    # result.validation_findings: list[dict]

Outputs (read by orchestrator + downstream tools):

    BOOK_DIR/slide-decks/chNN-deck-<slug>.txt        (the deck source)
    BOOK_DIR/slide-decks/chNN-framing-<slug>.md      (the customize prompt)
    BOOK_DIR/_system/slide-challenger-reports/chNN-report.md
    BOOK_DIR/_system/orchestrator-state.json         (updated per iteration)

Three layers of cap (matching audio):
    Inner (per Challenger invocation)  : Challenger's own internal limits
    Middle (this module — per chapter) : DEFAULT_MAX_ITERATIONS (5)
    Outer (per book)                   : orchestrate_book.py time / cost cap

Decision rule (per outer iteration of this module):

    SHIP-READY                               → break, return success
    SHIP-WITH-CAUTION, iter ≥ 2              → break, cautioned-ship
    SHIP-WITH-CAUTION, iter < 2              → re-author with findings, retry
    BLOCKED                                  → re-author with findings, retry
    iter == max_iterations still not green   → STALL
    two consecutive identical verdicts       → STALL (intelligent break)

Slide convergence is ISOLATED from audio: this module never touches
`chapters/chNN-<slug>.txt` or the episode `.txt`. Only the deck pair under
`slide-decks/` and the Challenger reports under `_system/`.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# _slide_authoring is being authored in parallel; import is deferred to
# call-sites so this module can be imported even before the sibling lands
# (orchestrator-side feature gating). The contract is documented in the
# module docstring above.

from _authoring import (  # noqa: E402
    AuthoringError,
    _run_claude_p,
)
from _progress import (  # noqa: E402
    read_state,
    write_state,
)

# Cost-ledger wiring (AU-S3-001 fix): every `claude -p` invocation in this
# module flows through `_authoring._run_claude_p(book_dir=...)`, which
# internally calls `_cost_ledger.append_from_claude_p_stdout` to append a
# per-call row to `<book_dir>/_system/cost-ledger.jsonl`. Calls below pass
# `phase="11b-slide-challenger"` (Challenger pass) or
# `phase="11b-slide-authoring"` (justified-skip note) so cost-ledger
# analysis can split slide-deck convergence spend from audio convergence,
# and so the orchestrator's `$50` cost cap (which sums `cost_usd` across
# all ledger rows in `orchestrate_book.py`'s `book_cost_usd()`) catches
# slide-deck overruns. Import made explicit so the regression-isolation
# grep finds `cost_ledger` here.
from _cost_ledger import append_from_claude_p_stdout  # noqa: E402,F401


# ─── Module-level constants ──────────────────────────────────────────────────

SCRIPT_VERSION = "1.0"
DEFAULT_MAX_ITERATIONS = 5  # smaller than audio's 15 — slide artifacts are smaller
DENSITY_THRESHOLD = 0.25
SHIP_WITH_CAUTION_MIN_ITER = 2
SLIDE_CHALLENGER_TIMEOUT = 1500  # 25 min per Challenger pass, matches audio


# ─── Result dataclass ────────────────────────────────────────────────────────


@dataclass
class ConvergenceResult:
    """The verdict-and-state of one chapter's slide-deck convergence pass."""

    verdict: str  # "SHIP-READY" | "SHIP-WITH-CAUTION" | "STALLED" | "SKIPPED" | "BLOCKED"
    iterations: int
    deck_path: Path | None = None
    framing_path: Path | None = None
    report_path: Path | None = None
    findings: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ─── Verdict / report parsing ────────────────────────────────────────────────

# The Slide Deck Challenger emits a report whose Overall section names the
# bundle status. Map "ship" → SHIP-READY, "iterate" → BLOCKED, plus an
# explicit SHIP-WITH-CAUTION line is honored when present.
_VERDICT_LINE_RE = re.compile(
    r"^\*\*(?:Verdict|Bundle status)\*\*:\s*"
    r"(SHIP-READY|SHIP-WITH-CAUTION|BLOCKED|ship|iterate)\b",
    re.IGNORECASE | re.MULTILINE,
)
_PROBE_FAIL_RE = re.compile(
    r"^\|\s*(\d+\s+[^|]+?)\s*\|\s*fail\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|",
    re.IGNORECASE | re.MULTILINE,
)
_ARCH_FAIL_RE = re.compile(
    r"^\|\s*(Visual Memory Test|Variety|Arc|Cross-Episode Consistency)\s*\|\s*fail\s*\|\s*([^|]*)\s*\|",
    re.IGNORECASE | re.MULTILINE,
)


def _parse_verdict(report_path: Path) -> tuple[str, list[dict]]:
    """Parse the Slide-Deck Challenger report.

    Returns (verdict, findings).

    Verdict is one of {"SHIP-READY", "SHIP-WITH-CAUTION", "BLOCKED"}.
    Falls back to "BLOCKED" with empty findings if the report is missing
    or unparseable — safer than silently shipping.

    Findings is a list of dicts:
        {"id": str, "severity": "fail", "slides": str, "notes": str, "scope": "probe"|"arch"}
    """
    if not report_path.exists():
        return "BLOCKED", []

    text = report_path.read_text(encoding="utf-8")

    # Verdict line
    m = _VERDICT_LINE_RE.search(text)
    if not m:
        verdict = "BLOCKED"
    else:
        raw = m.group(1).strip().upper()
        if raw == "SHIP":
            verdict = "SHIP-READY"
        elif raw == "ITERATE":
            verdict = "BLOCKED"
        elif raw in ("SHIP-READY", "SHIP-WITH-CAUTION", "BLOCKED"):
            verdict = raw
        else:
            verdict = "BLOCKED"

    findings: list[dict] = []
    for pm in _PROBE_FAIL_RE.finditer(text):
        findings.append({
            "id": pm.group(1).strip(),
            "severity": "fail",
            "slides": pm.group(2).strip(),
            "notes": pm.group(3).strip(),
            "scope": "probe",
        })
    for am in _ARCH_FAIL_RE.finditer(text):
        findings.append({
            "id": am.group(1).strip(),
            "severity": "fail",
            "slides": "",
            "notes": am.group(2).strip(),
            "scope": "arch",
        })

    return verdict, findings


def _intelligent_break(verdict_history: list[str]) -> bool:
    """Two consecutive identical non-success verdicts → stall.

    Mirrors `_convergence.py`'s intent: if the loop is not making progress
    (same verdict twice in a row) we stop burning tokens. SHIP-READY is
    never treated as a stall — the caller already broke on it.
    """
    if len(verdict_history) < 2:
        return False
    last, prev = verdict_history[-1], verdict_history[-2]
    if last == "SHIP-READY":
        return False
    return last == prev


# ─── Density gauge ───────────────────────────────────────────────────────────


def _chapter_num_from_slug(book_dir: Path, slug: str) -> str | None:
    """Resolve `chNN` from the audio chapter file. Returns 'ch07' or None."""
    for p in (book_dir / "chapters").glob(f"ch*-{slug}.txt"):
        m = re.match(r"^(ch\d{2}[a-z]?)-", p.name)
        if m:
            return m.group(1)
    return None


def _discussion_spine_path(book_dir: Path, slug: str) -> Path | None:
    """Locate `04-discussion-spine.md` under the episode-draft folder."""
    drafts_root = book_dir / "_system" / "episode-drafts"
    if not drafts_root.exists():
        return None
    for ep_dir in drafts_root.glob(f"EP*-{slug}"):
        spine = ep_dir / "04-discussion-spine.md"
        if spine.exists():
            return spine
    return None


def _compute_density(book_dir: Path, slug: str) -> float:
    """Compute density = [VISUAL CANDIDATE] beats / total beats.

    Reads `_system/episode-drafts/EP*-<slug>/04-discussion-spine.md` and
    counts beats. Returns 1.0 (high density, never skip) when the spine
    is missing — safer to authorize the full loop than to silently skip
    a chapter that genuinely needs a deck.
    """
    spine = _discussion_spine_path(book_dir, slug)
    if spine is None:
        return 1.0
    text = spine.read_text(encoding="utf-8")

    # Beat headers in the spine are typically H3 ("### Beat 1: …") OR
    # numbered list items ("1. **Beat title** …") — count both shapes,
    # de-duplicated by line index, to avoid double-counting either schema.
    total_beats = 0
    visual_beats = 0
    for line in text.splitlines():
        s = line.strip()
        is_beat = bool(re.match(r"^(?:###\s+|[-*]\s+|\d+\.\s+)", s))
        if not is_beat:
            continue
        total_beats += 1
        if "[VISUAL CANDIDATE]" in s.upper().replace(" ", " "):
            # tolerant match — uppercase folding handles "[Visual Candidate]"
            visual_beats += 1
        elif "[VISUAL CANDIDATE]" in line.upper():
            visual_beats += 1

    if total_beats == 0:
        return 1.0  # no parseable beats → assume needs a deck
    return visual_beats / total_beats


# ─── Slide-deck Challenger invocation ────────────────────────────────────────


def _invoke_slide_challenger(book_dir: Path, slug: str) -> Path:
    """Invoke the slide-deck-challenger agent. Returns the report path.

    Tries `subagent_type=slide-deck-challenger` first (canonical, if
    registered); falls back to `general-purpose` briefed with the
    canonical spec — mirroring the audio podcast-challenger pattern.

    Writes:
        BOOK_DIR/_system/slide-challenger-reports/chNN-report.md
    """
    book_slug = book_dir.name
    ch = _chapter_num_from_slug(book_dir, slug) or "ch00"
    reports_dir = book_dir / "_system" / "slide-challenger-reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{ch}-report.md"

    prompt = (
        f"Use the Agent tool with subagent_type=slide-deck-challenger to validate the "
        f"slide-deck bundle for chapter `{slug}` of book `{book_slug}`. The Challenger "
        f"reads its canonical spec from "
        f"`skills-staging/podcast/references/slide-deck-challenger.md` and validates the "
        f"deck pair at `{book_dir}/slide-decks/{ch}-deck-{slug}.txt` + "
        f"`{book_dir}/slide-decks/{ch}-framing-{slug}.md` against the audio chapter at "
        f"`{book_dir}/chapters/{ch}-{slug}.txt` and the discussion spine at "
        f"`{book_dir}/_system/episode-drafts/EP*-{slug}/04-discussion-spine.md`.\n\n"
        f"If subagent_type=slide-deck-challenger is not registered, fall back to "
        f"subagent_type=general-purpose and brief it with the canonical spec at "
        f"`skills-staging/podcast/references/slide-deck-challenger.md` — run BOTH the "
        f"Per-Slide Probes (Pass 1, probes 1–8) and the Architectural Pass (Pass 2, "
        f"checks 1–4), and emit the report in the schema documented in that spec.\n\n"
        f"Invocation argument: `{book_slug} --chapter {slug}`\n\n"
        f"Write the report to `{report_path}`. The report MUST contain a "
        f"`**Bundle status**:` line with one of `ship` / `iterate`, AND a "
        f"`**Verdict**:` line with one of `SHIP-READY` / `SHIP-WITH-CAUTION` / `BLOCKED`.\n\n"
        f"After the agent returns, exit immediately — do NOT take additional actions."
    )

    rc, stdout, stderr = _run_claude_p(
        prompt,
        timeout=SLIDE_CHALLENGER_TIMEOUT,
        book_dir=book_dir,
        phase="11b-slide-challenger",
        step=f"slide-challenger/{slug}",
    )
    if rc != 0:
        raise AuthoringError(
            phase=f"slide-challenger/{slug}",
            message=f"claude -p (slide-challenger) exited rc={rc}",
            manual_fallback=(
                "Invoke the slide-deck-challenger subagent manually on this chapter, "
                "then re-run slide convergence."
            ),
            stdout=stdout,
            stderr=stderr,
        )
    if not report_path.exists() or report_path.stat().st_size == 0:
        raise AuthoringError(
            phase=f"slide-challenger/{slug}",
            message=f"slide-challenger did not produce a non-empty report at {report_path}",
            manual_fallback="Re-run slide-deck-challenger via Agent tool manually.",
            stdout=stdout,
            stderr=stderr,
        )
    return report_path


# ─── Justified-skip flow ─────────────────────────────────────────────────────


def _author_justified_skip(book_dir: Path, slug: str, density: float) -> Path:
    """Author a justified-skip note for low-density chapters.

    The Challenger's Probe 7 verifies this before `slide-deck-status =
    not-needed` may be set. Returns the path to the justification file.
    """
    book_slug = book_dir.name
    ch = _chapter_num_from_slug(book_dir, slug) or "ch00"
    skip_dir = book_dir / "_system" / "slide-decks" / f"{ch}-{slug}"
    skip_dir.mkdir(parents=True, exist_ok=True)
    justification = skip_dir / "justified-skip.md"

    prompt = (
        f"You are authoring a justified-skip note for the slide-deck pipeline of "
        f"book `{book_slug}`, chapter `{slug}` ({ch}). The chapter's density gauge "
        f"computed `{density:.3f}` (threshold `{DENSITY_THRESHOLD}`), meaning fewer "
        f"than one in four discussion-spine beats are [VISUAL CANDIDATE].\n\n"
        f"INPUT (read these):\n"
        f"  - `{book_dir}/chapters/{ch}-{slug}.txt` (audio chapter)\n"
        f"  - `{book_dir}/_system/episode-drafts/EP*-{slug}/04-discussion-spine.md` "
        f"(beat-level structure)\n"
        f"  - `skills-staging/podcast/references/slide-deck-challenger.md` "
        f"(Probe 7 acceptance criteria)\n\n"
        f"OUTPUT: `{justification}`\n\n"
        f"The justification MUST name:\n"
        f"  (a) the source type from the affinity matrix;\n"
        f"  (b) which [VISUAL CANDIDATE] tags were considered (if any);\n"
        f"  (c) why none warranted a slide.\n\n"
        f"Generic justifications ('purely narrative', 'no visual content', "
        f"'doesn't fit') FAIL Probe 7. Cite specific source properties.\n\n"
        f"Exit when `{justification}` is non-empty."
    )
    rc, stdout, stderr = _run_claude_p(
        prompt,
        timeout=600,
        book_dir=book_dir,
        phase="11b-slide-authoring",
        step=f"slide-justified-skip/{slug}",
    )
    if rc != 0 or not justification.exists() or justification.stat().st_size == 0:
        raise AuthoringError(
            phase=f"slide-justified-skip/{slug}",
            message=f"justified-skip note not produced at {justification} (rc={rc})",
            manual_fallback=(
                "Author the justification manually per Probe 7 acceptance criteria, "
                "then re-run slide convergence."
            ),
            stdout=stdout,
            stderr=stderr,
        )
    return justification


# ─── Registry update (best-effort) ───────────────────────────────────────────


def _update_registry_status(book_dir: Path, slug: str, *,
                            slide_deck_status: str,
                            challenger_status: str) -> bool:
    """Best-effort update of slide-deck-status + challenger-status in the registry.

    Reads `BOOK_DIR/_system/registry.md`, finds the row whose slug column
    matches `slug`, and updates the `slide-deck-status` and
    `challenger-status` cells in place. Returns True on success, False on
    any miss (no registry, slug row not absent, columns not present). NEVER
    raises — registry shape is heterogeneous across books and a write-miss
    must not break convergence.
    """
    registry = book_dir / "_system" / "registry.md"
    if not registry.exists():
        return False
    try:
        text = registry.read_text(encoding="utf-8")
    except OSError:
        return False

    # Find the pipe-table header row that contains both columns of interest.
    lines = text.splitlines()
    header_idx = -1
    cols: list[str] = []
    for i, line in enumerate(lines):
        if "|" not in line:
            continue
        cells = [c.strip().lower() for c in line.split("|")]
        if "slide-deck-status" in cells and "challenger-status" in cells:
            header_idx = i
            cols = cells
            break
    if header_idx == -1:
        return False

    try:
        slug_col = cols.index("slug")
    except ValueError:
        # Fall back to the first column if no explicit "slug" header.
        slug_col = 1 if cols and cols[0] == "" else 0
    try:
        sds_col = cols.index("slide-deck-status")
        cs_col = cols.index("challenger-status")
    except ValueError:
        return False

    # Walk subsequent rows; skip the divider row (|---|---|...).
    changed = False
    for i in range(header_idx + 1, len(lines)):
        line = lines[i]
        if "|" not in line:
            continue
        if set(line.replace("|", "").strip()) <= {"-", " ", ":"}:
            continue
        cells = [c for c in line.split("|")]
        if len(cells) <= max(slug_col, sds_col, cs_col):
            continue
        if cells[slug_col].strip() != slug:
            continue
        cells[sds_col] = f" {slide_deck_status} "
        cells[cs_col] = f" {challenger_status} "
        lines[i] = "|".join(cells)
        changed = True
        break

    if not changed:
        return False
    try:
        registry.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


# ─── State updates ───────────────────────────────────────────────────────────


def _record_state(book_dir: Path, slug: str, *, phase_status: str,
                  iterations: int, verdict: str) -> None:
    """Stamp the slide-deck convergence outcome into orchestrator-state.json.

    Idempotent and resume-safe. Writes a per-chapter dict under
    `state['slide_decks'][slug]` with:
        slide_deck_phase: "running" | "done" | "stalled" | "skipped"
        slide_challenger_iter: int
        slide_challenger_verdict: str
    """
    state = read_state(book_dir) or {}
    sd = state.setdefault("slide_decks", {})
    sd[slug] = {
        "slide_deck_phase": phase_status,
        "slide_challenger_iter": iterations,
        "slide_challenger_verdict": verdict,
    }
    write_state(book_dir, state)


# ─── Public convergence loop ─────────────────────────────────────────────────


def run_slide_convergence(
    book_dir: Path,
    slug: str,
    *,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    enable_skip_flow: bool = True,
) -> ConvergenceResult:
    """Run the slide-deck convergence loop for one chapter.

    See module docstring for the full contract. Returns a `ConvergenceResult`
    with the verdict, iteration count, output paths, and parsed findings.

    Pre-conditions:
      - `BOOK_DIR/chapters/chNN-<slug>.txt` exists (audio chapter)
      - `BOOK_DIR/_system/episode-drafts/EP*-<slug>/04-discussion-spine.md` exists

    Post-conditions:
      - `BOOK_DIR/_system/slide-challenger-reports/chNN-report.md` reflects the last pass
      - `BOOK_DIR/_system/orchestrator-state.json` carries the per-chapter outcome
      - For SKIPPED: `BOOK_DIR/_system/slide-decks/chNN-<slug>/justified-skip.md` exists
      - Registry `slide-deck-status` + `challenger-status` columns updated (best-effort)
    """
    ch = _chapter_num_from_slug(book_dir, slug)
    if ch is None:
        raise AuthoringError(
            phase=f"slide-convergence/{slug}",
            message=f"no audio chapter file matches slug {slug!r} under {book_dir}/chapters/",
            manual_fallback=(
                "Run Phase 0d (chapter design) first; this loop requires "
                "`chapters/chNN-<slug>.txt` to derive the chapter number."
            ),
        )

    spine = _discussion_spine_path(book_dir, slug)
    if spine is None:
        raise AuthoringError(
            phase=f"slide-convergence/{slug}",
            message=f"no discussion-spine for slug {slug!r}",
            manual_fallback=(
                "Author the discussion spine (Phase 2 framing draft) before "
                "running slide convergence."
            ),
        )

    deck_path = book_dir / "slide-decks" / f"{ch}-deck-{slug}.txt"
    framing_path = book_dir / "slide-decks" / f"{ch}-framing-{slug}.md"
    report_path = book_dir / "_system" / "slide-challenger-reports" / f"{ch}-report.md"

    # ── Step 1: density gauge → optional justified-skip flow ────────────────
    density = _compute_density(book_dir, slug)
    if density < DENSITY_THRESHOLD and enable_skip_flow:
        outcome = ConvergenceResult(
            verdict="SKIPPED",
            iterations=0,
            deck_path=None,
            framing_path=None,
            report_path=report_path,
            findings=[],
            notes=[f"density={density:.3f} < {DENSITY_THRESHOLD} → justified-skip flow"],
        )
        _record_state(book_dir, slug, phase_status="skipped",
                      iterations=0, verdict="SKIPPED")
        try:
            justification = _author_justified_skip(book_dir, slug, density)
            outcome.notes.append(f"justified-skip authored at {justification}")
        except AuthoringError as e:
            outcome.notes.append(f"justified-skip authoring failed: {e}")
            outcome.verdict = "BLOCKED"
            _record_state(book_dir, slug, phase_status="stalled",
                          iterations=0, verdict="BLOCKED")
            return outcome

        # Probe-7-only Challenger pass.
        try:
            r_path = _invoke_slide_challenger(book_dir, slug)
            verdict, findings = _parse_verdict(r_path)
            outcome.findings = findings
            outcome.notes.append(
                f"Probe-7 verification: verdict={verdict} findings={len(findings)}"
            )
            if verdict == "SHIP-READY":
                _update_registry_status(book_dir, slug,
                                        slide_deck_status="not-needed",
                                        challenger_status="pass")
            else:
                # Justification rejected — escalate to a normal authoring loop
                # rather than silently shipping a bad skip.
                outcome.verdict = "BLOCKED"
                outcome.notes.append(
                    "Probe-7 rejected justification; SKIPPED escalated to BLOCKED"
                )
                _record_state(book_dir, slug, phase_status="stalled",
                              iterations=0, verdict="BLOCKED")
                return outcome
        except AuthoringError as e:
            outcome.notes.append(f"Probe-7 challenger invocation failed: {e}")
            outcome.verdict = "BLOCKED"
            _record_state(book_dir, slug, phase_status="stalled",
                          iterations=0, verdict="BLOCKED")
            return outcome

        return outcome

    # ── Step 2: convergence loop ────────────────────────────────────────────
    # Lazy import — _slide_authoring is authored in parallel; deferring keeps
    # this module importable in test contexts without the sibling.
    try:
        from _slide_authoring import author_deck_pair  # type: ignore
    except ImportError as e:
        raise AuthoringError(
            phase=f"slide-convergence/{slug}",
            message=f"_slide_authoring module not importable: {e}",
            manual_fallback=(
                "Author `_slide_authoring.py` (the parallel sibling) exposing "
                "`author_deck_pair(book_dir, slug, *, prior_findings=...) -> AuthoringResult`."
            ),
        ) from e

    outcome = ConvergenceResult(
        verdict="BLOCKED",
        iterations=0,
        deck_path=deck_path if deck_path.exists() else None,
        framing_path=framing_path if framing_path.exists() else None,
        report_path=report_path,
        findings=[],
        notes=[f"density={density:.3f} ≥ {DENSITY_THRESHOLD} → full loop"],
    )

    verdict_history: list[str] = []
    last_findings: list[dict] = []

    for outer in range(1, max_iterations + 1):
        outcome.iterations = outer
        _record_state(book_dir, slug, phase_status="running",
                      iterations=outer, verdict="(in-progress)")

        # 2a. (Re-)author the deck pair, passing prior findings as constraints.
        try:
            ar = author_deck_pair(book_dir, slug, prior_findings=last_findings)
        except TypeError:
            # Fallback if author_deck_pair's signature omits prior_findings.
            ar = author_deck_pair(book_dir, slug)  # type: ignore[misc]
        except AuthoringError as e:
            outcome.notes.append(f"iter {outer}: authoring failed — {e}")
            outcome.verdict = "BLOCKED"
            _record_state(book_dir, slug, phase_status="stalled",
                          iterations=outer, verdict="BLOCKED")
            return outcome

        if not getattr(ar, "success", False):
            outcome.notes.append(
                f"iter {outer}: authoring reported success=False; "
                f"validation_findings={len(getattr(ar, 'validation_findings', []) or [])}"
            )
            outcome.verdict = "BLOCKED"
            _record_state(book_dir, slug, phase_status="stalled",
                          iterations=outer, verdict="BLOCKED")
            return outcome

        outcome.deck_path = getattr(ar, "deck_path", deck_path)
        outcome.framing_path = getattr(ar, "framing_path", framing_path)

        # 2b. Invoke the Slide Deck Challenger.
        try:
            r_path = _invoke_slide_challenger(book_dir, slug)
        except AuthoringError as e:
            outcome.notes.append(f"iter {outer}: challenger invocation failed — {e}")
            outcome.verdict = "BLOCKED"
            _record_state(book_dir, slug, phase_status="stalled",
                          iterations=outer, verdict="BLOCKED")
            return outcome
        outcome.report_path = r_path

        # 2c. Parse the verdict.
        verdict, findings = _parse_verdict(r_path)
        verdict_history.append(verdict)
        last_findings = findings
        outcome.findings = findings
        outcome.notes.append(
            f"iter {outer}: verdict={verdict} findings={len(findings)}"
        )

        # 2d. Decision rule.
        if verdict == "SHIP-READY":
            outcome.verdict = "SHIP-READY"
            _record_state(book_dir, slug, phase_status="done",
                          iterations=outer, verdict="SHIP-READY")
            _update_registry_status(book_dir, slug,
                                    slide_deck_status="ready",
                                    challenger_status="pass")
            return outcome

        if verdict == "SHIP-WITH-CAUTION" and outer >= SHIP_WITH_CAUTION_MIN_ITER:
            outcome.verdict = "SHIP-WITH-CAUTION"
            outcome.notes.append(
                f"iter {outer}: SHIP-WITH-CAUTION accepted at iter ≥ "
                f"{SHIP_WITH_CAUTION_MIN_ITER}"
            )
            _record_state(book_dir, slug, phase_status="done",
                          iterations=outer, verdict="SHIP-WITH-CAUTION")
            _update_registry_status(book_dir, slug,
                                    slide_deck_status="ready",
                                    challenger_status="fail-iterating")
            return outcome

        # Intelligent break: two consecutive identical non-success verdicts.
        if _intelligent_break(verdict_history):
            outcome.notes.append(
                f"iter {outer}: intelligent break — verdict {verdict} "
                f"repeated; stalling"
            )
            outcome.verdict = "STALLED"
            _record_state(book_dir, slug, phase_status="stalled",
                          iterations=outer, verdict="STALLED")
            _update_registry_status(book_dir, slug,
                                    slide_deck_status="pending",
                                    challenger_status="fail-iterating")
            return outcome

        # Otherwise loop: next iteration re-authors with `findings` as constraints.
        continue

    # 2e. Cap reached without convergence.
    outcome.iterations = max_iterations
    outcome.verdict = "STALLED"
    outcome.notes.append(
        f"iter cap reached ({max_iterations}); slide-deck did not converge"
    )
    _record_state(book_dir, slug, phase_status="stalled",
                  iterations=max_iterations, verdict="STALLED")
    _update_registry_status(book_dir, slug,
                            slide_deck_status="pending",
                            challenger_status="fail-iterating")
    return outcome
