"""A test that skips reads as a pass, so a pile of skips can hide a gutted suite.

Ten-plus tests here skip with "this book is not present in this checkout" (test_compose_lanes_distinct,
test_term_render, test_pronunciation_block ...). On a checkout that lacks the content they all vanish from CI with no
failure signal. CI sets PF_SKIP_BUDGET; if more tests skip than the budget, the run fails and `-rs` lists why. Local runs
are unaffected (no env var, no gate). Driven for real in a scratch project with the repo's own root conftest.py.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(tmp_path: Path, skips: int, budget: str | None) -> subprocess.CompletedProcess:
    shutil.copy(ROOT / "conftest.py", tmp_path / "conftest.py")
    body = (
        "import pytest\n"
        + "".join(f"\n@pytest.mark.skip(reason='not present {i}')\ndef test_s{i}():\n    pass\n" for i in range(skips))
        + "\ndef test_real():\n    assert True\n"
    )
    (tmp_path / "test_x.py").write_text(textwrap.dedent(body), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PF_SKIP_BUDGET"}
    if budget is not None:
        env["PF_SKIP_BUDGET"] = budget
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", str(tmp_path)],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
        timeout=120,
    )


def test_within_budget_passes(tmp_path):
    assert _run(tmp_path, skips=3, budget="3").returncode == 0


def test_over_budget_fails_and_says_why(tmp_path):
    out = _run(tmp_path, skips=4, budget="3")
    text = out.stdout + out.stderr
    assert out.returncode != 0
    assert "skip budget" in text.lower() and "4" in text and "3" in text
    assert "not present" in text, "-rs must list the reasons so the skips can be read"


def test_no_budget_means_no_gate(tmp_path):
    assert _run(tmp_path, skips=10, budget=None).returncode == 0


def test_ci_sets_the_budget_and_asks_for_skip_reasons():
    text = (ROOT / ".github" / "workflows" / "podcast-e2e.yml").read_text(encoding="utf-8")
    assert "PF_SKIP_BUDGET" in text and "-rs" in text
