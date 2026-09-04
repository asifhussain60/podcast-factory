"""podcast-e2e.yml must run whenever a fixture the Python tests read changes.

Four TS<->Python mirror pairs (content-paths, peq-scores, anchor-key, vowelling)
plus the listener's search-fold and several book helpers are pinned by SHARED
fixture files under `plan-dashboard/scripts/lib/` and `listener/test/fixtures/`.
The TS side runs on lint.yml; the Python side runs on podcast-e2e.yml, whose path
filters listed `scripts/**` and `tests/**` but not the fixture directories. A
fixture-only commit therefore ran the TS half and never the Python half, and an
anchor-key divergence — the one that silently orphans every Composer edit — could
land with the mirror gate never firing.

This test derives the fixture set from the tests themselves (every `*.fixtures.json`
path a test module names) and asserts each is covered by BOTH trigger lists, using
GitHub's path-filter glob semantics (`*` stops at `/`, `**` does not).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "podcast-e2e.yml"
TEST_TREES = (REPO_ROOT / "tests", REPO_ROOT / "scripts" / "podcast" / "tests")

# A fixture reference as tests write it: `"plan-dashboard" / "scripts" / "lib" / "x.fixtures.json"`
# or a bare `listener/test/fixtures/x.fixtures.json` in a docstring. Both collapse to a
# repo-relative path once the quoting is stripped.
_SEGMENT_RE = re.compile(r'"([A-Za-z0-9_.\-]+)"\s*/\s*')
_PATH_RE = re.compile(r"(?:[A-Za-z0-9_\-]+/)+[A-Za-z0-9_\-]+\.fixtures\.json")


def _glob_to_re(glob: str) -> re.Pattern[str]:
    out = ""
    i = 0
    while i < len(glob):
        c = glob[i]
        if glob.startswith("**", i):
            out += ".*"
            i += 2
            continue
        if c == "*":
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        else:
            out += re.escape(c)
        i += 1
    return re.compile(f"^{out}$")


def _covered(path: str, globs: list[str]) -> bool:
    return any(_glob_to_re(g).match(path) for g in globs)


def _fixture_paths_named_by_tests() -> set[str]:
    found: set[str] = set()
    for tree in TEST_TREES:
        for module in tree.glob("test_*.py"):
            text = module.read_text(encoding="utf-8")
            for line in text.splitlines():
                if ".fixtures.json" not in line:
                    continue
                # Path(...) / "a" / "b" / "x.fixtures.json"  ->  a/b/x.fixtures.json
                segs = _SEGMENT_RE.findall(line)
                m = re.search(r'"([A-Za-z0-9_\-]+\.fixtures\.json)"', line)
                if segs and m:
                    found.add("/".join([*segs, m.group(1)]))
                    continue
                for m2 in _PATH_RE.finditer(line):
                    found.add(m2.group(0))
    return {p for p in found if (REPO_ROOT / p).is_file()}


def _trigger_paths() -> dict[str, list[str]]:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML parses the bare key `on` as boolean True.
    on = doc.get("on", doc.get(True))
    return {event: list(on[event]["paths"]) for event in ("pull_request", "push")}


def test_fixture_set_is_nonempty_and_spans_both_homes() -> None:
    fixtures = _fixture_paths_named_by_tests()
    assert any(p.startswith("plan-dashboard/scripts/lib/") for p in fixtures), fixtures
    assert any(p.startswith("listener/test/fixtures/") for p in fixtures), fixtures


@pytest.mark.parametrize("event", ["pull_request", "push"])
def test_every_python_read_fixture_triggers_the_python_suite(event: str) -> None:
    globs = _trigger_paths()[event]
    uncovered = sorted(p for p in _fixture_paths_named_by_tests() if not _covered(p, globs))
    assert uncovered == [], (
        f"podcast-e2e.yml `{event}` path filters do not cover fixtures the Python tests read: {uncovered}"
    )


def test_glob_semantics_match_github_path_filters() -> None:
    assert _covered("scripts/podcast/x.py", ["scripts/**"])
    assert _covered("plan-dashboard/scripts/lib/a.fixtures.json", ["plan-dashboard/scripts/lib/**"])
    assert not _covered("plan-dashboard/scripts/lib/a.json", ["plan-dashboard/*"])
    assert not _covered("listener/test/fixtures/a.json", ["scripts/**", "tests/**"])
