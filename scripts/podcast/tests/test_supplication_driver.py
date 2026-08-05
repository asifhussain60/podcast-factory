#!/usr/bin/env python3
"""Driver-level pins — the step ledger, the review halt, and the CLI.

Runs the whole lane against a temporary content root with the two model calls
and the PDF renderer stubbed out, so the step machinery is exercised with zero
Azure, Anthropic, or chromium spend.

The behaviour that matters most here: `run` STOPS at the review halt and does
not translate until `approve` is given. That halt is the only thing standing
between a bad segmentation and a full translation bill.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _paths  # noqa: E402
from supplication import driver, intake, llm, ocr, render, state  # noqa: E402
from supplication.schema import SourceLine, SourceRecord, Unit, UnitsDoc  # noqa: E402

LINES = [
    "وَ مِنَ اللَّيْلِ فَتَهَجَّدْ بِهِ",
    "نَافِلَةً لَكَ",
    "فَاِنَّ الْجَنَّةَ هِيَ الْمَأْوَى",
    "يَا اَرْحَمَ الرَّاحِمِينَ",
]

SLUG = "test-dua"


@pytest.fixture
def lane(tmp_path, monkeypatch):
    """A lane rooted in tmp_path, with OCR / model / renderer stubbed."""
    monkeypatch.setattr(_paths, "CONTENT_ROOT", tmp_path / "content")

    def fake_ocr(book_dir, *, slug, source_language, pdf_path):
        rec = SourceRecord(
            slug=slug,
            source_language=source_language,
            source_pdf=str(pdf_path),
            lines=[SourceLine(id=f"p1l{i + 1}", page=1, line=i + 1, text=t) for i, t in enumerate(LINES)],
            ocr={"pages": 1},
        )
        rec.write(ocr.record_path(book_dir))
        return rec

    def fake_segment(record, **kw):
        return UnitsDoc(
            slug=record.slug,
            source_language=record.source_language,
            source_digest=record.digest,
            units=[Unit(n=1, line_ids=["p1l1", "p1l2"]), Unit(n=2, line_ids=["p1l3"]), Unit(n=3, line_ids=["p1l4"])],
        )

    translated = {"called": 0}

    def fake_translate(doc, record, **kw):
        translated["called"] += 1
        for u in doc.units:
            u.english = f"English {u.n}"
        return doc

    rendered = {}

    def fake_render(book_dir, doc, record, out=None):
        out = out or render.output_path(book_dir, doc.slug)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"%PDF-1.4 stub")
        rendered["path"] = out
        return out

    monkeypatch.setattr(ocr, "run", fake_ocr)
    monkeypatch.setattr(llm, "segment", fake_segment)
    monkeypatch.setattr(llm, "translate", fake_translate)
    monkeypatch.setattr(render, "run", fake_render)

    book_dir = intake.run(SLUG, source_language="ar", title_en="Test", create_branch=False)
    state.mark_done(book_dir, "intake")
    st = state.load(book_dir)
    src = book_dir / "_system" / "source" / "src.pdf"
    src.write_bytes(b"%PDF stub")
    st["source_pdf"] = str(src.relative_to(book_dir))
    state.save(book_dir, st)
    return {"dir": book_dir, "translated": translated, "rendered": rendered}


class TestIntake:
    def test_routes_into_the_supplications_bucket(self, lane):
        assert lane["dir"].parent.name == "Supplications"
        assert lane["dir"].name == SLUG

    def test_branch_name_is_bucket_grouped(self, lane):
        assert intake.branch_for(SLUG) == f"Supplications/{SLUG}"

    def test_config_declares_pdf_only(self, lane):
        cfg = (lane["dir"] / "_system" / "series-config.yaml").read_text()
        assert "source_language: ar" in cfg
        assert "episodes: false" in cfg and "audio: false" in cfg

    def test_refuses_to_clobber_an_existing_slug(self, lane):
        from supplication.schema import SupplicationError

        with pytest.raises(SupplicationError, match="already exists"):
            intake.run(SLUG, source_language="ar", create_branch=False)

    def test_rejects_an_unknown_metadata_field(self, tmp_path, monkeypatch):
        from supplication.schema import SupplicationError

        monkeypatch.setattr(_paths, "CONTENT_ROOT", tmp_path / "content")
        with pytest.raises(SupplicationError, match="unknown metadata"):
            intake.run("x", source_language="ar", meta={"nope": "v"}, create_branch=False)


class TestRunHaltsForReview:
    def test_run_stops_at_review_without_translating(self, lane):
        assert driver.cmd_run(_args(slug=SLUG)) == 0
        st = state.load(lane["dir"])
        assert st["step"] == "review"
        assert st["step_status"] == "halted"
        assert "segment" in st["completed_steps"]
        # The point of the halt: no translation spend has happened.
        assert lane["translated"]["called"] == 0
        assert "translate" not in st["completed_steps"]

    def test_rerunning_stays_halted(self, lane):
        driver.cmd_run(_args(slug=SLUG))
        driver.cmd_run(_args(slug=SLUG))
        assert lane["translated"]["called"] == 0

    def test_approve_then_run_completes_every_step(self, lane):
        driver.cmd_run(_args(slug=SLUG))
        assert driver.cmd_approve(_args(slug=SLUG)) == 0
        assert driver.cmd_run(_args(slug=SLUG)) == 0

        st = state.load(lane["dir"])
        assert state.next_step(st) is None
        assert st["completed_steps"] == list(state.STEPS)
        assert lane["translated"]["called"] == 1
        assert lane["rendered"]["path"].is_file()

    def test_approve_renumbers_units_after_review_edits(self, lane):
        driver.cmd_run(_args(slug=SLUG))
        p = lane["dir"] / "units.json"
        doc = UnitsDoc.read(p)
        # Simulate a human MERGE of units 2 and 3.
        doc.units = [doc.units[0], Unit(n=99, line_ids=["p1l3", "p1l4"])]
        doc.write(p)

        assert driver.cmd_approve(_args(slug=SLUG)) == 0
        assert [u.n for u in UnitsDoc.read(p).units] == [1, 2]

    def test_approve_refuses_a_review_edit_that_drops_a_line(self, lane):
        driver.cmd_run(_args(slug=SLUG))
        p = lane["dir"] / "units.json"
        doc = UnitsDoc.read(p)
        doc.units = doc.units[:2]  # p1l4 orphaned
        doc.write(p)

        assert driver.cmd_verify(_args(slug=SLUG, require_english=False)) == 1
        with pytest.raises(Exception, match="integrity gate FAILED"):
            driver.cmd_approve(_args(slug=SLUG))
        # And the halt is still in place — the run cannot slip past it.
        assert state.load(lane["dir"])["step_status"] == "halted"


class TestStateLedgerIsolation:
    def test_lane_writes_its_own_state_file_only(self, lane):
        driver.cmd_run(_args(slug=SLUG))
        sysdir = lane["dir"] / "_system"
        assert (sysdir / "supplication-state.json").is_file()
        # The podcast pipeline's state file is never created by this lane.
        assert not (sysdir / "orchestrator-state.json").exists()

    def test_state_records_the_lane_name(self, lane):
        assert state.load(lane["dir"])["lane"] == "supplication"


def _args(**kw):
    return type("A", (), kw)()
