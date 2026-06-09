"""phases/per_chapter.py — per_chapter_pass: extract → frame → build → converge.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT  # noqa: E402
from _authoring import AuthoringError, author_framing  # noqa: E402
from _convergence import ChapterOutcome, converge_chapter  # noqa: E402
from phases.series_plan import _resolve_episode_id  # noqa: E402

EXTRACT_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "extract_chapter.py"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "build_episode_txt.py"

# F32 framing cache: a sidecar written next to 00-framing.md after a successful
# author_framing. Its presence + a matching chapter-input signature lets a
# watchdog RESTART skip the (expensive) re-authoring of an already-authored
# framing — extract --force overwrites 00-framing.md with a template, so the
# authored copy is preserved across the extract and restored.
_FRAMING_SIG_NAME = ".framing-sig"


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _chapter_sig(chapter_file: Path) -> str:
    """Stable signature of a framing's primary input (the chapter text)."""
    try:
        return hashlib.sha256(chapter_file.read_bytes()).hexdigest()[:16]
    except OSError:
        return ""


def _draft_dir_for(book_dir: Path, chapter_slug: str) -> Path | None:
    """Resolve the episode-draft dir (EP##-<slug>) for a chapter, or None."""
    ep_root = book_dir / "_system" / "episode-drafts"
    if not ep_root.is_dir():
        return None
    for d in sorted(ep_root.iterdir()):
        if d.is_dir() and d.name.endswith(f"-{chapter_slug}"):
            return d
    return None


def per_chapter_pass(
    book_dir: Path,
    chapter_slug: str,
    *,
    per_chapter_cost_cap: float = 0.0,
    book_cost_cap: float = 0.0,
    chapter_cost_fn=None,
    book_cost_fn=None,
    heartbeat=None,
) -> ChapterOutcome:
    """Run the full per-chapter pipeline for one chapter.

    extract → author framing → pipeline_lint → build episode .txt → converge.
    Returns the convergence ChapterOutcome. Never raises — failure is encoded
    in the returned outcome's `final_verdict = "FAILED"`.

    Safety-rail params (Phase 3, all optional) are forwarded to converge_chapter:
    per/whole-book cost ceilings + a heartbeat. The F32 framing cache is applied
    here: a watchdog restart with an unchanged chapter + an already-authored
    framing skips the LLM re-authoring step.
    """
    book_slug = book_dir.name

    chapter_file = next((book_dir / "chapters").glob(f"ch*-{chapter_slug}.txt"), None)
    if chapter_file is None:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[f"chapter file missing for slug {chapter_slug} "
                   f"(expected at chapters/ch*-{chapter_slug}.txt)"],
        )
    chapter_ref = f"{book_slug}/{chapter_file.stem}"

    # F32 framing cache — BEFORE the destructive extract --force (which overwrites
    # 00-framing.md with a template), capture an already-authored framing whose
    # chapter-input signature still matches, so a restart can reuse it.
    sig = _chapter_sig(chapter_file)
    cached_framing: str | None = None
    if sig:
        _prior_draft = _draft_dir_for(book_dir, chapter_slug)
        if _prior_draft is not None:
            _fp = _prior_draft / "00-framing.md"
            _sp = _prior_draft / _FRAMING_SIG_NAME
            if (_fp.is_file() and _sp.is_file()
                    and _sp.read_text(encoding="utf-8").strip() == sig):
                cached_framing = _fp.read_text(encoding="utf-8")

    # 1. Extract — scaffold the episode-draft folder + bundle from the contract.
    rc, out, err = _run(
        [sys.executable, str(EXTRACT_SCRIPT), chapter_ref, "--force"]
    )
    if rc != 0:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[f"extract_chapter.py failed for {chapter_ref!r}: rc={rc}: {err.strip()[:200]}"],
        )

    # 2. Author framing — LLM call (or F32 cache hit: restore the prior authored
    # framing that extract --force just overwrote, and skip the LLM re-authoring).
    _draft = _draft_dir_for(book_dir, chapter_slug)
    framing_cached = False
    if cached_framing is not None and _draft is not None:
        (_draft / "00-framing.md").write_text(cached_framing, encoding="utf-8")
        framing_cached = True
    else:
        # (The $0 deterministic smoke gate runs once at the loop level in
        # chapter_driver, before any chapter is attempted — see smoke_check_book.
        # It is intentionally NOT duplicated here: the extract step above already
        # validates path/contract for direct single-chapter callers.)
        try:
            author_framing(book_dir, chapter_slug)
        except AuthoringError as e:
            return ChapterOutcome(
                chapter_slug=chapter_slug,
                final_verdict="FAILED",
                outer_iterations=0,
                fixer_attempts=0,
                p0_remaining=0, p1_remaining=0, p2_remaining=0,
                notes=[f"framing authoring failed: {e}"],
            )
    # Stamp the framing signature so a later restart can reuse this framing.
    if sig and _draft is not None:
        try:
            (_draft / _FRAMING_SIG_NAME).write_text(sig, encoding="utf-8")
        except OSError:
            pass

    # 2.5. Pre-flight lint: run pipeline_lint against the freshly-authored
    # framing + chapter pair. Catches structural mismatches BEFORE build's hard
    # gates do. Deterministic, $0 cost.
    _episode_id = _resolve_episode_id(book_dir, chapter_file, chapter_slug)
    _lint_path = Path(__file__).resolve().parents[1] / "pipeline_lint.py"
    _lint_rc, _lint_out, _lint_err = _run(
        [sys.executable, str(_lint_path),
         "--book-dir", str(book_dir),
         "--episode", _episode_id]
    )
    if _lint_rc == 1:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=1, p1_remaining=0, p2_remaining=0,
            notes=[f"pipeline_lint P0: framing structural mismatch:\n{_lint_out.strip()[:600]}"],
        )

    # 3. Build the episode .txt — deterministic gate.
    episode_id = _resolve_episode_id(book_dir, chapter_file, chapter_slug)
    rc, out, err = _run([sys.executable, str(BUILD_SCRIPT), str(book_dir), episode_id])
    if rc != 0:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[f"build_episode_txt.py failed: rc={rc}: {err.strip()[:300]}"],
        )

    # 3.5. Knowledge augmentation — prepend prior-doctrine context block when enabled.
    # Gate: meta.yml series.enable_knowledge_augmenter must be True (default False).
    # Books without that flag are untouched; tradition-match guard is inside the augmenter.
    # Failure is non-fatal: the episode .txt remains as built.
    augmentation_note: str | None = None
    try:
        from intelligence.augmenter import augment_episode_text as _augment  # noqa: PLC0415
        episode_path = book_dir / "episodes" / f"{episode_id}.txt"
        if episode_path.exists():
            original = episode_path.read_text(encoding="utf-8")
            augmented = _augment(original, book_dir, episode_slug=episode_id)
            if augmented != original:
                episode_path.write_text(augmented, encoding="utf-8")
                augmentation_note = "knowledge augmentation applied"
    except Exception as _aug_err:  # noqa: BLE001
        augmentation_note = f"knowledge augmentation skipped ({_aug_err})"

    # 4. Convergence loop (with Phase 3 safety rails threaded through).
    outcome = converge_chapter(
        book_dir, chapter_slug,
        per_chapter_cost_cap=per_chapter_cost_cap,
        book_cost_cap=book_cost_cap,
        chapter_cost_fn=chapter_cost_fn,
        book_cost_fn=book_cost_fn,
        heartbeat=heartbeat,
    )
    if framing_cached:
        outcome.notes.append("F32: framing cache hit — skipped LLM re-authoring")
    if augmentation_note:
        outcome.notes.append(augmentation_note)
    return outcome
