#!/usr/bin/env python3
"""Podcast/journal boundary check (P1.1).

AST-scans every `.py` file under `scripts/podcast/` looking for write/
append/`open(...,'w')` operations targeting forbidden paths:
    content/babu-memoir/**
    content/_shared/**
    scripts/memoir/**
    scripts/site/**

ALLOWED exception (whitelisted by `meta.scope_in_writes_to_shared_exception`
in `_workspace/plan/podcast-plan.yaml`):
    content/_shared/arabic/06-abjad-numerals.md  (P4 one-time write)

Exits 0 on clean tree; exits non-zero with `file:line` lines on any violation.
Targets <2s runtime on the current scripts/podcast/ tree.

Per `_workspace/plan/podcast-plan.yaml` P1.1.
"""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from _paths import REPO_ROOT

SCRIPTS_PODCAST = REPO_ROOT / "scripts" / "podcast"

FORBIDDEN_PATH_PATTERNS: tuple[str, ...] = (
    "content/babu-memoir/",
    "content/_shared/",
    "scripts/memoir/",
    "scripts/site/",
)

# The single whitelisted write path. Anything ending in this suffix is exempt.
WHITELISTED_PATHS: tuple[str, ...] = (
    "content/_shared/arabic/06-abjad-numerals.md",
)

# Open modes that are violations: anything with 'w', 'a', 'x'.
WRITE_MODE_RE = re.compile(r"[wax]")


@dataclass(frozen=True)
class Violation:
    file: Path
    line: int
    col: int
    target: str
    reason: str

    def fmt(self) -> str:
        rel = self.file.relative_to(REPO_ROOT)
        return f"{rel}:{self.line}:{self.col}: writes forbidden path {self.target!r} ({self.reason})"


def _is_whitelisted(target_str: str) -> bool:
    return any(target_str.endswith(w) for w in WHITELISTED_PATHS)


def _matches_forbidden(target_str: str) -> str | None:
    for pat in FORBIDDEN_PATH_PATTERNS:
        if pat in target_str:
            return pat
    return None


def _extract_str_argument(node: ast.AST) -> str | None:
    """Best-effort literal-string extraction from a call argument.

    Recognises:
        "literal/path"
        Path("literal/path")
        Path("literal") / "subdir" / "file.md"  (joined chain)
        REPO_ROOT / "scripts/memoir/foo.py"     (treat known-prefix vars as wildcards)
        f-strings with literal segments (only matches the literal parts)
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        # f-string: concatenate the literal segments only
        return "".join(v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Path":
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            return node.args[0].value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div,)):
        # Path('x') / 'y' / 'z'    OR    repo_root / 'scripts/memoir/...'
        parts = []
        # Walk left, accumulate strings.
        def _walk(n: ast.AST) -> None:
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
                _walk(n.left)
                _walk(n.right)
            else:
                s = _extract_str_argument(n)
                if s:
                    parts.append(s)
        _walk(node)
        if parts:
            return "/".join(parts)
    return None


class _BoundaryVisitor(ast.NodeVisitor):
    def __init__(self, file: Path):
        self.file = file
        self.violations: list[Violation] = []

    def _check_str(self, target_str: str, node: ast.AST, reason: str) -> None:
        if _is_whitelisted(target_str):
            return
        pat = _matches_forbidden(target_str)
        if pat is None:
            return
        self.violations.append(
            Violation(
                file=self.file,
                line=getattr(node, "lineno", 0),
                col=getattr(node, "col_offset", 0),
                target=target_str,
                reason=reason,
            )
        )

    def visit_Call(self, node: ast.Call) -> None:
        # open(path, 'w') / open(path, mode='w')
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            mode = None
            if len(node.args) >= 2:
                m = node.args[1]
                if isinstance(m, ast.Constant) and isinstance(m.value, str):
                    mode = m.value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    mode = kw.value.value
            if mode and WRITE_MODE_RE.search(mode):
                if node.args:
                    target_str = _extract_str_argument(node.args[0])
                    if target_str:
                        self._check_str(target_str, node, f"open(..., mode={mode!r})")

        # Path(...).write_text / .write_bytes / .open('w'...)
        if isinstance(node.func, ast.Attribute):
            method = node.func.attr
            if method in ("write_text", "write_bytes"):
                target_str = _extract_str_argument(node.func.value)
                if target_str:
                    self._check_str(target_str, node, f".{method}(...)")
            elif method == "open":
                # Path(...).open('w')
                mode = None
                if node.args:
                    m = node.args[0]
                    if isinstance(m, ast.Constant) and isinstance(m.value, str):
                        mode = m.value
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        mode = kw.value.value
                if mode and WRITE_MODE_RE.search(mode):
                    target_str = _extract_str_argument(node.func.value)
                    if target_str:
                        self._check_str(target_str, node, f".open({mode!r})")

        self.generic_visit(node)


def scan_file(file: Path) -> list[Violation]:
    """Scan one .py file. Returns list of violations."""
    try:
        tree = ast.parse(file.read_text(), filename=str(file))
    except SyntaxError as e:
        # Don't crash on a syntax error in a target file — surface it as a
        # special violation so it's visible in CI output.
        return [
            Violation(
                file=file,
                line=e.lineno or 0,
                col=e.offset or 0,
                target="<syntax-error>",
                reason=f"SyntaxError: {e.msg}",
            )
        ]
    v = _BoundaryVisitor(file)
    v.visit(tree)
    return v.violations


def scan_tree(root: Path = SCRIPTS_PODCAST) -> list[Violation]:
    """Scan every .py file under `root` recursively. Skips __pycache__."""
    out: list[Violation] = []
    for py in root.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        out.extend(scan_file(py))
    return out


def main(argv: list[str] | None = None) -> int:
    violations = scan_tree()
    if violations:
        for v in violations:
            print(v.fmt(), file=sys.stderr)
        print(
            f"\n{len(violations)} podcast/journal boundary violation(s). "
            f"See scripts/podcast/_boundary_check.py for the whitelist.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
