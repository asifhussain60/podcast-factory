"""Mechanical checks that run BEFORE the pipeline spends anything.

Both were written on 2026-08-31 for the same reason, from the same day's damage:
the rules they enforce were already written down in prose and were violated
anyway. `CLAUDE.md` names `content_profile` four times and a recorded sermon
still ran the book pipeline; `_chapter_design.py` documents its own checkpoint
scheme and stale checkpoints from a different plan would still have been
honoured. Prose does not bind. A check does.

Both are DECIDABLE — no model, no network, no judgement — so they cost nothing
and can run on every launch.

Both degrade to "no claim" when the evidence is absent rather than guessing.
That is what makes them safe to add to a repo with twenty-seven books already on
disk: a book that predates the thing being checked is not retroactively broken
by it.
"""

from __future__ import annotations

from pathlib import Path

# ── A. The folder a book lives in must agree with the profile it declares ────


def bucket_mismatch(book_dir: Path) -> str | None:
    """The message to halt on, or None when the book is consistent.

    THE FAILURE THIS CATCHES cost two chapters on 2026-08-30.
    `purification-of-the-heart` sat in `content/Sessions/` with no
    `content_profile`, which defaults to `islamic_scholarly` — so every phase
    read it as a scholarly book, and phase 0e's enrichment rewrote a recorded
    sermon into third-person literary essays before anyone noticed.

    The folder said one thing and the config said another, and nothing compared
    them. That comparison is one function call: the bucket a profile resolves to
    is `bucket_for_profile`, which `_paths` already uses to decide where a book
    goes. Asking it whether the book is where it says it should be is free.

    Absent config reads as absent, not as a default: a book with no
    series-config.yaml at all is left alone, because inventing a profile for it
    is exactly the guess that caused the damage.
    """
    try:
        import yaml
        from _content_types import bucket_for_profile
        from _paths import CONTENT_ROOT
    except Exception:
        return None

    book_dir = Path(book_dir).resolve()
    try:
        rel = book_dir.relative_to(Path(CONTENT_ROOT).resolve())
    except ValueError:
        return None  # not under content/ — a test fixture or a work parent
    actual = rel.parts[0] if rel.parts else ""
    if not actual or actual.startswith(("_", ".")):
        return None

    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.is_file():
        return None
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    if not isinstance(cfg, dict):
        return None

    profile = cfg.get("content_profile")
    # A config that exists but never answers the question is the exact shape of
    # the failure, so it IS reported — with the missing key named, because
    # "declared nothing" and "declared wrongly" need different fixes.
    declared = str(profile).strip() if profile else ""
    expected = bucket_for_profile(declared or None)
    if expected == actual:
        return None

    if not declared:
        return (
            f"this book is in content/{actual}/ but its series-config.yaml declares no "
            f"content_profile, so every phase reads it as the default and resolves it to "
            f"content/{expected}/. That mismatch is what ran a recorded sermon through the "
            f"book pipeline on 2026-08-30 and rewrote two of its chapters."
        )
    return (
        f"this book is in content/{actual}/ but declares content_profile: {declared}, "
        f"which resolves to content/{expected}/. The folder and the config disagree about "
        f"what this content IS, and every phase trusts the config."
    )


# ── B. Checkpoints must belong to the plan currently on disk ────────────────


def stale_done_markers(chunks_dir: Path, source_chapters: list) -> list[str]:
    """Checkpoints whose recorded chapter is not the plan's chapter at that index.

    THE FAILURE THIS CATCHES was caught by hand on 2026-08-31 and would have
    been silent. Phase 0d checkpoints each source chapter as `sc-NNN.done` and
    skips any index already marked. The markers are keyed by POSITION, so when a
    book is re-segmented — seventeen chapters replaced by twenty-four — `sc-001`
    stops meaning what it meant: it was "The World and the Envious Heart" and
    becomes "Love of the World". Left in place, seventeen of the twenty-four
    would have been skipped as already done, keeping chapter files belonging to
    a plan that no longer exists. The run would have reported success.

    The marker already records `source_title=`, so no new state is needed: a
    marker whose title disagrees with the plan's title at its index is from a
    different plan. A marker with no recorded title makes no claim and is left
    alone, which is what keeps every book written before this check resumable.
    """
    problems: list[str] = []
    chunks_dir = Path(chunks_dir)
    if not chunks_dir.is_dir():
        return problems

    planned = {}
    for i, sc in enumerate(source_chapters, start=1):
        idx = sc.get("sc_index") if isinstance(sc, dict) else None
        planned[int(idx) if idx else i] = str((sc or {}).get("source_title") or "").strip()

    for marker in sorted(chunks_dir.glob("sc-*.done")):
        try:
            fields = dict(line.split("=", 1) for line in marker.read_text(encoding="utf-8").splitlines() if "=" in line)
        except Exception:
            continue
        recorded = fields.get("source_title", "").strip()
        if not recorded:
            continue  # makes no claim
        try:
            idx = int(fields.get("sc_index") or marker.stem.split("-")[1])
        except (ValueError, IndexError):
            continue
        if idx not in planned:
            problems.append(
                f"{marker.name} checkpoints chapter {idx} ({recorded!r}), but the plan has only {len(planned)} chapters"
            )
        elif planned[idx] != recorded:
            problems.append(
                f"{marker.name} checkpoints {recorded!r} at index {idx}, but the plan's "
                f"chapter {idx} is {planned[idx]!r}"
            )
    return problems


def assert_bucket_matches(slug: str, *, find_content, err) -> bool:
    """False when the launch must stop. Reports the mismatch and the fix.

    The lookup, the check and the two error lines live here rather than in
    `orchestrate_book.py` because that module sits exactly ON the 600-line
    DR-005 limit — it is not grandfathered, so anything added to it has to come
    back out. The caller stays one `if`.
    """
    ref = find_content(slug)
    if not ref:
        return True  # a slug with no folder fails later, with a better message
    message = bucket_mismatch(ref[2])
    if not message:
        return True
    err(f"{slug}: {message}")
    err("Fix content_profile in _system/series-config.yaml (or move the folder), then re-run.")
    return False
