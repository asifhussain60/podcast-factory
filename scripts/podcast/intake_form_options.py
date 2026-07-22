"""intake_form_options.py — single source of truth for the smart-intake-form dropdowns.

Phase 6 (Q12 "minimal typing"): every intake field that can be a dropdown is
pre-seeded here from the pipeline's OWN canonical vocabularies (the content-type
registry + the blueprint classifier enums + the orchestrator's length/video
options). The form NEVER hardcodes these lists — it reads them from here so the
options can't drift from what the pipeline actually accepts.

User additions / renames / removals (the inline "+ add / edit" affordance)
persist to an editable YAML at ``content/_system/intake/form-options.yml`` so they
survive reloads. That file holds ONLY the deltas — the defaults always come from
code, so a new content type added to the registry shows up automatically.

Overrides schema (all keys optional, per field):
    content_profile:
      add:    [my_new_profile]
      rename: {fiction: novel}
      remove: [consumer_explainer]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths
from _blueprint_schema import (
    AUDIENCE_PROFILE_ENUM,
    EPISODE_PLANNING_MODE_ENUM,
)
from _rules import BUCKETS, CONTENT_PROFILES

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise ImportError("intake_form_options requires PyYAML") from exc

# The fields whose dropdowns the form renders, each pre-seeded from a canonical
# pipeline vocabulary. Ordered as the form presents them.
FIELDS: tuple[str, ...] = (
    "content_profile",
    "bucket",
    "audience_profile",
    "host_dynamic",
    "length_tier",
    "video_style",
    "episode_planning_mode",
    "source_language",
    "volume_count",
)


def default_options() -> dict[str, list[str]]:
    """The code-derived default option-set for every dropdown field.

    Pulled from the pipeline's own single-source vocabularies so the form can
    only ever offer values the pipeline accepts:
      - content_profile / bucket → _rules registry
      - audience_profile / episode_planning_mode → _blueprint_schema enums
      - host_dynamic / length_tier / video_style → orchestrator + video LOCKED tables
    """
    return {
        "content_profile": list(CONTENT_PROFILES),
        "bucket": list(BUCKETS),
        "audience_profile": sorted(AUDIENCE_PROFILE_ENUM),
        # NotebookLM "Deep dive or debate" conversation style.
        "host_dynamic": ["deep_dive", "debate"],
        # orchestrate_book.py --length-tier choices.
        "length_tier": ["default_deep_dive", "longer", "extended"],
        # LOCKED video table (CLAUDE.md): islamic→teaching_hybrid, fiction→scenic, technical.
        "video_style": ["teaching_hybrid", "scenic", "technical"],
        "episode_planning_mode": sorted(EPISODE_PLANNING_MODE_ENUM),
        "source_language": ["ar", "en", "ur", "fa", "tr", "id"],
        "volume_count": [str(i) for i in range(1, 13)],
    }


def options_path() -> Path:
    """The editable user-overrides YAML (deltas only)."""
    return _paths.CONTENT_ROOT / "_system" / "intake" / "form-options.yml"


def load_overrides() -> dict[str, dict[str, Any]]:
    """Read the user-overrides YAML, or {} if absent/invalid."""
    p = options_path()
    if not p.is_file():
        return {}
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_overrides(overrides: dict[str, dict[str, Any]]) -> None:
    import os
    import tempfile

    p = options_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".form-options.", suffix=".yml.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.safe_dump(overrides, fh, sort_keys=True, allow_unicode=True)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _apply_field_overrides(defaults: list[str], delta: dict[str, Any]) -> list[str]:
    """Apply rename → remove → add (dedup, order-preserving) to one field's list."""
    rename = delta.get("rename") or {}
    remove = set(delta.get("remove") or [])
    add = delta.get("add") or []
    out: list[str] = []
    seen: set[str] = set()
    for v in defaults:
        v2 = rename.get(v, v) if isinstance(rename, dict) else v
        if v2 in remove or v2 in seen:
            continue
        seen.add(v2)
        out.append(v2)
    for v in add:
        if v not in seen and v not in remove:
            seen.add(v)
            out.append(v)
    return out


def get_form_options() -> dict[str, list[str]]:
    """Return the merged (defaults + user overrides) option-set for every field."""
    defaults = default_options()
    overrides = load_overrides()
    merged: dict[str, list[str]] = {}
    for field, vals in defaults.items():
        delta = overrides.get(field) if isinstance(overrides.get(field), dict) else None
        merged[field] = _apply_field_overrides(vals, delta) if delta else list(vals)
    return merged


def add_option(field: str, value: str) -> dict[str, list[str]]:
    """Add a new value to a field's dropdown (persists). Returns the merged set."""
    _require_field(field)
    if not value or not value.strip():
        raise ValueError("add_option: value must be non-empty")
    value = value.strip()
    overrides = load_overrides()
    delta = overrides.setdefault(field, {})
    adds = delta.setdefault("add", [])
    # Don't double-add (whether it's a default or already-added value).
    if value not in adds and value not in default_options().get(field, []):
        adds.append(value)
    # If it was previously removed, un-remove it.
    if value in (delta.get("remove") or []):
        delta["remove"] = [v for v in delta["remove"] if v != value]
    _write_overrides(overrides)
    return get_form_options()


def rename_option(field: str, old: str, new: str) -> dict[str, list[str]]:
    """Rename an existing value in a field's dropdown (persists)."""
    _require_field(field)
    if not new or not new.strip():
        raise ValueError("rename_option: new value must be non-empty")
    new = new.strip()
    overrides = load_overrides()
    delta = overrides.setdefault(field, {})
    if old in default_options().get(field, []):
        # Renaming a default: record the mapping.
        delta.setdefault("rename", {})[old] = new
    else:
        # Renaming a user-added value: rewrite it in the add list.
        adds = delta.setdefault("add", [])
        delta["add"] = [new if v == old else v for v in adds]
    _write_overrides(overrides)
    return get_form_options()


def _require_field(field: str) -> None:
    if field not in FIELDS:
        raise ValueError(f"unknown form field {field!r} (expected one of {FIELDS})")


# ── CLI (the JSON contract the Astro intake endpoints shell out to) ──────────
def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description="smart-intake-form dropdown options")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("get")
    a = sub.add_parser("add")
    a.add_argument("field")
    a.add_argument("value")
    r = sub.add_parser("rename")
    r.add_argument("field")
    r.add_argument("old")
    r.add_argument("new")
    args = p.parse_args(argv)
    try:
        if args.cmd == "get":
            out = get_form_options()
        elif args.cmd == "add":
            out = add_option(args.field, args.value)
        else:
            out = rename_option(args.field, args.old, args.new)
    except ValueError as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 2
    print(json.dumps({"ok": True, "options": out}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
