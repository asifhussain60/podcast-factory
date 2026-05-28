"""seal.py — Stamp bundle.yml stage transitions for the translation pipeline.

Valid transitions:
  --stage translated  : reviewed  → translated   (set by translate.py already, but can be forced)
  --stage adapted     : translated → adapted      (operator calls after writing adapted-extract.en.md)
  --stage challenged  : adapted   → challenged    (set by wisdom-challenger after convergence)

Also validates that the required output files exist for each stage before stamping.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

_STAGE_ORDER = ["reviewed", "translated", "adapted", "challenged"]
_REQUIRED_FILES: dict[str, list[str]] = {
    "translated": ["raw-extract.en.md"],
    "adapted": ["raw-extract.en.md", "adapted-extract.en.md", "adaptation-citations.jsonl"],
    "challenged": ["adapted-extract.en.md", "adaptation-citations.jsonl", "wisdom-challenger-report.md"],
}


def _read_stage(bundle_yml: Path) -> str:
    for line in bundle_yml.read_text(encoding="utf-8").splitlines():
        if line.startswith("stage:"):
            return line.split(":", 1)[1].strip()
    return ""


def _update_stage(bundle_yml: Path, new_stage: str) -> None:
    text = bundle_yml.read_text(encoding="utf-8")
    lines = [
        f"stage: {new_stage}" if l.startswith("stage:") else l
        for l in text.splitlines()
    ]
    bundle_yml.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_seal_block(bundle_yml: Path, stage: str, completed_at: str) -> None:
    text = bundle_yml.read_text(encoding="utf-8")
    key = f"seal_{stage}"
    # Strip prior block for idempotence
    lines = text.splitlines()
    out: list[str] = []
    skipping = False
    for line in lines:
        if line.startswith(f"{key}:"):
            skipping = True
            continue
        if skipping and (not line or line[0] in (" ", "\t")):
            continue
        skipping = False
        out.append(line)
    block = f"\n{key}:\n  completed_at: {completed_at}\n"
    bundle_yml.write_text("\n".join(out).rstrip() + block, encoding="utf-8")


def seal_stage(bundle_root: Path, target_stage: str) -> dict:
    """Validate outputs and stamp bundle.yml to target_stage.

    Returns {"sealed": True, "stage": target_stage} on success.
    Raises on missing files or invalid transition.
    """
    bundle_yml = bundle_root / "bundle.yml"
    text_dir = bundle_root / "_system" / "source" / "text"

    if not bundle_yml.exists():
        raise FileNotFoundError(f"bundle.yml not found: {bundle_yml}")

    current = _read_stage(bundle_yml)

    # Validate transition
    if target_stage not in _STAGE_ORDER:
        raise ValueError(f"Unknown stage '{target_stage}'. Valid: {_STAGE_ORDER}")
    current_idx = _STAGE_ORDER.index(current) if current in _STAGE_ORDER else -1
    target_idx = _STAGE_ORDER.index(target_stage)
    if target_idx <= current_idx and current != "reviewed":
        if current == target_stage:
            print(f"SKIPPED (already {target_stage}): {bundle_root}")
            return {"sealed": False, "skipped": True, "stage": target_stage}
        raise RuntimeError(
            f"Cannot transition from '{current}' to '{target_stage}' — would go backwards."
        )

    # Validate required output files
    required = _REQUIRED_FILES.get(target_stage, [])
    missing = [f for f in required if not (text_dir / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing required files for stage '{target_stage}': {missing}\n"
            f"  Expected under: {text_dir}"
        )

    completed_at = datetime.now(timezone.utc).isoformat()
    _update_stage(bundle_yml, target_stage)
    _append_seal_block(bundle_yml, target_stage, completed_at)

    print(f"SEALED → {target_stage}: {bundle_root}")
    return {"sealed": True, "stage": target_stage, "completed_at": completed_at}
