from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_voice import _adapt_chapter_body  # noqa: E402


def test_rearticulation_can_use_smaller_windows(tmp_path: Path) -> None:
    calls: list[int] = []

    def adapter(_title, window, _book_dir, _label, _log, **_kwargs):
        calls.append(len(window.split()))
        return window

    paragraph = " ".join(["word"] * 500)
    body = "\n\n".join([paragraph] * 5)

    _adapt_chapter_body(
        "Chapter",
        body,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=1000,
    )

    assert len(calls) == 3
    assert max(calls) <= 1000
