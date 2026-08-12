#!/usr/bin/env python3
"""_dialogue_convergence.py — pre-synthesis convergence loop for dialogue scripts.

The dialogue analog of `_convergence.py` (audio chapters) and
`_slide_convergence.py` (decks). For each elevenlabs-book chapter:

    author script (Step 2) -> deterministic gate (Step 3) ->
    semantic challenger pass (claude -p, Max — faithfulness + coverage depth
    the deterministic gate cannot judge) -> fixer with findings -> re-gate ->
    loop until SHIP-READY, cautioned-ship at iter >= 2, or stall at the cap.

Verdict semantics (same gate as the audio convergence loop):

    SHIP-READY          deterministic P0=0 AND P1=0 AND semantic pass clean
    SHIP-WITH-CAUTION   deterministic P0=0, residual P1s, iter >= 2
    FAILED              P0s (or semantic BLOCKED) survive the iteration cap

NOTHING renders before a passing verdict: the renderer checks the verdict
file this module writes (`_system/dialogue-gate-reports/<EP>.verdict`).

Findings flow to `_learning/findings.jsonl` with source="dialogue-gate" so
the trainer learning loop compounds on this path too. Every gate report
carries the EXACT credit estimate (chars x registry rate) — the H1 spend
halt reads its number from here.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _authoring._core import AuthoringError, _run_claude_p, pure_text_call_options
from _authoring._dialogue import _episode_id_for_chapter, author_dialogue_script
from _dialogue_script import script_path_for
from _paths import REPO_ROOT
from _validators_dialogue import (
    DIALOGUE_GATE_VERSION,
    Finding,
    gate_dialogue_script,
    render_gate_report,
)

MAX_ITERATIONS = 5
SHIP_WITH_CAUTION_MIN_ITER = 2
SEMANTIC_TIMEOUT = 1200
FIXER_TIMEOUT = 900

_SEM_VERDICT_RE = re.compile(r"VERDICT:\s*(SHIP-READY|SHIP-WITH-CAUTION|BLOCKED)")
_SEM_FINDING_RE = re.compile(r"^-\s*\[(P0|P1|P2)\]\s*([A-Z0-9-]+):\s*(.+)$", re.MULTILINE)


@dataclass
class DialogueConvergenceResult:
    chapter_slug: str
    episode_id: str
    verdict: str  # SHIP-READY | SHIP-WITH-CAUTION | FAILED
    iterations: int = 0
    p0_remaining: int = 0
    p1_remaining: int = 0
    p2_remaining: int = 0
    credit_estimate: int = 0
    char_count: int = 0
    notes: list[str] = field(default_factory=list)


def _reports_dir(book_dir: Path) -> Path:
    return book_dir / "_system" / "dialogue-gate-reports"


def gate_report_path(book_dir: Path, episode_id: str) -> Path:
    return _reports_dir(book_dir) / f"{episode_id}.md"


def verdict_path(book_dir: Path, episode_id: str) -> Path:
    return _reports_dir(book_dir) / f"{episode_id}.verdict"


def read_verdict(book_dir: Path, episode_id: str) -> str | None:
    """The last converged verdict for an episode's script, or None."""
    p = verdict_path(book_dir, episode_id)
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8").strip() or None


def _emit_findings(book_dir: Path, episode_id: str, chapter_slug: str, findings: list[Finding]) -> None:
    """Append gate findings to the learning ledger (trainer substrate)."""
    try:
        from _rules import emit_finding

        for f in findings:
            emit_finding(
                repo_root=REPO_ROOT,
                source="dialogue-gate",
                source_version=DIALOGUE_GATE_VERSION,
                book=book_dir.name,
                episode=episode_id,
                chapter=chapter_slug,
                check_id=f.check_id,
                severity=f.severity,
                signature=f.message[:160],
                file=str(script_path_for(book_dir, episode_id)),
                context_excerpt=f.excerpt,
            )
    except Exception as e:
        print(f"  [dialogue-converge] WARN: findings ledger append failed: {e}", file=sys.stderr)


def _semantic_pass(
    book_dir: Path, episode_id: str, chapter_slug: str, timeout: int = SEMANTIC_TIMEOUT
) -> tuple[str, list[Finding]]:
    """LLM challenger pass (Max, $0 marginal) for what the deterministic gate

    cannot judge: faithfulness-against-addition (no invented doctrine),
    semantic coverage depth (a tension name-checked but not actually
    developed), and conversational quality. Returns (verdict, findings);
    an unparseable response maps to BLOCKED (safe refusal, mirrors
    _slide_convergence)."""
    script = script_path_for(book_dir, episode_id)
    chapter_files = sorted((book_dir / "chapters").glob(f"ch*-{chapter_slug}.txt"))
    chapter = chapter_files[0] if chapter_files else None
    contract = book_dir / "chapter-contracts" / f"{chapter_slug}.yml"
    prompt = (
        f"You are the dialogue-script challenger for episode `{episode_id}`.\n"
        f"Review the COMPLETE dialogue script at `{script}` against the source "
        f"chapter at `{chapter}` and the contract at `{contract}`.\n\n"
        f"Judge ONLY what a deterministic scanner cannot:\n"
        f"  1. FAITHFULNESS-AGAINST-ADDITION: every doctrinal claim, attribution, "
        f"quotation, and fact in the script must trace to the chapter. Invented "
        f"material is P0.\n"
        f"  2. COVERAGE DEPTH: each contract tension/concept must be genuinely "
        f"DEVELOPED in the conversation, not just name-checked. Undeveloped = P1.\n"
        f"  3. NO TEACHING LOST: a teaching present in the chapter but absent "
        f"from the script is P0.\n"
        f"  4. CONVERSATIONAL QUALITY: hosts in role (A scholar / B seeker), "
        f"genuine friction, no chorus agreement, open landing. Defects = P1.\n"
        f"  5. NOTEBOOKLM INTERACTIVE STYLE — each of these seven moves must be "
        f"GENUINELY present; a missing/weak move is a P1 (check id "
        f"DLG-SEM-STYLE-<MOVE>):\n"
        f"     (a) COLD-OPEN HOOK — opens on the chapter's question to the "
        f"listener, not a 'welcome' frame;\n"
        f"     (b) INTERRUPTION ECHOES — the seeker cuts in to echo a strange "
        f"term back as a question;\n"
        f"     (c) TWO PUSHBACK-AND-CONCEDE ARCS — the seeker objects with real "
        f"stakes, the scholar answers with the source's own analogy, the seeker "
        f"concedes explicitly (at least two such arcs);\n"
        f"     (d) SHORT REACTIVE BEATS — 1-5 word reactive turns at the peaks;\n"
        f"     (e) MID-THOUGHT HANDOFFS — one host occasionally completes the "
        f"other's sentence;\n"
        f"     (f) RECURRING REFRAIN — the spine line lands ~3 times "
        f"(open / pivot / close);\n"
        f"     (g) DIRECT-TO-LISTENER CLOSE — ends on the unresolved image / a "
        f"question to the listener, never a tidy summary.\n\n"
        f"OUTPUT FORMAT (exactly this, nothing else):\n"
        f"  VERDICT: SHIP-READY | SHIP-WITH-CAUTION | BLOCKED\n"
        f"  then zero or more findings, one per line:\n"
        f"  - [P0] DLG-SEM-<SHORT-ID>: <one-line finding>\n"
        f"  - [P1] DLG-SEM-<SHORT-ID>: <one-line finding>\n"
        f"Use BLOCKED only for P0-class problems. Do not modify any file."
    )
    try:
        rc, stdout, stderr = _run_claude_p(
            prompt,
            timeout=timeout,
            book_dir=book_dir,
            phase="audio-script",
            step=f"dialogue-challenger/{chapter_slug}",
            **pure_text_call_options(),
        )
    except AuthoringError as e:
        return "BLOCKED", [Finding("DLG-SEM-ERROR", "P1", f"semantic pass failed to run: {e}")]
    m = _SEM_VERDICT_RE.search(stdout or "")
    if not m:
        return "BLOCKED", [Finding("DLG-SEM-UNPARSEABLE", "P1", "semantic challenger output had no VERDICT line")]
    findings = [
        Finding(check_id=fm.group(2), severity=fm.group(1), message=fm.group(3).strip()[:300])
        for fm in _SEM_FINDING_RE.finditer(stdout)
    ]
    return m.group(1), findings


def _fixer_pass(
    book_dir: Path, episode_id: str, chapter_slug: str, findings: list[Finding], timeout: int = FIXER_TIMEOUT
) -> None:
    """One focused fixer pass: edit the script in place to resolve findings.

    CONTENT QUALITY FIRST: the fixer is explicitly forbidden from deleting
    teachings to silence a finding."""
    script = script_path_for(book_dir, episode_id)
    chapter_files = sorted((book_dir / "chapters").glob(f"ch*-{chapter_slug}.txt"))
    chapter = chapter_files[0] if chapter_files else "(missing)"
    listed = "\n".join(f"  - [{f.severity}] {f.check_id}: {f.message}" for f in findings if f.severity in ("P0", "P1"))
    prompt = (
        f"Fix the dialogue script at `{script}` IN PLACE to resolve these gate "
        f"findings:\n\n{listed}\n\n"
        f"RULES:\n"
        f"  - The source chapter is `{chapter}` — fix faithfulness findings by "
        f"correcting to the source, NEVER by inventing.\n"
        f"  - Fix coverage findings by ADDING the missing tension/concept "
        f"development (drawn from the chapter), never by trimming elsewhere.\n"
        f"  - NEVER delete a teaching, tension, or quotation to silence a "
        f"finding — content completeness outranks every band and count.\n"
        f"  - Keep the format: 'HOST_A: ...' / 'HOST_B: ...' turn lines, '#' "
        f"comments only, ASCII only, sparse [tag] cues.\n"
        f"  - Do not modify any other file.\n"
        f"Exit when the script is fixed."
    )
    _run_claude_p(
        prompt, timeout=timeout, book_dir=book_dir, phase="audio-script", step=f"dialogue-fixer/{chapter_slug}"
    )


def converge_dialogue_script(
    book_dir: Path,
    chapter_slug: str,
    *,
    max_iterations: int = MAX_ITERATIONS,
    semantic: bool = True,
    author_first: bool = True,
    log=print,
) -> DialogueConvergenceResult:
    """Drive one chapter's script to a shippable verdict. Writes the gate

    report + verdict file every iteration; emits findings to the ledger.

    semantic=False skips the LLM challenger pass (tests; deterministic-only
    smoke runs). author_first=False skips authorship when a script already
    exists (re-convergence after manual edits)."""
    episode_id, _chapter_file = _episode_id_for_chapter(book_dir, chapter_slug)
    script = script_path_for(book_dir, episode_id)

    if author_first and not script.exists():
        log(f"  [dialogue-converge] authoring script for {episode_id}")
        author_dialogue_script(book_dir, chapter_slug)

    result = DialogueConvergenceResult(chapter_slug=chapter_slug, episode_id=episode_id, verdict="FAILED")
    verdict_history: list[str] = []

    for iteration in range(1, max_iterations + 1):
        result.iterations = iteration
        report = gate_dialogue_script(book_dir, episode_id)
        sem_verdict, sem_findings = ("SHIP-READY", [])
        if semantic and report.p0 == 0:
            # Semantic pass only once the deterministic gate is P0-clean —
            # no point paying wall-clock for a script that already needs fixes.
            sem_verdict, sem_findings = _semantic_pass(book_dir, episode_id, chapter_slug)
            report.findings.extend(sem_findings)

        # Persist the gate report + emit findings to the learning ledger.
        rpt_path = gate_report_path(book_dir, episode_id)
        rpt_path.parent.mkdir(parents=True, exist_ok=True)
        rpt_path.write_text(render_gate_report(report), encoding="utf-8")
        _emit_findings(book_dir, episode_id, chapter_slug, report.findings)

        result.p0_remaining = report.p0
        result.p1_remaining = report.p1
        result.p2_remaining = report.p2
        result.credit_estimate = report.credit_estimate
        result.char_count = report.char_count

        blocked = report.p0 > 0 or sem_verdict == "BLOCKED"
        if not blocked and report.p1 == 0:
            result.verdict = "SHIP-READY"
            break
        if not blocked and iteration >= SHIP_WITH_CAUTION_MIN_ITER:
            result.verdict = "SHIP-WITH-CAUTION"
            result.notes.append(f"{report.p1} P1 finding(s) accepted at iteration {iteration}")
            break

        verdict_label = "BLOCKED" if blocked else "P1-ITERATE"
        verdict_history.append(
            verdict_label + ":" + ",".join(sorted(f.check_id for f in report.findings if f.severity in ("P0", "P1")))
        )
        if len(verdict_history) >= 2 and verdict_history[-1] == verdict_history[-2]:
            result.notes.append(
                "stall: identical findings across two iterations — not burning further passes (archetype-over-rerun)"
            )
            break
        if iteration == max_iterations:
            result.notes.append(f"iteration cap {max_iterations} reached")
            break

        log(f"  [dialogue-converge] iter {iteration}: P0={report.p0} P1={report.p1} -> fixer pass")
        actionable = [f for f in report.findings if f.severity in ("P0", "P1")]
        try:
            _fixer_pass(book_dir, episode_id, chapter_slug, actionable)
        except AuthoringError as e:
            # A fixer timeout/crash must never abort convergence: claude -p
            # frequently applies its edits and THEN hangs past the timeout
            # (observed live 2026-06-12 — both fixes were on disk when the
            # 900s timeout fired). The artifact on disk is the truth; loop
            # back and let the next gate judge it as it stands.
            result.notes.append(f"fixer error at iteration {iteration} (re-gating artifact as-is): {e}")
            log(f"  [dialogue-converge] fixer error — re-gating as-is: {e}")

    verdict_path(book_dir, episode_id).parent.mkdir(parents=True, exist_ok=True)
    verdict_path(book_dir, episode_id).write_text(result.verdict + "\n", encoding="utf-8")
    log(
        f"  [dialogue-converge] {episode_id}: {result.verdict} "
        f"(iter={result.iterations}, P0={result.p0_remaining}, "
        f"P1={result.p1_remaining}, est={result.credit_estimate:,} credits)"
    )
    return result
