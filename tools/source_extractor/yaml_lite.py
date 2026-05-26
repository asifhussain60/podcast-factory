"""Tiny YAML emit helpers — no PyYAML dependency.

We hand-emit YAML because the meta files are simple and we want byte-for-byte
deterministic output for diffability across runs.
"""
from __future__ import annotations
import json


def yaml_str(s: str | None) -> str:
    """Quote a string for YAML output. Bare-string when safe; JSON-quoted otherwise."""
    if s is None or s == "":
        return "''"
    if any(c in s for c in ":#\"'\n[]{},&*!|>%@`"):
        return json.dumps(s, ensure_ascii=False)
    return s


def yaml_value(v) -> str:
    """Render a scalar Python value as YAML."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if v is None:
        return "null"
    return yaml_str(str(v))
