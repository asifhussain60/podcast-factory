from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_voice import _adapt_chapter_body, _iter_prose_windows  # noqa: E402


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


def test_arabic_dense_paragraphs_split_by_sentence() -> None:
    sentences = [f"Sentence {i} names رَحْمَةٌ and ٱللَّٰهُ and حَمْدٌ." for i in range(1, 16)]
    paragraph = " ".join(sentences)

    windows = _iter_prose_windows(paragraph, target_words=500)

    assert len(windows) > 1
    assert all(window.count("رَحْمَةٌ") <= 8 for window in windows)


def test_stitched_rearticulation_must_preserve_chapter_level_detail(tmp_path: Path) -> None:
    def adapter(_title, window, _book_dir, _label, _log, **_kwargs):
        return " ".join(window.split()[:70])

    paragraph = " ".join(f"word{i}" for i in range(100))
    body = "\n\n".join([paragraph] * 3)

    new_body, record = _adapt_chapter_body(
        "Chapter",
        body,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=100,
    )

    assert new_body == body
    assert record["status"] == "reverted"
    assert record["windows_kept"] == 0
    assert record["pre_assembly_windows_kept"] == 3
    assert any("below detail floor" in gate for gate in record["assembly_gates"])


def test_stitched_rearticulation_rejects_duplicate_join_artifacts(tmp_path: Path) -> None:
    repeated = " ".join(f"detail{i}" for i in range(60))

    def adapter(_title, _window, _book_dir, _label, _log, **_kwargs):
        return repeated + "\n\n" + repeated

    body = "\n\n".join([" ".join(f"source{j}_{i}" for i in range(120)) for j in range(2)])

    new_body, record = _adapt_chapter_body(
        "Chapter",
        body,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=120,
    )

    assert new_body == body
    assert record["status"] == "reverted"
    assert any("duplicated adjacent paragraphs" in gate for gate in record["assembly_gates"])


def test_partial_stitched_rearticulation_names_the_continuity_review(tmp_path: Path) -> None:
    def adapter(_title, window, _book_dir, label, _log, **_kwargs):
        if label.endswith("part-02"):
            return ""
        return window

    body = "\n\n".join([" ".join(f"word{j}_{i}" for i in range(80)) for j in range(3)])

    _new_body, record = _adapt_chapter_body(
        "Chapter",
        body,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=80,
    )

    assert record["status"] == "partial"
    assert record["windows_kept"] == 2
    assert any("review voice continuity" in warning for warning in record["warnings"])


def test_arabic_runs_are_protected_from_the_model_and_restored_before_gates(tmp_path: Path) -> None:
    source = "The word رَحْمَةٌ opens the matter and the word ٱللَّٰهُ completes it."

    def adapter(_title, window, _book_dir, _label, _log, **_kwargs):
        assert "رَحْمَةٌ" not in window
        assert "[[ARABIC_001]]" in window
        assert "[[ARABIC_002]]" in window
        return "The matter opens with [[ARABIC_001]], and it is completed by [[ARABIC_002]]."

    new_body, record = _adapt_chapter_body(
        "Chapter",
        source,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=100,
    )

    assert record["status"] == "adapted"
    assert "رَحْمَةٌ" in new_body
    assert "ٱللَّٰهُ" in new_body
    assert "[[ARABIC_" not in new_body


def test_quote_only_windows_are_preserved_without_model_call(tmp_path: Path) -> None:
    source = "> يَٓأَيُّهَا ٱلَّذِينَ آمَنُوا۟\n>\n> O you who believe!"

    def adapter(*_args, **_kwargs):
        raise AssertionError("quote-only windows should not be sent to the model")

    new_body, record = _adapt_chapter_body(
        "Chapter",
        source,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=100,
    )

    assert new_body == source
    assert record["status"] == "adapted"
    assert record["windows_kept"] == 1
    assert record["windows_source_preserved"] == 1
    assert any("protected source artifact" in warning for warning in record["warnings"])


def test_structural_artifacts_are_split_out_and_preserved(tmp_path: Path) -> None:
    calls: list[str] = []
    body = "\n\n".join(
        [
            "First prose paragraph names Allah and explains the opening idea.",
            "### ILAH",
            "A vs THE",
            "![](images/example.jpg)",
            "Second prose paragraph continues the explanation with the same teaching intact.",
        ]
    )

    def adapter(_title, window, _book_dir, _label, _log, **_kwargs):
        calls.append(window)
        assert "### ILAH" not in window
        assert "A vs THE" not in window
        assert "![](images/example.jpg)" not in window
        assert "[[ARTIFACT_001]]" in window
        assert "[[ARTIFACT_002]]" in window
        assert "[[ARTIFACT_003]]" in window
        return window

    new_body, record = _adapt_chapter_body(
        "Chapter",
        body,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=100,
    )

    assert new_body == body
    assert len(calls) == 1
    assert record["status"] == "adapted"
    assert record["windows_source_preserved"] == 0


def test_dropping_an_arabic_placeholder_still_reverts(tmp_path: Path) -> None:
    source = "The word رَحْمَةٌ opens the matter and the word ٱللَّٰهُ completes it."

    def adapter(_title, _window, _book_dir, _label, _log, **_kwargs):
        return "The matter opens with [[ARABIC_001]], and then it completes."

    new_body, record = _adapt_chapter_body(
        "Chapter",
        source,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=100,
    )

    assert record["status"] == "reverted"
    assert new_body == source
    assert any("Arabic runs dropped" in gate for gate in record["gates"])


def test_failed_window_can_be_repaired_before_reverting(tmp_path: Path) -> None:
    source = "The word رَحْمَةٌ opens the matter and the word ٱللَّٰهُ completes it."
    repair_calls: list[tuple[str, str, list[str]]] = []

    def adapter(_title, _window, _book_dir, _label, _log, **_kwargs):
        return "The matter opens with [[ARABIC_001]], and then it completes."

    def repair(_title, source_window, candidate, gates, _book_dir, _label, _log, **_kwargs):
        repair_calls.append((source_window, candidate, gates))
        return "The matter opens with [[ARABIC_001]], and it is completed by [[ARABIC_002]]."

    new_body, record = _adapt_chapter_body(
        "Chapter",
        source,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=100,
        repair_fn=repair,
    )

    assert record["status"] == "adapted"
    assert record["windows_repaired"] == 1
    assert len(repair_calls) == 1
    assert "[[ARABIC_002]]" in repair_calls[0][0]
    assert "[[ARABIC_002]]" not in repair_calls[0][1]
    assert any("[[ARABIC_002]]" in gate for gate in repair_calls[0][2])
    assert any("Arabic runs dropped" in gate for gate in repair_calls[0][2])
    assert "رَحْمَةٌ" in new_body
    assert "ٱللَّٰهُ" in new_body


def test_accepted_windows_are_cached_and_failed_windows_are_retried(tmp_path: Path) -> None:
    calls: list[str] = []

    def first_adapter(_title, window, _book_dir, label, _log, **_kwargs):
        calls.append(label)
        if label.endswith("part-02"):
            return ""
        return window

    body = "\n\n".join([" ".join(f"word{j}_{i}" for i in range(80)) for j in range(3)])
    _adapt_chapter_body(
        "Chapter",
        body,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        first_adapter,
        noun="rearticulate",
        window_words=80,
    )
    assert calls == ["rearticulate-01-part-01", "rearticulate-01-part-02", "rearticulate-01-part-03"]

    calls.clear()

    def second_adapter(_title, window, _book_dir, label, _log, **_kwargs):
        calls.append(label)
        return window

    _new_body, record = _adapt_chapter_body(
        "Chapter",
        body,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        second_adapter,
        noun="rearticulate",
        window_words=80,
    )

    assert calls == ["rearticulate-01-part-02"]
    assert record["windows_cached"] == 2
    assert record["status"] == "adapted"


def test_cached_window_that_passes_is_not_repaired(tmp_path: Path) -> None:
    calls: list[str] = []
    repair_calls: list[str] = []

    def adapter(_title, window, _book_dir, label, _log, **_kwargs):
        calls.append(label)
        return window

    body = "\n\n".join([" ".join(f"word{j}_{i}" for i in range(80)) for j in range(2)])
    _adapt_chapter_body(
        "Chapter",
        body,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=80,
    )
    calls.clear()

    def repair(_title, _source_window, _candidate, _gates, _book_dir, label, _log, **_kwargs):
        repair_calls.append(label)
        return ""

    _new_body, record = _adapt_chapter_body(
        "Chapter",
        body,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=80,
        repair_fn=repair,
    )

    assert calls == []
    assert repair_calls == []
    assert record["windows_cached"] == 2
    assert record["windows_repaired"] == 0
    assert record["status"] == "adapted"


def test_repeated_model_process_failures_disable_fresh_calls(tmp_path: Path) -> None:
    calls: list[str] = []

    def adapter(_title, _window, _book_dir, label, _log, **_kwargs):
        calls.append(label)
        raise RuntimeError("claude -p rc=1")

    body = "\n\n".join([" ".join(f"word{j}_{i}" for i in range(80)) for j in range(5)])
    new_body, record = _adapt_chapter_body(
        "Chapter",
        body,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=80,
    )

    assert new_body == body
    assert calls == ["rearticulate-01-part-01", "rearticulate-01-part-02", "rearticulate-01-part-03"]
    assert record["status"] == "reverted"
    assert record["model_failures"] == 3
    assert record["fresh_calls_disabled"] is True
    assert any("fresh model calls disabled" in warning for warning in record["warnings"])


def test_window_cache_is_fingerprint_scoped_to_source_text(tmp_path: Path) -> None:
    calls: list[str] = []

    def adapter(_title, window, _book_dir, label, _log, **_kwargs):
        calls.append(label)
        return window

    body = "\n\n".join([" ".join(f"word{j}_{i}" for i in range(80)) for j in range(2)])
    changed = body.replace("word0_0", "changed0_0")

    _adapt_chapter_body(
        "Chapter",
        body,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=80,
    )
    calls.clear()
    _adapt_chapter_body(
        "Chapter",
        changed,
        tmp_path,
        "rearticulate-01",
        lambda *_args: None,
        adapter,
        noun="rearticulate",
        window_words=80,
    )

    assert calls == ["rearticulate-01-part-01"]


def test_rearticulate_can_decline_to_write_partial_output(tmp_path: Path, monkeypatch) -> None:
    import rearticulate_chapter as rc

    book = tmp_path / "book"
    (book / "book").mkdir(parents=True)
    (book / "_system").mkdir()
    book_md = book / "book" / "book.md"
    book_md.write_text("# T\n\n## A Chapter\n\nOriginal body.\n", encoding="utf-8")

    def fake_run_pass(*_args, **_kwargs):
        return "# T\n\n## A Chapter\n\nPartial body.\n", [{"title": "A Chapter", "status": "partial"}]

    monkeypatch.setattr(rc, "_run_pass", fake_run_pass)
    result = rc.rearticulate(book, "a chapter", write_partial=False, log=lambda *_: None)

    assert result["record"]["status"] == "partial"
    assert "Original body." in book_md.read_text(encoding="utf-8")
    assert not (book / "_system" / "composer-edits.json").exists()
