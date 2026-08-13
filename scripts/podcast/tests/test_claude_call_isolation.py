#!/usr/bin/env python3
"""Guard bounded Claude calls against full agent-mode slowdowns."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ISOLATION_KWARGS = {
    "tools",
    "safe_mode",
    "no_chrome",
    "no_session_persistence",
    "system_prompt",
    "effort",
}

# These calls intentionally need repository tools because the prompt asks Claude
# to write/edit files or invoke another agent. Everything else should use
# pure_text_call_options()/pure_json_call_options().
AGENTIC_ALLOWLIST = {
    ("_authoring/_agent_invocations.py", "per-chapter"),
    ("_authoring/_agent_invocations.py", "trainer"),
    ("_authoring/_book_intelligence.py", "0ci"),
    ("_authoring/_chapter_design.py", "0d"),
    ("_authoring/_dialogue.py", "audio-script"),
    ("_authoring/_enrichment.py", "0e"),
    ("_authoring/_framing.py", "per-chapter"),
    ("_dialogue_convergence.py", "audio-script"),
    ("_slide_authoring.py", "11b-slide-authoring"),
    ("_slide_convergence.py", "11b-slide-authoring"),
    ("_slide_convergence.py", "11b-slide-challenger"),
    ("_slide_import.py", ""),
    ("_slide_replicate.py", ""),
    ("augment_fiction_sidecar.py", "0e-fiction-sidecar"),
    ("holistic_editorial.py", "0a-synthesize"),
    ("multi_source_synthesis.py", "0a-synthesize"),
}


def _literal_keyword(call: ast.Call, name: str) -> str:
    for kw in call.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return ""


def _call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def test_non_agentic_claude_calls_use_isolated_mode():
    offenders: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        if path.parts[-2] == "tests":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _call_name(node) not in {"_run_claude_p", "_run_claude_p_with_retry"}:
                continue
            has_isolation = any(kw.arg in ISOLATION_KWARGS or kw.arg is None for kw in node.keywords)
            if has_isolation:
                continue
            phase = _literal_keyword(node, "phase")
            if (rel, phase) in AGENTIC_ALLOWLIST:
                continue
            offenders.append(f"{rel}:{node.lineno} phase={phase or '(dynamic/blank)'}")

    assert offenders == []
