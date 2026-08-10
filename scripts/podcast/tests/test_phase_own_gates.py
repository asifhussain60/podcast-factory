#!/usr/bin/env python3
"""The gates added on 2026-08-09 for the phases that checked nothing about their own work.

Twenty-four of the twenty-nine phases had no gate of their own: the review layer only
re-verified that the five gated phases' outputs still existed, so a phase could finish
having produced nothing and the only evidence was the absence of a crash.

Each gate below was validated against all 22 books on disk before being added — run over
the books that ACTUALLY COMPLETED that phase, every one reports zero failures. These
tests pin the two halves of that: the healthy shape passes, and the specific broken shape
the gate exists to catch fails.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _phase_review as pr  # noqa: E402
from _progress import initial_state, read_state, write_state  # noqa: E402


class _Book(unittest.TestCase):
    def setUp(self) -> None:
        self._td = TemporaryDirectory()
        self.book = Path(self._td.name) / "bk"
        (self.book / "_system").mkdir(parents=True)
        for d in ("chapter-contracts", "chapters", "episodes", "book", "audits", "slide-decks"):
            (self.book / d).mkdir()
        write_state(self.book, initial_state("bk", "books"))

    def tearDown(self) -> None:
        self._td.cleanup()

    def _state(self, **kw):
        s = read_state(self.book)
        s.update(kw)
        write_state(self.book, s)


class ContractsHaveChapterFilesTests(_Book):
    """0d writes contracts AND the chapter text each one describes."""

    def _contract(self, slug):
        (self.book / "chapter-contracts" / f"{slug}.yml").write_text("title: t\n", encoding="utf-8")

    def _chapter(self, n, slug):
        (self.book / "chapters" / f"ch{n:02d}-{slug}.txt").write_text("prose\n", encoding="utf-8")

    def test_a_matched_set_passes(self):
        for i, s in enumerate(("alpha", "beta"), start=1):
            self._contract(s)
            self._chapter(i, s)
        ok, note = pr.gate_contracts_have_chapter_files(self.book)
        self.assertTrue(ok, note)

    def test_a_contract_with_no_chapter_file_fails(self):
        self._contract("alpha")
        self._chapter(1, "alpha")
        self._contract("orphan")
        ok, note = pr.gate_contracts_have_chapter_files(self.book)
        self.assertFalse(ok)
        self.assertIn("orphan", note)

    def test_no_contracts_at_all_fails(self):
        ok, note = pr.gate_contracts_have_chapter_files(self.book)
        self.assertFalse(ok)
        self.assertIn("produced nothing", note)


class EnrichmentRecordedTests(_Book):
    def test_a_written_log_passes(self):
        (self.book / "_system" / "enrichment-log.md").write_text("enriched 3 chapters\n", encoding="utf-8")
        self.assertTrue(pr.gate_enrichment_recorded(self.book)[0])

    def test_a_missing_log_fails(self):
        self.assertFalse(pr.gate_enrichment_recorded(self.book)[0])

    def test_an_empty_log_fails(self):
        (self.book / "_system" / "enrichment-log.md").write_text("", encoding="utf-8")
        self.assertFalse(pr.gate_enrichment_recorded(self.book)[0])


class AuditBundleWrittenTests(_Book):
    def test_audit_files_pass(self):
        (self.book / "audits" / "a-bundle-audit.md").write_text("x\n", encoding="utf-8")
        self.assertTrue(pr.gate_audit_bundle_written(self.book)[0])

    def test_an_empty_audits_dir_fails(self):
        ok, note = pr.gate_audit_bundle_written(self.book)
        self.assertFalse(ok)
        self.assertIn("swept nothing", note)

    def test_it_reads_disk_rather_than_the_state_key(self):
        """`kitab-al-riyad` completed 0g in May 2026, before `audit_outcomes` existed.

        A gate keyed on that state field would report a healthy book broken, which is
        exactly the kind of false positive that teaches a reader to skim past reviews.
        """
        (self.book / "audits" / "legacy-audit.md").write_text("x\n", encoding="utf-8")
        s = read_state(self.book)
        s["phases"]["0g"] = {"status": "completed"}  # no audit_outcomes key at all
        write_state(self.book, s)
        self.assertTrue(pr.gate_audit_bundle_written(self.book)[0])


class PerChapterGatesTests(_Book):
    def _contract(self, slug):
        (self.book / "chapter-contracts" / f"{slug}.yml").write_text("title: t\n", encoding="utf-8")

    def _episode(self, slug):
        (self.book / "episodes" / f"EP-{slug}.txt").write_text("framing\n", encoding="utf-8")

    def _completed(self, slugs):
        s = read_state(self.book)
        s["phases"]["per-chapter"] = {"status": "running", "completed_slugs": list(slugs)}
        write_state(self.book, s)

    def test_one_episode_per_chapter_passes(self):
        for s in ("a", "b"):
            self._contract(s)
            self._episode(s)
        self.assertTrue(pr.gate_every_chapter_has_an_episode(self.book)[0])

    def test_a_short_lane_fails(self):
        self._contract("a")
        self._contract("b")
        self._episode("a")
        ok, note = pr.gate_every_chapter_has_an_episode(self.book)
        self.assertFalse(ok)
        self.assertIn("short", note)

    def test_completed_slugs_covering_every_contract_passes(self):
        self._contract("a")
        self._contract("b")
        self._completed(["a", "b"])
        self.assertTrue(pr.gate_completed_slugs_cover_contracts(self.book)[0])

    def test_a_chapter_never_attempted_fails(self):
        """The shape the loop's own failure handling cannot catch.

        A chapter that failed is recorded in `failed_slugs` and keeps the phase from
        completing. A chapter never ATTEMPTED — dropped from the pending list, skipped
        by a resume that mis-read prior state — never failed, never shipped, and was
        never mentioned anywhere.
        """
        self._contract("a")
        self._contract("ghost")
        self._completed(["a"])
        ok, note = pr.gate_completed_slugs_cover_contracts(self.book)
        self.assertFalse(ok)
        self.assertIn("ghost", note)
        self.assertIn("never shipped and never failed", note)

    def test_a_book_with_no_contracts_is_not_judged(self):
        self.assertTrue(pr.gate_every_chapter_has_an_episode(self.book)[0])
        self.assertTrue(pr.gate_completed_slugs_cover_contracts(self.book)[0])


class SlideDecksTests(_Book):
    def test_decks_present_passes(self):
        (self.book / "slide-decks" / "ch01-deck.txt").write_text("deck\n", encoding="utf-8")
        self.assertTrue(pr.gate_slide_decks_present(self.book)[0])

    def test_an_empty_deck_dir_fails(self):
        self.assertFalse(pr.gate_slide_decks_present(self.book)[0])


class RenderedPdfTests(_Book):
    def test_a_real_pdf_passes(self):
        (self.book / "book" / "book.pdf").write_bytes(b"%PDF-1.4\n" + b"x" * 20_000)
        ok, note = pr.gate_rendered_pdf_present(self.book)
        self.assertTrue(ok, note)

    def test_no_pdf_fails(self):
        ok, note = pr.gate_rendered_pdf_present(self.book)
        self.assertFalse(ok)
        self.assertIn("produced nothing", note)

    def test_an_essentially_empty_pdf_fails(self):
        """A failed render can leave a structurally valid but empty PDF behind.

        A presence check waves that through and a reader concludes the edition printed.
        """
        (self.book / "book" / "book.pdf").write_bytes(b"%PDF-1.4 stub\n")
        ok, note = pr.gate_rendered_pdf_present(self.book)
        self.assertFalse(ok)
        self.assertIn("under 10 kB", note)

    def test_the_largest_real_pdf_is_the_one_reported(self):
        (self.book / "book" / "small.pdf").write_bytes(b"%PDF\n" + b"x" * 11_000)
        (self.book / "book" / "big.pdf").write_bytes(b"%PDF\n" + b"x" * 40_000)
        ok, note = pr.gate_rendered_pdf_present(self.book)
        self.assertTrue(ok)
        self.assertIn("big.pdf", note)


class PublicationStatusTests(_Book):
    def test_a_flipped_status_passes(self):
        self._state(status="published")
        self.assertTrue(pr.gate_publication_status_flipped(self.book)[0])

    def test_an_unflipped_status_fails(self):
        self._state(status="draft")
        ok, note = pr.gate_publication_status_flipped(self.book)
        self.assertFalse(ok)
        self.assertIn("draft", note)

    def test_publish_completing_over_an_unflipped_status_is_the_whole_point(self):
        # Publish's entire job is one field. "Completed" without it is the exact shape
        # of a write that silently matched no rows.
        self._state(status="draft")
        self.assertFalse(pr.gate_publication_status_flipped(self.book)[0])


class NoGateCrashesOnAnEmptyBookTests(_Book):
    """Every gate must return a verdict on a bare directory rather than raising.

    A gate that crashes is recorded as neither pass nor omission, which is right — but
    crashing on an empty book would make every early phase of every new book noisy.
    """

    def test_every_declared_gate_survives_an_empty_book(self):
        for phase, gates in pr.OWN_GATES.items():
            for gid, name, fn in gates:
                with self.subTest(gate=gid):
                    try:
                        passed, note = fn(self.book)
                    except Exception as e:  # noqa: BLE001 - the assertion is the report
                        self.fail(f"{gid} ({phase}/{name}) raised {type(e).__name__}: {e}")
                    self.assertIsInstance(passed, bool)
                    self.assertIsInstance(note, str)
                    self.assertTrue(note.strip(), f"{gid} returned an empty note")


if __name__ == "__main__":
    unittest.main()
