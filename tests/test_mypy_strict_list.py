"""The strict-typing list is a contract: every entry exists, once, and the list only grows."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIST = ROOT / "infra" / "mypy-strict-modules.txt"
FLOOR = 12  # the size when the gate landed (2026-09-19); shrinking it means a module was dropped to go green


def _entries() -> list[str]:
    return [ln.strip() for ln in LIST.read_text().splitlines() if ln.strip() and not ln.startswith("#")]


def test_every_listed_module_exists():
    missing = [e for e in _entries() if not (ROOT / e).is_file()]
    assert missing == [], f"strict list names files that are gone: {missing}"


def test_no_module_is_listed_twice():
    entries = _entries()
    assert len(entries) == len(set(entries))


def test_the_list_never_shrinks_below_where_it_started():
    assert len(_entries()) >= FLOOR


def test_make_lint_and_ci_both_run_the_strict_set():
    assert "mypy-strict-modules.txt" in (ROOT / "Makefile").read_text()
    assert "mypy-strict-modules.txt" in (ROOT / ".github" / "workflows" / "lint.yml").read_text()
