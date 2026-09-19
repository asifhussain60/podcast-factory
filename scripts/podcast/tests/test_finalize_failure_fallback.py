"""A failed finalize gate must tell the watchdog it needs a human.

`watch_orchestrator.sh` halts (instead of retrying up to 20 times) exactly when the failing
phase recorded a `manual_fallback`. The finalize step recorded none, so deterministic gate
failures (G13, G14 on isaf-al-talib) were relaunched "retry 3/20" until someone killed the
watchdog by hand. A gate that fails on this input fails on the same input again.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _finalize_failure import finalize_fallback  # noqa: E402

STDOUT = """\
PASS  [G1] structure
FAIL  [G13] arabic-script-in-chapters: 0/20 chapters carry Arabic
PASS  [G5] state shippable
FAIL  [G14] no AI-introduced Arabic: 3 span(s) in ch20
"""


def test_names_every_failing_gate_and_the_resume_command():
    text = finalize_fallback("isaf-al-talib", STDOUT)
    assert "G13" in text and "G14" in text
    assert "G1]" not in text and "G5" not in text  # passing gates are noise
    assert "orchestrate_book.py --resume isaf-al-talib" in text


def test_is_never_empty_even_when_the_validator_printed_no_fail_line():
    # An empty fallback is falsy to the watchdog, which then retries — the exact bug.
    assert finalize_fallback("slug", "").strip()
    assert finalize_fallback("slug", "Traceback (most recent call last): boom").strip()


def test_a_flood_of_failures_stays_readable():
    stdout = "\n".join(f"FAIL  [G{i}] {'x' * 300}" for i in range(1, 40))
    assert len(finalize_fallback("slug", stdout)) < 1500


def test_every_finalize_failure_records_a_manual_fallback():
    """The wiring, not just the helper: a new `failed` finalize update that forgets the
    fallback would silently bring the 20-retry loop back."""
    import ast

    src = (Path(__file__).resolve().parents[1] / "phases" / "post_chapter_driver.py").read_text()
    checked = 0
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "update_phase"):
            continue
        kw = {k.arg: k.value for k in node.keywords}
        is_finalize_failure = (
            isinstance(kw.get("phase"), ast.Constant)
            and kw["phase"].value == "finalize"
            and isinstance(kw.get("status"), ast.Constant)
            and kw["status"].value == "failed"
        )
        if is_finalize_failure:
            checked += 1
            assert "manual_fallback" in (ast.get_source_segment(src, node) or "")
    assert checked >= 1
