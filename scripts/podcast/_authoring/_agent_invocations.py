"""_authoring/_agent_invocations.py — Challenger, fixer, and trainer invocations.

Extracted from _authoring.py (A4 split). Renamed from _authoring/_convergence.py
(R3, 2026-07-18) to remove the basename collision with the per-chapter
convergence-loop module scripts/podcast/_convergence.py — this module holds the
`claude -p` shellouts that INVOKE the challenger/fixer/trainer agents; the loop
that drives them lives in _convergence.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ._core import (
    CHALLENGER_TIMEOUT,
    FIXER_TIMEOUT,
    TRAINER_TIMEOUT,
    AuthoringError,
    _run_claude_p,
)


def invoke_challenger(book_dir: Path, chapter_slug: str, timeout: int = CHALLENGER_TIMEOUT) -> str:
    """Invoke the podcast-challenger subagent on one chapter."""
    book_slug = book_dir.name
    prompt = (
        f"Use the Agent tool with subagent_type=podcast-challenger to validate the "
        f"chapter `{chapter_slug}` of book `{book_slug}`. The challenger reads its "
        f"canonical spec from `.github/agents/podcast-challenger.agent.md`, runs the "
        f"convergence loop (max 5 internal iterations per invocation), writes "
        f"`{book_dir}/_system/challenger-report.md`, emits findings into "
        f"`_learning/findings.jsonl`, and writes the health JSON.\n\n"
        f"Invocation argument: `{book_slug} --chapter {chapter_slug}`\n\n"
        f"PIPELINE CONTEXT (mandatory for the challenger agent to read before any "
        f"pre-check): This invocation originates from WITHIN the orchestrator pipeline "
        f"(`orchestrate_book.py`). Any `orchestrate_book.py` process visible via pgrep "
        f"is THIS pipeline's parent process — it spawned this challenger call and is "
        f"waiting for it. This is NOT a concurrent independent run. The Category S1 "
        f"(async-safety) gate MUST NOT fire for the parent orchestrator process. Bypass "
        f"S1 for this invocation and proceed with the full per-chapter challenger sweep.\n\n"
        f"After the agent returns, exit immediately — do NOT take additional actions."
    )
    rc, stdout, stderr = _run_claude_p(
        prompt,
        timeout=timeout,
        book_dir=book_dir,
        phase="per-chapter",
        step=f"challenger/{chapter_slug}",
    )
    report = book_dir / "_system" / "challenger-report.md"
    if rc != 0:
        raise AuthoringError(
            phase=f"challenger/{chapter_slug}",
            message=f"claude -p (challenger) exited rc={rc}",
            manual_fallback=(
                "Invoke the podcast-challenger subagent manually on this chapter, "
                "then re-invoke orchestrate-book --resume."
            ),
            stdout=stdout,
            stderr=stderr,
        )
    if not report.exists() or report.stat().st_size == 0:
        raise AuthoringError(
            phase=f"challenger/{chapter_slug}",
            message=f"challenger did not produce a non-empty report at {report}",
            manual_fallback="Re-run challenger via Agent tool manually.",
            stdout=stdout,
            stderr=stderr,
        )
    return stdout


def invoke_fixer(book_dir: Path, chapter_slug: str, severity: str, timeout: int = FIXER_TIMEOUT) -> str:
    """Invoke the conversational `/podcast` skill to fix open findings."""
    book_slug = book_dir.name
    report = book_dir / "_system" / "challenger-report.md"
    if not report.exists():
        raise AuthoringError(
            phase=f"fixer/{chapter_slug}",
            message=f"no challenger-report.md at {report} — nothing to fix",
            manual_fallback="Run the challenger first.",
        )

    prompt = (
        f"You are the orchestrator's fixer pass for book `{book_slug}`, chapter "
        f"`{chapter_slug}`. Read `{report}` and address every **{severity}** finding "
        f"in the order listed. For each, follow the **Suggested fix** line in the "
        f"report.\n\n"
        f"Allowed edits (only these):\n"
        f"  - `{book_dir}/chapters/ch*-{chapter_slug}.txt`\n"
        f"  - `{book_dir}/_system/episode-drafts/EP*-{chapter_slug}/00-framing.md`\n\n"
        f"After every framing edit, run `python3 scripts/podcast/build_episode_txt.py "
        f"{book_dir} EP##-{chapter_slug}` to re-emit the episode `.txt`.\n\n"
        f"FRAMING CHARACTER LIMIT (P0 hard gate): the `00-framing.md` file MUST stay "
        f"under 4,200 CHARACTERS after every edit. Do NOT add prose explanations, "
        f"long sample-dialogue blocks, or multi-sentence paragraphs — these expand the "
        f"framing past the NotebookLM Customize box limit and cause the build to hard-fail. "
        f"Insert canonical R-* clause text ONLY (imperative directives, no reasoning). "
        f"If a fix would push the framing over 4,200 chars, cut an equal amount of "
        f"lower-priority prose (e.g. sample friction sentences, Audience section, "
        f"Host dynamic prose paragraphs) to stay within the limit.\n\n"
        f"Do NOT modify the chapter contract, fixtures, _learning/* files, or any other "
        f"book/skill files. Exit when every {severity} finding listed in the report has "
        f"been addressed (or you have determined the finding cannot be fixed without "
        f"author judgment — in which case leave a one-line note at the end of the report)."
    )
    rc, stdout, stderr = _run_claude_p(
        prompt,
        timeout=timeout,
        book_dir=book_dir,
        phase="per-chapter",
        step=f"fixer/{chapter_slug}/{severity}",
    )
    if rc != 0:
        raise AuthoringError(
            phase=f"fixer/{chapter_slug}/{severity}",
            message=f"fixer rc={rc}",
            manual_fallback=f"Manually address {severity} findings in {report}, then --resume.",
            stdout=stdout,
            stderr=stderr,
        )
    return stdout


def invoke_trainer(book_dir: Path, timeout: int = TRAINER_TIMEOUT) -> str:
    """Invoke the podcast-trainer subagent after all chapters have shipped."""
    book_slug = book_dir.name
    prompt = (
        f"Use the Agent tool with subagent_type=podcast-trainer on book `{book_slug}`. "
        f"The trainer reads its canonical spec from `.github/agents/podcast-trainer.agent.md` "
        f"(v2 — substrate-driven). Follow its Protocol §1–§6:\n\n"
        f"  1. Run `python3 scripts/podcast/learn_aggregate.py` (ensures patterns.md is current)\n"
        f"  2. Read `_learning/patterns.md` + open proposals + health JSON\n"
        f"  3. For each proposer-eligible proposal: draft the smallest spec/handbook diff\n"
        f"  4. Regression-gate each diff in a `git worktree add` temp branch via "
        f"`python3 scripts/podcast/test_challenger.py` (all fixtures must stay green)\n"
        f"  5. On green: apply diff to the live book branch + commit with `[trainer]` tag, "
        f"move proposal to `_learning/promoted/` with decision-log block, bump "
        f"`CHALLENGER_VERSION` in `_rules.py` if the diff touched the challenger spec\n"
        f"  6. On red / INVARIANT / P0-class: move proposal to `_learning/archive/` with reason\n\n"
        f"Invocation argument: `{book_slug}`\n\n"
        f"After the agent returns, exit immediately."
    )
    rc, stdout, stderr = _run_claude_p(
        prompt,
        timeout=timeout,
        book_dir=book_dir,
        phase="trainer",
        step="invoke",
    )
    if rc != 0:
        raise AuthoringError(
            phase="trainer",
            message=f"trainer rc={rc}",
            manual_fallback="Invoke podcast-trainer manually then re-invoke orchestrate-book --resume.",
            stdout=stdout,
            stderr=stderr,
        )
    return stdout
