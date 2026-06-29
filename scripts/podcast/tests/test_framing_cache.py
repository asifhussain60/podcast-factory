#!/usr/bin/env python3
"""Phase 3 regression — F32 framing cache in per_chapter_pass.

A watchdog restart with an unchanged chapter + an already-authored framing must
SKIP the LLM re-authoring (and restore the authored framing that extract --force
overwrote). A changed chapter (sig mismatch) must re-author.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import phases.per_chapter as pc  # noqa: E402
from _convergence import ChapterOutcome  # noqa: E402

SLUG = "will-and-command"
EP = f"EP01-{SLUG}"


@pytest.fixture
def book(tmp_path):
    bd = tmp_path / "book"
    (bd / "chapters").mkdir(parents=True)
    (bd / "_system" / "episode-drafts" / EP).mkdir(parents=True)
    (bd / "episodes").mkdir(parents=True)
    (bd / "chapters" / f"ch01-{SLUG}.txt").write_text("chapter body v1", encoding="utf-8")
    return bd


def _wire(monkeypatch, book, *, author_calls: list):
    """Stub the subprocess steps + LLM + convergence so only the cache logic runs."""
    draft = book / "_system" / "episode-drafts" / EP
    template = "# 00-framing.md TEMPLATE (from extract --force)\n"

    def fake_run(cmd, *, cwd=None):
        # extract --force overwrites 00-framing.md with a template (the real behaviour)
        if str(pc.EXTRACT_SCRIPT) in cmd:
            (draft / "00-framing.md").write_text(template, encoding="utf-8")
        return (0, "", "")  # extract / lint / build all succeed (rc 0)

    monkeypatch.setattr(pc, "_run", fake_run)
    monkeypatch.setattr(pc, "_resolve_episode_id", lambda *a, **k: EP)

    def fake_author(bd, slug):
        author_calls.append(slug)
        (draft / "00-framing.md").write_text("AUTHORED framing\n", encoding="utf-8")

    monkeypatch.setattr(pc, "author_framing", fake_author)
    monkeypatch.setattr(pc, "converge_chapter",
                        lambda *a, **k: ChapterOutcome(SLUG, "SHIP-READY", 1, 0, 0, 0, 0))


class TestFramingCache:
    def test_first_run_authors_and_stamps_sig(self, book, monkeypatch):
        calls = []
        _wire(monkeypatch, book, author_calls=calls)
        pc.per_chapter_pass(book, SLUG)
        assert calls == [SLUG]  # authored
        draft = book / "_system" / "episode-drafts" / EP
        assert (draft / pc._FRAMING_SIG_NAME).is_file()
        assert (draft / "00-framing.md").read_text() == "AUTHORED framing\n"

    def test_restart_same_chapter_cache_hit(self, book, monkeypatch):
        calls = []
        _wire(monkeypatch, book, author_calls=calls)
        pc.per_chapter_pass(book, SLUG)            # first run authors
        assert calls == [SLUG]
        out = pc.per_chapter_pass(book, SLUG)      # restart: unchanged chapter
        assert calls == [SLUG]                      # NOT re-authored (cache hit)
        # authored framing restored despite extract --force template overwrite
        draft = book / "_system" / "episode-drafts" / EP
        assert (draft / "00-framing.md").read_text() == "AUTHORED framing\n"
        assert any("F32: framing cache hit" in n for n in out.notes)

    def test_changed_chapter_reauthors(self, book, monkeypatch):
        calls = []
        _wire(monkeypatch, book, author_calls=calls)
        pc.per_chapter_pass(book, SLUG)            # authors with sig of v1
        (book / "chapters" / f"ch01-{SLUG}.txt").write_text("chapter body v2 CHANGED", encoding="utf-8")
        pc.per_chapter_pass(book, SLUG)            # sig mismatch → re-author
        assert calls == [SLUG, SLUG]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
