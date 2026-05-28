"""Per-binder driver for the autonomous KAHSKOLE rollout.

Usage:
  python scripts/kashkole/binder_driver.py survey BINDER_ID
  python scripts/kashkole/binder_driver.py prepare BINDER_ID
  python scripts/kashkole/binder_driver.py vision-list BINDER_ID
  python scripts/kashkole/binder_driver.py finalize-review-seal BINDER_ID

Phases:
  survey  — print list of chapter IDs + names for the binder.
  prepare — call `tools.source_extractor prepare` for each chapter. Skips
            chapters already at stage 'prepared' or beyond. Logs failures.
  vision-list — print, per chapter, the list of PNG paths that still need a
            JSON sidecar (so the in-conversation Claude can Read each and
            Write the sidecar).
  finalize-review-seal — for each chapter with stage 'prepared', run
            finalize → review → seal. Logs failures.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VENV = REPO_ROOT / "CONTENT" / "_shared" / "kashkole-corpus" / ".venv" / "bin" / "python"
FAILURE_LOG = REPO_ROOT / "_workspace" / "plan" / "kashkole-rollout-failures.log"
EXTRACT_ROOT = REPO_ROOT / "CONTENT" / "_shared" / "kashkole-corpus" / "extracted" / "kashkole"


def survey(binder_id: int) -> list[tuple[int, int, str]]:
    """Return list of (order, chapter_id, name) for the binder."""
    sys.path.insert(0, str(REPO_ROOT))
    from tools.source_extractor.db import query_json
    chaps = query_json("KASHKOLE", f"""
SELECT bc.BinderChapterOrder AS ord, c.ChapterID AS id, c.ChapterName AS name
FROM BinderChapters bc JOIN Chapters c ON c.ChapterID = bc.ChapterID
WHERE bc.BinderID = {binder_id} ORDER BY bc.BinderChapterOrder FOR JSON PATH;""")
    return [(c["ord"], c["id"], c["name"]) for c in chaps]


def get_bundle_root(binder_id: int, chapter_id: int) -> Path:
    """Compute bundle root by resolving via source_extractor adapter."""
    sys.path.insert(0, str(REPO_ROOT))
    from tools.source_extractor.adapters import get_adapter
    from tools.source_extractor.adapters.base import BookIds
    from tools.source_extractor.bundle import bundle_paths
    adapter = get_adapter("kashkole")
    meta = adapter.resolve_book(BookIds(shelf_id=binder_id, book_id=chapter_id))
    return bundle_paths(EXTRACT_ROOT.parent, meta).root


def get_stage(bundle_root: Path) -> str | None:
    """Return the bundle.yml stage value (None if bundle.yml missing)."""
    bundle_yml = bundle_root / "bundle.yml"
    if not bundle_yml.exists():
        return None
    for line in bundle_yml.read_text(encoding="utf-8").splitlines():
        if line.startswith("stage:"):
            return line.split(":", 1)[1].strip()
    return None


def _log_failure(msg: str) -> None:
    with FAILURE_LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def _run(cmd: list[str], step_name: str) -> bool:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=300)
        if r.returncode != 0:
            _log_failure(f"{step_name} failed cmd={' '.join(cmd)} stderr={r.stderr.strip()[:500]}")
            print(f"  FAIL {step_name}: {r.stderr.strip()[:300]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        _log_failure(f"{step_name} timeout cmd={' '.join(cmd)}")
        print(f"  FAIL {step_name}: timeout")
        return False


def cmd_survey(binder_id: int) -> None:
    chaps = survey(binder_id)
    print(f"# Binder {binder_id} — {len(chaps)} chapters")
    for ord_, cid, name in chaps:
        bundle_root = get_bundle_root(binder_id, cid)
        stage = get_stage(bundle_root) or "missing"
        print(f"#{ord_:02d}  id={cid:>4}  stage={stage}  {name}")


def cmd_prepare(binder_id: int) -> None:
    chaps = survey(binder_id)
    for ord_, cid, name in chaps:
        bundle_root = get_bundle_root(binder_id, cid)
        stage = get_stage(bundle_root)
        if stage in ("prepared", "finalized", "reviewed"):
            print(f"#{ord_:02d}  id={cid}  SKIP (stage={stage})")
            continue
        print(f"#{ord_:02d}  id={cid}  preparing…")
        ok = _run(
            [str(VENV), "-m", "tools.source_extractor", "prepare", "kashkole",
             "--binder", str(binder_id), "--chapter", str(cid)],
            f"prepare binder={binder_id} chapter={cid}",
        )
        if ok:
            print(f"  OK")


def cmd_vision_list(binder_id: int) -> None:
    """Print, per chapter, the absolute paths of PNGs lacking a sidecar."""
    chaps = survey(binder_id)
    total_pending = 0
    for ord_, cid, name in chaps:
        bundle_root = get_bundle_root(binder_id, cid)
        stage = get_stage(bundle_root)
        if stage is None:
            print(f"#{ord_:02d}  id={cid}  NO BUNDLE (skipped during prepare?)")
            continue
        images_dir = bundle_root / "_system" / "source" / "images"
        if not images_dir.exists():
            print(f"#{ord_:02d}  id={cid}  no images/ dir  ({stage})")
            continue
        pngs = sorted(images_dir.glob("*.png"))
        pending = [p for p in pngs if not (p.with_suffix(".json")).exists()]
        if not pending:
            print(f"#{ord_:02d}  id={cid}  all {len(pngs)} images have sidecars  ({stage})")
            continue
        total_pending += len(pending)
        print(f"#{ord_:02d}  id={cid}  pending vision for {len(pending)}/{len(pngs)} images:")
        for p in pending:
            print(f"  {p}")
    print(f"# TOTAL pending vision: {total_pending} images")


def cmd_finalize_review_seal(binder_id: int) -> None:
    chaps = survey(binder_id)
    for ord_, cid, name in chaps:
        bundle_root = get_bundle_root(binder_id, cid)
        stage = get_stage(bundle_root)
        if stage is None:
            print(f"#{ord_:02d}  id={cid}  NO BUNDLE — skip")
            continue
        if stage == "reviewed":
            print(f"#{ord_:02d}  id={cid}  already reviewed — skip")
            continue

        if stage == "prepared":
            print(f"#{ord_:02d}  id={cid}  finalize…")
            if not _run(
                [str(VENV), "-m", "tools.source_extractor", "finalize", "kashkole",
                 "--binder", str(binder_id), "--chapter", str(cid)],
                f"finalize binder={binder_id} chapter={cid}",
            ):
                continue
            stage = "finalized"

        if stage == "finalized":
            print(f"#{ord_:02d}  id={cid}  review…")
            if not _run(
                [str(VENV), "-m", "tools.content_reviewer", "review", "kashkole",
                 "--binder", str(binder_id), "--chapter", str(cid)],
                f"review binder={binder_id} chapter={cid}",
            ):
                continue
            print(f"#{ord_:02d}  id={cid}  seal…")
            if not _run(
                [str(VENV), "-m", "tools.content_reviewer", "seal", "kashkole",
                 "--binder", str(binder_id), "--chapter", str(cid)],
                f"seal binder={binder_id} chapter={cid}",
            ):
                continue
            print(f"#{ord_:02d}  id={cid}  REVIEWED")


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    phase = sys.argv[1]
    binder_id = int(sys.argv[2])
    if phase == "survey":
        cmd_survey(binder_id)
    elif phase == "prepare":
        cmd_prepare(binder_id)
    elif phase == "vision-list":
        cmd_vision_list(binder_id)
    elif phase == "finalize-review-seal":
        cmd_finalize_review_seal(binder_id)
    else:
        print(f"Unknown phase: {phase}")
        sys.exit(2)


if __name__ == "__main__":
    main()
