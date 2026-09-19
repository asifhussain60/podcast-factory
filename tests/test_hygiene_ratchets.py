"""The hygiene ratchets must be able to FAIL, and must only ever tighten.

Two counters guard the pipeline's worst silent-failure shapes: a subprocess call with no
`timeout=` (one hung ffmpeg or `claude -p` inside a chapter fan-out stalls a whole book)
and an `except` whose entire body is `pass`/`continue` (a swallowed failure ships a
defective book). The audit found 128 and 197 of them; fixing all at once was rejected as
too risky for thinly-tested code, so the count is frozen per file and may only fall.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_hygiene_ratchets as H  # noqa: E402


def _write(root: Path, rel: str, body: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_counts_subprocess_calls_without_a_timeout(tmp_path):
    _write(
        tmp_path,
        "scripts/a.py",
        "import subprocess\nsubprocess.run(['x'])\nsubprocess.check_output(['x'])\nsubprocess.run(['x'], timeout=5)\n",
    )
    assert H.scan(tmp_path)["scripts/a.py"]["subprocess_no_timeout"] == 2


def test_kwargs_expansion_is_given_the_benefit_of_the_doubt(tmp_path):
    _write(tmp_path, "scripts/a.py", "import subprocess\nsubprocess.run(['x'], **opts)\n")
    assert "scripts/a.py" not in H.scan(tmp_path)


def test_counts_silent_excepts_only(tmp_path):
    _write(
        tmp_path,
        "scripts/a.py",
        "try:\n    f()\nexcept ValueError:\n    pass\n"
        "for i in x:\n    try:\n        f()\n    except Exception:\n        continue\n"
        "try:\n    f()\nexcept OSError as e:\n    log(e)\n",
    )
    assert H.scan(tmp_path)["scripts/a.py"]["silent_except"] == 2


def test_test_trees_and_caches_are_out_of_scope(tmp_path):
    body = "import subprocess\nsubprocess.run(['x'])\n"
    _write(tmp_path, "scripts/podcast/tests/test_a.py", body)
    _write(tmp_path, "scripts/__pycache__/a.py", body)
    assert H.scan(tmp_path) == {}


def test_a_new_violation_in_a_clean_file_fails_the_check(tmp_path):
    _write(tmp_path, "scripts/a.py", "import subprocess\nsubprocess.run(['x'])\n")
    problems, _ = H.compare(H.scan(tmp_path), {})
    assert problems and "scripts/a.py" in problems[0]


def test_growth_past_the_baseline_fails_and_holding_passes(tmp_path):
    _write(tmp_path, "scripts/a.py", "import subprocess\nsubprocess.run(['x'])\nsubprocess.run(['y'])\n")
    current = H.scan(tmp_path)
    grew, _ = H.compare(current, {"scripts/a.py": {"subprocess_no_timeout": 1}})
    held, _ = H.compare(current, {"scripts/a.py": {"subprocess_no_timeout": 2}})
    assert grew and not held


def test_shrinking_passes_and_is_reported_so_the_baseline_can_be_lowered(tmp_path):
    _write(tmp_path, "scripts/a.py", "import subprocess\nsubprocess.run(['x'])\n")
    problems, shrunk = H.compare(H.scan(tmp_path), {"scripts/a.py": {"subprocess_no_timeout": 3}})
    assert not problems and shrunk


def test_a_file_that_became_clean_counts_as_shrinkage(tmp_path):
    problems, shrunk = H.compare({}, {"scripts/gone.py": {"silent_except": 4}})
    assert not problems and shrunk


def test_baseline_round_trips(tmp_path):
    _write(tmp_path, "scripts/a.py", "try:\n    f()\nexcept Exception:\n    pass\n")
    path = tmp_path / "baseline.json"
    H.write_baseline(H.scan(tmp_path), path)
    assert json.loads(path.read_text())["files"]["scripts/a.py"] == {"silent_except": 1}
    assert H.load_baseline(path) == {"scripts/a.py": {"silent_except": 1}}


def test_the_committed_baseline_covers_the_live_tree():
    """The gate as CI runs it: the real repo must not exceed its own frozen counts."""
    root = Path(__file__).resolve().parents[1]
    problems, _ = H.compare(H.scan(root), H.load_baseline(H.BASELINE))
    assert problems == []
