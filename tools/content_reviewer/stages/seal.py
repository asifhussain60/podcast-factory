"""seal.py — validate the review outputs, switch bundle.yml.stage to 'reviewed',
and stamp needs_human_review flag if any annotation needs human attention.
"""
from __future__ import annotations
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FAILURE_LOG = REPO_ROOT / "_workspace" / "plan" / "kashkole-rollout-failures.log"


def _update_stage(bundle_yml: Path, new_stage: str) -> None:
    text = bundle_yml.read_text(encoding="utf-8")
    out: list[str] = []
    for line in text.splitlines():
        if line.startswith("stage:"):
            out.append(f"stage: {new_stage}")
        else:
            out.append(line)
    bundle_yml.write_text("\n".join(out) + "\n", encoding="utf-8")


def _set_needs_human_review_flag(bundle_yml: Path, value: bool) -> None:
    text = bundle_yml.read_text(encoding="utf-8")
    lines = text.splitlines()
    # Strip any pre-existing top-level flag.
    out = [l for l in lines if not l.startswith("needs_human_review:")]
    out.append(f"needs_human_review: {'true' if value else 'false'}")
    bundle_yml.write_text("\n".join(out) + "\n", encoding="utf-8")


def seal_book(bundle_root: Path) -> dict:
    bundle_yml = bundle_root / "bundle.yml"
    text_dir = bundle_root / "_system" / "source" / "text"
    editorial_md = text_dir / "editorial-review.md"
    annotations_jsonl = text_dir / "editorial-annotations.jsonl"

    if not bundle_yml.exists():
        raise FileNotFoundError(f"bundle.yml not found at {bundle_yml}")
    if not editorial_md.exists() or not annotations_jsonl.exists():
        raise FileNotFoundError(
            f"Reviewer outputs missing under {text_dir}. Run `review` first."
        )

    # Inspect annotations for needs-human-review entries.
    nhr_count = 0
    total = 0
    with annotations_jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            total += 1
            if obj.get("type") == "needs-human-review":
                nhr_count += 1

    needs_human = nhr_count > 0
    _set_needs_human_review_flag(bundle_yml, needs_human)
    _update_stage(bundle_yml, "reviewed")

    if needs_human:
        FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with FAILURE_LOG.open("a", encoding="utf-8") as f:
            f.write(
                f"needs_human_review bundle={bundle_root} "
                f"annotations={nhr_count}/{total}\n"
            )

    return {
        "total_annotations": total,
        "needs_human_review": needs_human,
        "needs_human_review_count": nhr_count,
    }
