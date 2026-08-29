"""Tests for phases/series_plan.py::phase_0g_register.

Regression coverage for a repo-surgeon AU-A3 finding: the function wrote to a
pre-restructure cross-book path (content/podcast/.skill/registry.md, deleted in
the 2026-06-04 content restructure) guarded by a silent `if not exists: return`,
so it had been a no-op for every book scaffolded since. framework.md INVARIANT 6
requires each chapter's title mirrored into the book's own `_system/registry.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))
if str(_SCRIPTS_PODCAST / "phases") not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST / "phases"))

from phases.series_plan import phase_0g_register  # noqa: E402
from validate_registry import parse_table, validate_one  # noqa: E402


def _make_book(tmp_path: Path, *, with_meta: bool = True, with_registry: bool = False) -> Path:
    book_dir = tmp_path / "some-book"
    (book_dir / "chapter-contracts").mkdir(parents=True)
    (book_dir / "chapters").mkdir(parents=True)
    (book_dir / "_system").mkdir(parents=True)
    if with_meta:
        (book_dir / "meta.yml").write_text(yaml.dump({"title": "Some Book", "author": "Some Author"}), encoding="utf-8")
    for ep, slug in [(1, "opening"), (2, "closing")]:
        (book_dir / "chapter-contracts" / f"{slug}.yml").write_text(
            yaml.dump(
                {
                    "episode_number": ep,
                    "slug": slug,
                    "title": slug.title(),
                    "source_type": "book-chapter",
                }
            ),
            encoding="utf-8",
        )
        (book_dir / "chapters" / f"ch{ep:02d}-{slug}.txt").write_text("body", encoding="utf-8")
    if with_registry:
        (book_dir / "_system" / "registry.md").write_text(
            "# Podcast Episode Registry — Some Book\n\n"
            "Author: **Some Author**.\n\n"
            "| EP# | Title | Slug | Source Type | Status | Date Started | NotebookLM URL |\n"
            "|-----|-------|------|-------------|--------|--------------|----------------|\n",
            encoding="utf-8",
        )
    return book_dir


class TestPhase0gRegister:
    def test_writes_to_per_book_path_not_cross_book_path(self, tmp_path):
        book_dir = _make_book(tmp_path, with_registry=True)
        phase_0g_register(book_dir)
        assert (book_dir / "_system" / "registry.md").exists()
        assert not (tmp_path / "content").exists()

    def test_creates_missing_registry_from_meta(self, tmp_path):
        book_dir = _make_book(tmp_path, with_registry=False)
        phase_0g_register(book_dir)
        text = (book_dir / "_system" / "registry.md").read_text(encoding="utf-8")
        assert "Some Book" in text
        assert "Some Author" in text
        assert "| opening |" in text
        assert "| closing |" in text

    def test_rows_pass_validate_registry(self, tmp_path):
        book_dir = _make_book(tmp_path, with_registry=True)
        phase_0g_register(book_dir)
        findings = validate_one(book_dir / "_system" / "registry.md")
        assert findings == []

    def test_ep_column_has_no_ep_prefix(self, tmp_path):
        # A prior bug wrote "EP01" into the EP# cell; validate_registry's R2
        # requires a bare integer (`raw.isdigit()`).
        book_dir = _make_book(tmp_path, with_registry=True)
        phase_0g_register(book_dir)
        rows, header_found = parse_table((book_dir / "_system" / "registry.md").read_text(encoding="utf-8"))
        assert header_found
        assert {r["EP#"] for r in rows} == {"01", "02"}

    def test_status_is_a_valid_enum_value(self, tmp_path):
        # A prior bug wrote "drafted", which is not in validate_registry's
        # ALLOWED_STATUS set ({draft, challenger-pending, ready, generated, archived}).
        book_dir = _make_book(tmp_path, with_registry=True)
        phase_0g_register(book_dir)
        rows, _ = parse_table((book_dir / "_system" / "registry.md").read_text(encoding="utf-8"))
        assert {r["Status"] for r in rows} == {"draft"}

    def test_idempotent_on_repeated_calls(self, tmp_path):
        book_dir = _make_book(tmp_path, with_registry=True)
        phase_0g_register(book_dir)
        phase_0g_register(book_dir)
        rows, _ = parse_table((book_dir / "_system" / "registry.md").read_text(encoding="utf-8"))
        assert len(rows) == 2

    def test_no_contracts_dir_is_a_noop(self, tmp_path):
        book_dir = tmp_path / "empty-book"
        (book_dir / "_system").mkdir(parents=True)
        (book_dir / "_system" / "registry.md").write_text("# stub\n", encoding="utf-8")
        phase_0g_register(book_dir)  # must not raise
        assert (book_dir / "_system" / "registry.md").read_text(encoding="utf-8") == "# stub\n"

    def test_orphaned_contract_without_a_chapter_file_is_skipped(self, tmp_path):
        # spiritual-ethos carries contracts left behind by an earlier
        # re-segmentation whose slug no longer has a chapter file — they
        # reuse the episode_number of the contract that replaced them, and
        # mirroring both into the registry produced duplicate EP# rows.
        book_dir = _make_book(tmp_path, with_registry=True)
        (book_dir / "chapter-contracts" / "orphaned.yml").write_text(
            yaml.dump(
                {
                    "episode_number": 1,
                    "slug": "orphaned",
                    "title": "Orphaned",
                    "source_type": "book-chapter",
                }
            ),
            encoding="utf-8",
        )
        phase_0g_register(book_dir)
        rows, _ = parse_table((book_dir / "_system" / "registry.md").read_text(encoding="utf-8"))
        assert {r["Slug"] for r in rows} == {"opening", "closing"}
        assert validate_one(book_dir / "_system" / "registry.md") == []
