from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rearticulate_chapter import _WINDOW_WORDS, _adapter, timeout_for_window  # noqa: E402


def test_rearticulate_timeout_scales_with_window_complexity() -> None:
    short = "Plain English sentence. " * 40
    long = "Plain English sentence. " * 1400
    arabic_heavy = ("Plain English sentence. " * 1400) + (" الله " * 300)

    assert timeout_for_window(short) == 180
    assert timeout_for_window(short) < timeout_for_window(long)
    assert timeout_for_window(long) < timeout_for_window(arabic_heavy)


def test_rearticulate_timeout_has_a_ceiling() -> None:
    huge = ("Plain English sentence. " * 10000) + (" الله " * 5000)

    assert timeout_for_window(huge) == 600


def test_rearticulate_adapter_runs_claude_without_tools_or_workspace_context(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict] = []

    def fake_run(prompt: str, **kwargs):
        calls.append({"prompt": prompt, **kwargs})
        return 0, "Articulated prose.", ""

    monkeypatch.setattr("rearticulate_chapter._run_claude_p", fake_run)
    monkeypatch.setattr("rearticulate_chapter._source_language", lambda _book_dir: "ar")

    out = _adapter("A Chapter", "Plain English sentence. " * 40, tmp_path, "ch01", lambda *_: None)

    assert out == "Articulated prose."
    assert calls
    assert calls[0]["phase"] == "rearticulate"
    assert calls[0]["tools"] == ""
    assert calls[0]["safe_mode"] is True
    assert calls[0]["no_chrome"] is True
    assert calls[0]["no_session_persistence"] is True
    assert calls[0]["effort"] == "low"
    assert "Return only the requested transformed prose" in calls[0]["system_prompt"]


def test_rearticulate_windows_stay_small_enough_for_cli_text_transform() -> None:
    assert _WINDOW_WORDS == 300
