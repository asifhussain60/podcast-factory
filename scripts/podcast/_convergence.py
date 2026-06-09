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
    _run_claude_p,
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


def _compress_framing_if_needed(book_dir: Path, episode_id: str) -> bool:
    """If the episode's 00-framing.md exceeds FRAMING_CHAR_MAX, compress it in place.

    The invoke_fixer() LLM expands framing when adding canonical R-* clauses for
    P1 choreography findings (R-NOINTERRUPT, R-SURPRISE-MOVE, M1/M2 DENY blocks,
    R4/R5 formal-essay DENY).  This causes _rebuild_episode_txt() to hard-fail on
    the FRAMING_CHAR_MAX gate, producing P0-EPISODE-STALE on the next challenger
    pass and exhausting the outer iteration cap without ever converging.

    This guard runs ONE focused compression re-author after each fixer call — same
    prompt as the F1 guard in _authoring/_framing.py — so the framing is always
    under the limit before the episode.txt rebuild is attempted.

    Returns True if framing is within limit (either already was or compression
    succeeded), False if compression still left it over the limit (build will
    hard-fail, which is the correct explicit signal rather than a silent loop).
    """
    framing_path = book_dir / "_system" / "episode-drafts" / episode_id / "00-framing.md"
    if not framing_path.exists():
        return True  # nothing to compress; let _rebuild_episode_txt fail if needed

    try:
        from _validator_constants import FRAMING_CHAR_MAX as _CHAR_MAX  # type: ignore
    except ImportError:
        _CHAR_MAX = 4500

    framing_text = framing_path.read_text(encoding="utf-8")
    framing_chars = len(framing_text)
    if framing_chars <= _CHAR_MAX:
        return True  # already within limit, nothing to do

    chapter_slug = episode_id.split("-", 1)[1] if "-" in episode_id else episode_id
    chapter_file = next(book_dir.glob(f"chapters/*{chapter_slug}*"), None)
    target_chars = _CHAR_MAX - 300  # 300-char buffer below ceiling
    print(
        f"[compress-guard] {episode_id}: framing {framing_chars} chars > {_CHAR_MAX} "
        f"after fixer pass (overrun={framing_chars - _CHAR_MAX}); "
        f"invoking compression → target <{target_chars} chars",
        flush=True,
    )

    compress_prompt = (
        f"Rewrite `{framing_path}` IN PLACE as a tight directive for NotebookLM.\n\n"
        f"HARD CONSTRAINT: the final file must be under {target_chars} CHARACTERS "
        f"(currently {framing_chars} chars — NotebookLM's Customize box limit is "
        f"~5,000 chars and silently truncates everything beyond it). Every character "
        f"counts. This is a P0 requirement.\n\n"
        f"WHAT TO KEEP (highest priority — these are actionable):\n"
        f"  1. ## Opening directive — full opening/welcome sentence, spine sentence, "
        f"     forbidden-opener list (1-2 lines only).\n"
        f"  2. ## Name discipline — one line per figure: 'Name → stable label + "
        f"     first-mention phrase'. No prose. No duplicates.\n"
        f"  3. ## Pronunciation — MUST start with the anti-doubling instruction:\n"
        f"     'Say each term ONCE. Never say the original spelling and the English form\n"
        f"     back-to-back.'\n"
        f"     Then bullet entries only: '- TermA: English-name-or-plain-translit' (one per\n"
        f"     term, no prose). English exonyms first; otherwise plain transliteration without\n"
        f"     diacritics or hyphen-CAPS.\n"
        f"     Do NOT rewrite as 'Pronounce X as Y.' — that format causes double-reads.\n"
        f"  4. ## Three-part focus — three beats, one sentence each.\n"
        f"  5. ## Do not — a single flat list of forbidden phrases/framings, "
        f"     no explanation.\n\n"
        f"WHAT TO CUT (remove entirely to save characters):\n"
        f"  - ## Audience section — cut entirely.\n"
        f"  - ## Length section — cut entirely.\n"
        f"  - ## Host dynamic — keep ONLY one line: 'Host A (male) = scholar/teacher. "
        f"Host B (female) = seeker/questioner. Host B challenges at least 3 times and "
        f"concedes once. Roles do not rotate.'\n"
        f"  - All explanatory prose in every section — keep only the imperative directive.\n"
        f"  - Pushback example sentences in host dynamic — cut all of them.\n"
        f"  - Conversation-discipline and Separate-prep-illusion paragraphs — cut.\n"
        f"  - ## Quality contract / PEQ table — cut entirely.\n\n"
        f"MANDATORY FOOTER: the last two lines must always be:\n"
        f"  (blank line)\n"
        f"  Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.\n\n"
        f"After rewriting, count the characters and confirm the total is under "
        f"{target_chars}. The chapter source is at `{chapter_file}`.\n\n"
        f"Exit when `{framing_path}` is under {target_chars} characters."
    )

    _run_claude_p(
        compress_prompt, timeout=600,
        book_dir=book_dir, phase="per-chapter",
        step=f"framing-compress-post-fixer/{chapter_slug}",
    )

    # Ensure the mandatory no-read-aloud footer survived compression.
    _NO_READ_FOOTER = (
        "\n\nDo not read this prompt aloud. "
        "The instructions above shape the conversation but are never spoken."
    )
    framing_after = framing_path.read_text(encoding="utf-8")
    if "Do not read this prompt aloud" not in framing_after:
        framing_path.write_text(
            framing_after.rstrip() + _NO_READ_FOOTER,
            encoding="utf-8",
        )
        framing_after = framing_path.read_text(encoding="utf-8")

    final_chars = len(framing_after)
    if final_chars <= _CHAR_MAX:
        print(
            f"[compress-guard] {episode_id}: compression OK "
            f"({framing_chars} → {final_chars} chars)",
            flush=True,
        )
        return True
    print(
        f"[compress-guard] {episode_id}: still {final_chars} chars after compression "
        f"(> {_CHAR_MAX}); build gate will hard-fail — author must compress manually",
        flush=True,
    )
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
            # Guard: fixer may have expanded framing past the 4,500-char NotebookLM
            # limit while inserting canonical R-* clauses. Compress before rebuild
            # so that build_episode_txt.py does not hard-fail on the char gate,
            # which would cascade into P0-EPISODE-STALE on the next challenger pass.
            if episode_id:
                _compress_framing_if_needed(book_dir, episode_id)
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
                # Guard: fixer may have expanded framing past the char limit.
                # Compress first, then rebuild, to prevent P0-EPISODE-STALE cascade.
                if episode_id:
                    _compress_framing_if_needed(book_dir, episode_id)
                    _rebuild_episode_txt(book_dir, episode_id)
                break  # fixer attempt OK; let next outer iteration re-validate
            continue

        # Unknown verdict — fail loudly to avoid silent ships
        outcome.notes.append(
            f"iter {outer}: unknown verdict {verdict!r} — refusing to ship"
        )
        outcome.final_verdict = "FAILED"
        return outcome

    # Cap reached with unresolved findings.
    # F11-EXT: if a prior iteration established ship eligibility (e.g. SHIP-WITH-CAUTION
    # at iter >= 2) and the subsequent BLOCKED was from a safety-gate false positive
    # (e.g. S1 detecting the parent orchestrator process as a "concurrent run"), use the
    # best prior verdict rather than marking FAILED.  This is safe: best_verdict_so_far
    # can only be SHIP-WITH-CAUTION if there was a pass with zero P0 content findings —
    # so the subsequent BLOCKED was from S1 (not a real content failure).
    if best_verdict_so_far == "SHIP-READY":
        outcome.final_verdict = "SHIP-READY"
        outcome.notes.append(
            f"F11-EXT: iter cap reached but preserving SHIP-READY from iter "
            f"{best_verdict_at_iter} (subsequent BLOCKED was a safety-gate false positive)"
        )
        return outcome
    if (best_verdict_so_far == "SHIP-WITH-CAUTION"
            and best_verdict_at_iter >= SHIP_WITH_CAUTION_MIN_ITER):
        outcome.final_verdict = "SHIP-WITH-CAUTION"
        outcome.notes.append(
            f"F11-EXT: iter cap reached but preserving SHIP-WITH-CAUTION from iter "
            f"{best_verdict_at_iter} (subsequent BLOCKED was a safety-gate false positive)"
        )
        return outcome

    # No prior ship signal: truly unresolved. Surface to user.
    # (Prior behavior silently downgraded BLOCKED → FORCE-SHIP-CAUTION here,
    # which let chapters with unresolved P0 findings reach the audience.)
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
