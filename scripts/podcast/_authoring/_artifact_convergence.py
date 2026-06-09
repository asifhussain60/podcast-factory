"""_authoring/_artifact_convergence.py — bounded discriminator/fixer loop for
single upstream authoring artifacts (Phases 0b, 0e).

Shift-left companion to ``_convergence.converge_chapter``. That loop validates a
*finished chapter* (semantic challenger + deterministic PEQ) at the per-chapter
stage; this helper validates the **upstream artifacts those chapters are built
from** — 0b's ``refined-english.md`` and 0e's enriched chapter files — at the
point of generation, so a defect is caught once, before it is multiplied across
every downstream chapter and re-paid per chapter by the challenger.

Design contract (locked by the approved Wave-N adversarial-validation plan):

  * **Deterministic pre-check runs first and FREE.** The optional LLM
    discriminator fires only when a per-phase cost cap is configured (> 0). Caps
    default to 0.0 in ``series-plan.md``, so existing books run byte-identically
    with zero new LLM calls until a book opts in.

  * **FLAG-AND-PROCEED, never hard-FAIL.** On non-convergence the helper records
    findings (to ``_learning/findings.jsonl`` + the caller's brief) and returns;
    it NEVER raises and NEVER blocks the phase. Unlike ``converge_chapter`` (which
    can return FAILED and halt the book), this loop is strictly *additive* — it
    can only improve an artifact, never stop a good book. The downstream
    per-chapter challenger, the PEQ gate, and the human 06a/0ci review gates
    remain the real safety net.

  * **Bounded.** ``MAX_ARTIFACT_ROUNDS`` rounds; a per-call cost-ceiling check
    mirrors the F35 mid-loop rail in ``converge_chapter`` (checked BEFORE the
    expensive call so a runaway is stopped at the round boundary).

Phase A wires only the deterministic pre-check path (``discriminator_fn=None``,
``fixer_fn=None``) into 0b/0e — no autonomous LLM spend. Phases B/C supply the
frozen-prompt discriminator + fixer callbacks and a non-zero cap.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _paths import REPO_ROOT  # noqa: E402

ARTIFACT_CONVERGENCE_VERSION = "1.0"

# Upstream artifacts are cheaper to fix than a finished chapter and the human
# 06a/0ci gates backstop them, so the round cap is one less than the per-chapter
# loop's MAX_OUTER_ITERATIONS (3).
MAX_ARTIFACT_ROUNDS = 2

# ─── Deterministic pre-check thresholds ──────────────────────────────────────
# Conservative bands chosen to minimise false positives — a precheck finding is
# surfaced to a human gate, so a noisy check costs human attention. Tune here.

# 0b: refined-english.md word count relative to its raw-extract.md input. A
# faithful refinement cleans and lightly compresses; a ratio outside this band
# signals a wholesale drop (too low) or a hallucinated expansion (too high).
PRECHECK_0B_LENGTH_RATIO_MIN = 0.40
PRECHECK_0B_LENGTH_RATIO_MAX = 1.60
# 0b: refined paragraph count below this fraction of raw paragraphs (when raw
# has at least this many) signals a structural collapse / merged-everything bug.
PRECHECK_0B_PARA_COLLAPSE_FRACTION = 0.50
PRECHECK_0B_PARA_MIN_RAW = 4

# 0e: enrichment ADDS citations/context in place, so after >= before is expected.
# after < before words means source content was dropped during enrichment.
# after/before above the balloon ratio means enrichment buried the source.
PRECHECK_0E_BALLOON_RATIO = 2.50


# ─── Result types ────────────────────────────────────────────────────────────


@dataclass
class ArtifactFinding:
    """One defect found in an upstream artifact. Mirrors the subset of the
    ``emit_finding`` record shape this layer populates."""
    check_id: str
    severity: str          # "P0" | "P1" | "P2"
    signature: str
    message: str
    file: str = ""
    context_excerpt: str = ""


@dataclass
class ArtifactOutcome:
    """The result of one ``converge_artifact`` pass. ``proceeded`` is ALWAYS True
    — this loop never blocks a phase — and is kept explicit so callers (and the
    regression tests) can assert the flag-and-proceed contract directly."""
    label: str
    converged: bool                 # True iff the final round surfaced no findings
    rounds: int
    discriminator_calls: int
    fixer_calls: int
    findings: list[ArtifactFinding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Set when the per-book cost ceiling tripped mid-loop. Distinct from
    # converge_chapter's `systemic_halt`: here it does NOT halt the book — it
    # only disables the LLM discriminator and proceeds on deterministic findings.
    cost_ceiling_tripped: str | None = None
    proceeded: bool = True


# ─── Deterministic pre-checks (pure — no I/O, fully unit-testable) ────────────


def _word_count(text: str) -> int:
    return len(text.split())


def _paragraph_count(text: str) -> int:
    """Blank-line-delimited paragraph count, ignoring empty runs."""
    return len([p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()])


def precheck_refined_english(raw_text: str, refined_text: str,
                             *, file: str = "") -> list[ArtifactFinding]:
    """Deterministic pre-checks for the 0b output (refined-english.md).

    Catches the failure modes a downstream LLM challenger would otherwise catch
    late and expensively: an empty/near-empty refinement, a wholesale
    drop-or-balloon in length, and a structural paragraph collapse. Pure: takes
    the raw input text and the refined output text, returns findings.
    """
    findings: list[ArtifactFinding] = []
    refined_words = _word_count(refined_text)
    raw_words = _word_count(raw_text)

    if refined_words == 0:
        findings.append(ArtifactFinding(
            check_id="U0B-EMPTY", severity="P0",
            signature="U0B-EMPTY",
            message="refined-english.md is empty after 0b refinement.",
            file=file,
        ))
        return findings  # nothing else is meaningful on an empty artifact

    if raw_words > 0:
        ratio = refined_words / raw_words
        if ratio < PRECHECK_0B_LENGTH_RATIO_MIN or ratio > PRECHECK_0B_LENGTH_RATIO_MAX:
            findings.append(ArtifactFinding(
                check_id="U0B-LENGTH-DRIFT", severity="P1",
                signature="U0B-LENGTH-DRIFT",
                message=(
                    f"refined/raw word ratio {ratio:.2f} outside band "
                    f"[{PRECHECK_0B_LENGTH_RATIO_MIN}, {PRECHECK_0B_LENGTH_RATIO_MAX}] "
                    f"(refined={refined_words}, raw={raw_words}) — possible wholesale "
                    f"drop or hallucinated expansion."
                ),
                file=file,
                context_excerpt=f"refined={refined_words} raw={raw_words} ratio={ratio:.2f}",
            ))

    raw_paras = _paragraph_count(raw_text)
    refined_paras = _paragraph_count(refined_text)
    if (raw_paras >= PRECHECK_0B_PARA_MIN_RAW
            and refined_paras < raw_paras * PRECHECK_0B_PARA_COLLAPSE_FRACTION):
        findings.append(ArtifactFinding(
            check_id="U0B-STRUCTURE-COLLAPSE", severity="P1",
            signature="U0B-STRUCTURE-COLLAPSE",
            message=(
                f"refined paragraph count {refined_paras} collapsed below "
                f"{PRECHECK_0B_PARA_COLLAPSE_FRACTION:.0%} of raw {raw_paras} — "
                f"paragraphs may have been merged into a wall of text."
            ),
            file=file,
            context_excerpt=f"refined_paras={refined_paras} raw_paras={raw_paras}",
        ))

    return findings


def precheck_enriched_chapter(before_text: str, after_text: str,
                              *, file: str = "") -> list[ArtifactFinding]:
    """Deterministic pre-checks for one 0e enriched chapter (in-place rewrite).

    Enrichment adds citations/context, so the enriched text should grow, not
    shrink. ``before_text`` is the pre-enrichment chapter, ``after_text`` the
    enriched result. Pure.
    """
    findings: list[ArtifactFinding] = []
    before_words = _word_count(before_text)
    after_words = _word_count(after_text)

    if before_words == 0:
        return findings  # nothing to compare against

    if after_words < before_words:
        findings.append(ArtifactFinding(
            check_id="U0E-SHRANK", severity="P1",
            signature="U0E-SHRANK",
            message=(
                f"enriched chapter shrank ({after_words} < {before_words} words) — "
                f"enrichment should add citations/context, not remove source content."
            ),
            file=file,
            context_excerpt=f"before={before_words} after={after_words}",
        ))
    elif after_words / before_words > PRECHECK_0E_BALLOON_RATIO:
        findings.append(ArtifactFinding(
            check_id="U0E-BALLOON", severity="P1",
            signature="U0E-BALLOON",
            message=(
                f"enriched/source word ratio {after_words / before_words:.2f} exceeds "
                f"{PRECHECK_0E_BALLOON_RATIO} — enrichment may be burying the source."
            ),
            file=file,
            context_excerpt=f"before={before_words} after={after_words}",
        ))

    return findings


# ─── Findings ledger emission ────────────────────────────────────────────────


def _emit_findings(findings: list[ArtifactFinding], *, book_slug: str,
                   source: str) -> None:
    """Append findings to the repo-level _learning/findings.jsonl ledger so the
    trainer (Phase D) can cluster recurring upstream defects. Best-effort: a
    ledger failure must never break the authoring phase."""
    if not findings:
        return
    try:
        from _rules import emit_finding
    except Exception:  # noqa: BLE001
        return
    for f in findings:
        try:
            emit_finding(
                repo_root=REPO_ROOT,
                source=source,
                source_version=ARTIFACT_CONVERGENCE_VERSION,
                book=book_slug,
                check_id=f.check_id,
                severity=f.severity,
                signature=f.signature,
                file=f.file,
                context_excerpt=f.context_excerpt or f.message,
            )
        except Exception:  # noqa: BLE001
            continue


def write_precheck_brief(book_dir: Path, label: str,
                         findings: list[ArtifactFinding]) -> Path:
    """Write a short markdown brief the human 06a/0ci review gate will see.

    Appends (does not overwrite) so 0b and 0e briefs accumulate in one place.
    Returns the brief path. A clean pass writes an explicit 'no findings' row so
    the reviewer can tell the check ran.
    """
    brief = book_dir / "_system" / "upstream-precheck-report.md"
    brief.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if not brief.exists():
        lines.append("# Upstream pre-check report\n")
        lines.append(
            "Deterministic shift-left checks on 0b/0e artifacts "
            "(flag-and-proceed — these never block the pipeline). "
            "Review before approving the 06a source-review gate.\n"
        )
    lines.append(f"\n## {label}\n")
    if not findings:
        lines.append("- ✅ no deterministic findings\n")
    else:
        for f in findings:
            lines.append(f"- **{f.severity} {f.check_id}** — {f.message}\n")
    with brief.open("a", encoding="utf-8") as fh:
        fh.write("".join(lines))
    return brief


# ─── Bounded convergence loop ────────────────────────────────────────────────


def converge_artifact(
    *,
    label: str,
    book_dir: Path,
    precheck_fn: Callable[[], list[ArtifactFinding]],
    discriminator_fn: Optional[Callable[[], list[ArtifactFinding]]] = None,
    fixer_fn: Optional[Callable[[list[ArtifactFinding]], None]] = None,
    cost_cap_usd: float = 0.0,
    cost_fn: Optional[Callable[[], float]] = None,
    heartbeat: Optional[Callable[[int, str], None]] = None,
    max_rounds: int = MAX_ARTIFACT_ROUNDS,
    log=print,
) -> ArtifactOutcome:
    """Drive a bounded, flag-and-proceed validation loop over one upstream artifact.

    ``precheck_fn`` (REQUIRED) runs every round, is free, and is the only check
    used when no discriminator/cap is configured (Phase A). The optional
    ``discriminator_fn`` (an LLM scorer) fires ONLY when ``cost_cap_usd > 0`` —
    so a book that has not opted in pays exactly zero. ``fixer_fn`` (also LLM)
    is invoked on the combined findings between rounds when present and enabled.

    Cost ceiling: when ``cost_fn`` and ``cost_cap_usd > 0`` are supplied, the
    per-book spend is checked at the TOP of each round (before any LLM call). A
    breach records ``systemic_halt`` and proceeds — it never raises.

    The loop NEVER raises and ALWAYS returns with ``proceeded=True``. Findings
    from the final round are emitted to the ledger + brief by the caller-facing
    wrappers (``run_*_precheck``), not here, so emission happens once.
    """
    outcome = ArtifactOutcome(
        label=label, converged=False, rounds=0,
        discriminator_calls=0, fixer_calls=0,
    )
    llm_enabled = cost_cap_usd > 0 and discriminator_fn is not None

    for rnd in range(1, max_rounds + 1):
        outcome.rounds = rnd

        if heartbeat is not None:
            try:
                heartbeat(rnd, "artifact-converge")
            except Exception:  # noqa: BLE001
                pass  # a beat failure must never break the loop

        # F35-style mid-loop cost ceiling — checked BEFORE any LLM call so a
        # runaway is stopped at the round boundary. Only meaningful once the LLM
        # path is enabled (deterministic prechecks are free).
        if llm_enabled and cost_fn is not None:
            spent = cost_fn()
            if spent > cost_cap_usd:
                msg = (f"COST-CEILING: book spent ${spent:.2f} > cap "
                       f"${cost_cap_usd:.2f} at round {rnd} — disabling LLM "
                       f"discriminator, proceeding on deterministic findings only.")
                outcome.notes.append(msg)
                outcome.cost_ceiling_tripped = msg
                llm_enabled = False

        findings = list(precheck_fn())

        if llm_enabled and discriminator_fn is not None:
            try:
                findings.extend(discriminator_fn() or [])
                outcome.discriminator_calls += 1
            except Exception as e:  # noqa: BLE001
                # A discriminator failure degrades to deterministic-only — never
                # fatal (flag-and-proceed). Record and carry on.
                outcome.notes.append(f"round {rnd}: discriminator failed — {e!r}")

        outcome.findings = findings
        outcome.notes.append(
            f"round {rnd}: {len(findings)} finding(s) "
            f"[{', '.join(f.check_id for f in findings) or 'none'}]"
        )

        if not findings:
            outcome.converged = True
            return outcome

        # Findings remain. With no enabled fixer (Phase A, or LLM disabled) we
        # cannot auto-repair — surface and proceed (the human gate / downstream
        # challenger handles it). With a fixer, attempt repair and re-validate.
        if not (llm_enabled and fixer_fn is not None):
            outcome.notes.append(
                f"round {rnd}: no enabled fixer — flag-and-proceed "
                f"({len(findings)} finding(s) surfaced to human gate)"
            )
            return outcome

        try:
            fixer_fn(findings)
            outcome.fixer_calls += 1
        except Exception as e:  # noqa: BLE001
            outcome.notes.append(
                f"round {rnd}: fixer failed — {e!r}; flag-and-proceed")
            return outcome

    # Round cap reached with findings still open — flag-and-proceed.
    outcome.notes.append(
        f"round cap {max_rounds} reached with {len(outcome.findings)} open "
        f"finding(s) — flag-and-proceed (no hard fail upstream)."
    )
    return outcome


# ─── Phase-specific precheck wrappers (Phase A entry points) ──────────────────


def run_0b_precheck(book_dir: Path, *, log=print) -> ArtifactOutcome:
    """Phase A: deterministic-only validation of 0b's refined-english.md.

    Reads the raw input + refined output, runs the bounded loop with no LLM,
    emits findings to the ledger + writes the human-gate brief, and returns the
    outcome. NEVER raises — a precheck failure must not break Phase 0b.
    """
    raw_path = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    refined_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    rel = str(refined_path)
    _clean = ArtifactOutcome(label="0b:refined-english.md", converged=True,
                             rounds=0, discriminator_calls=0, fixer_calls=0)
    # The wrapper is an advisory safety net invoked AFTER 0b has already
    # hard-asserted a non-empty refined-english.md. If the refined artifact is
    # absent or empty here, the phase's own assertion is the authority — skip
    # rather than emit a spurious U0B-EMPTY (a false positive on missing input).
    if not refined_path.exists() or refined_path.stat().st_size == 0:
        log("  phase 0b · precheck skipped (no refined artifact to check)")
        return _clean
    try:
        raw_text = raw_path.read_text(encoding="utf-8") if raw_path.exists() else ""
        refined_text = refined_path.read_text(encoding="utf-8")
    except OSError as e:
        log(f"  phase 0b · precheck skipped (read error: {e})")
        return _clean

    outcome = converge_artifact(
        label="0b:refined-english.md",
        book_dir=book_dir,
        precheck_fn=lambda: precheck_refined_english(raw_text, refined_text, file=rel),
        log=log,
    )
    _emit_findings(outcome.findings, book_slug=book_dir.name, source="precheck-0b")
    write_precheck_brief(book_dir, outcome.label, outcome.findings)
    if outcome.findings:
        log(f"  phase 0b · precheck flagged {len(outcome.findings)} finding(s) "
            f"(flag-and-proceed): {', '.join(f.check_id for f in outcome.findings)}")
    else:
        log("  phase 0b · precheck clean")
    return outcome


def run_0e_chapter_precheck(book_dir: Path, chapter_stem: str,
                            before_text: str, after_text: str,
                            *, file: str = "", log=print) -> ArtifactOutcome:
    """Phase A: deterministic-only validation of one 0e enriched chapter.

    Called per chapter from ``author_phase_0e`` with the pre-enrichment text
    captured before the LLM rewrite. NEVER raises.
    """
    label = f"0e:{chapter_stem}"
    outcome = converge_artifact(
        label=label,
        book_dir=book_dir,
        precheck_fn=lambda: precheck_enriched_chapter(before_text, after_text, file=file),
        log=log,
    )
    _emit_findings(outcome.findings, book_slug=book_dir.name, source="precheck-0e")
    write_precheck_brief(book_dir, label, outcome.findings)
    if outcome.findings:
        log(f"    {chapter_stem} · precheck flagged "
            f"{', '.join(f.check_id for f in outcome.findings)} (flag-and-proceed)")
    return outcome
