#!/usr/bin/env python3
"""Tranche 2 pins — the supplication lane's schema, integrity gate, and firewall.

The headline test is `TestVerbatimGate::test_mutating_a_source_line_fails_the_run`
— the plan's Verification item 5. It mutates the OCR record after the fact and
proves the gate refuses the run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from supplication import gates  # noqa: E402
from supplication.schema import (  # noqa: E402
    SourceLine,
    SourceRecord,
    SupplicationError,
    Unit,
    UnitsDoc,
    derive_source,
    refrain_units,
    render_payload,
    validate_source_language,
)

AR_LINES = [
    "وَ مِنَ اللَّيْلِ فَتَهَجَّدْ بِهِ",
    "نَافِلَةً لَكَ",
    "فَاِنَّ الْجَنَّةَ هِيَ الْمَأْوَى",
    "يَا اَرْحَمَ الرَّاحِمِينَ",
]


def make_record(lines=None, lang="ar") -> SourceRecord:
    lines = lines or AR_LINES
    return SourceRecord(
        slug="test-supplication",
        source_language=lang,
        source_pdf="src.pdf",
        lines=[SourceLine(id=f"p1l{i + 1}", page=1, line=i + 1, text=t) for i, t in enumerate(lines)],
    )


def make_doc(record: SourceRecord, groups=None, *, english=True) -> UnitsDoc:
    groups = groups or [["p1l1", "p1l2"], ["p1l3"], ["p1l4"]]
    return UnitsDoc(
        slug=record.slug,
        source_language=record.source_language,
        source_digest=record.digest,
        units=[
            Unit(n=i + 1, line_ids=g, english=f"English for unit {i + 1}" if english else "")
            for i, g in enumerate(groups)
        ],
    )


class TestSchema:
    def test_source_language_is_never_inferred(self):
        assert validate_source_language("ar") == "ar"
        assert validate_source_language("ur") == "ur"
        for bad in (None, "", "en", "fa", "arabic"):
            with pytest.raises(SupplicationError):
                validate_source_language(bad)

    def test_derive_source_joins_lines_verbatim(self):
        rec = make_record()
        got = derive_source(["p1l1", "p1l2"], rec.by_id())
        assert got == f"{AR_LINES[0]} {AR_LINES[1]}"
        # Tashkeel survives the round trip untouched — no normalization anywhere.
        assert "ّ" in got  # shadda

    def test_derive_source_rejects_unknown_ids(self):
        with pytest.raises(SupplicationError, match="unknown OCR line id"):
            derive_source(["p9l9"], make_record().by_id())

    def test_digest_changes_when_any_line_changes(self):
        a = make_record().digest
        b = make_record(AR_LINES[:-1] + ["مختلف"]).digest
        assert a != b

    def test_record_read_rejects_a_tampered_file(self, tmp_path):
        p = tmp_path / "source-record.json"
        make_record().write(p)
        d = json.loads(p.read_text())
        d["lines"][0]["text"] = "tampered"
        p.write_text(json.dumps(d, ensure_ascii=False))
        with pytest.raises(SupplicationError, match="digest mismatch"):
            SourceRecord.read(p)

    def test_record_write_refuses_to_overwrite(self, tmp_path):
        p = tmp_path / "source-record.json"
        make_record().write(p)
        with pytest.raises(SupplicationError, match="immutable"):
            make_record().write(p)


class TestVerbatimGate:
    def test_a_clean_document_passes_every_check(self):
        rec = make_record()
        rep = gates.verify(make_doc(rec), rec)
        assert rep.passed, rep.summary()
        assert set(rep.checks) == {
            "G-SUP-1 digest",
            "G-SUP-2 resolvable",
            "G-SUP-3 coverage",
            "G-SUP-4 order",
            "G-SUP-5 verbatim",
            "G-SUP-6 translated",
        }

    def test_mutating_a_source_line_fails_the_run(self):
        """Plan Verification #5 — the gate's reason for existing.

        A unit is segmented against one OCR record; the record is then altered
        (as a bad re-OCR, a hand edit, or a compromised model write would).
        The gate must refuse, not silently render the altered text.
        """
        rec = make_record()
        doc = make_doc(rec)  # carries the ORIGINAL digest

        mutated = make_record(["MUTATED"] + AR_LINES[1:])
        rep = gates.verify(doc, mutated)

        assert not rep.passed
        assert rep.checks["G-SUP-1 digest"] is False
        assert any("does not match" in f for f in rep.failures)
        with pytest.raises(SupplicationError, match="integrity gate FAILED"):
            gates.assert_ok(doc, mutated)

    def test_a_dropped_line_fails_coverage(self):
        rec = make_record()
        doc = make_doc(rec, [["p1l1", "p1l2"], ["p1l3"]])  # p1l4 never used
        rep = gates.verify(doc, rec)
        assert not rep.passed
        assert rep.checks["G-SUP-3 coverage"] is False
        assert any("never used" in f for f in rep.failures)

    def test_a_duplicated_line_fails_coverage(self):
        rec = make_record()
        doc = make_doc(rec, [["p1l1", "p1l2"], ["p1l3"], ["p1l3", "p1l4"]])
        rep = gates.verify(doc, rec)
        assert rep.checks["G-SUP-3 coverage"] is False

    def test_reordered_units_fail_order(self):
        rec = make_record()
        doc = make_doc(rec, [["p1l3"], ["p1l1", "p1l2"], ["p1l4"]])
        rep = gates.verify(doc, rec)
        assert rep.checks["G-SUP-4 order"] is False

    def test_noncontiguous_line_ids_fail_order(self):
        rec = make_record()
        doc = make_doc(rec, [["p1l1", "p1l3"], ["p1l2"], ["p1l4"]])
        rep = gates.verify(doc, rec)
        assert rep.checks["G-SUP-4 order"] is False

    def test_untranslated_units_fail_only_when_english_is_required(self):
        rec = make_record()
        doc = make_doc(rec, english=False)
        assert not gates.verify(doc, rec, require_english=True).passed
        assert gates.verify(doc, rec, require_english=False).passed


class TestDerivedRefrains:
    """A refrain is arithmetic, not a model's opinion.

    The first version of this asked the segmentation model to flag refrains.
    That was an unvalidated judgment call — a model that over-flags speckles the
    page with highlight and nothing downstream could tell a real refrain from a
    guess. These tests pin the replacement: a unit is a refrain if and only if
    its exact source text appears again elsewhere in the same document.
    """

    def test_nothing_is_marked_when_every_source_is_distinct(self):
        rec = make_record()
        doc = make_doc(rec, [["p1l1"], ["p1l2"], ["p1l3"], ["p1l4"]])
        assert refrain_units(doc, rec) == set()

    def test_a_repeated_source_marks_every_occurrence(self):
        # p1l2 and p1l4 are given identical text, so both units are refrains —
        # and the two that are unique are not.
        rec = make_record([AR_LINES[0], "يَا اَرْحَمَ الرَّاحِمِينَ", AR_LINES[2], "يَا اَرْحَمَ الرَّاحِمِينَ"])
        doc = make_doc(rec, [["p1l1"], ["p1l2"], ["p1l3"], ["p1l4"]])
        assert refrain_units(doc, rec) == {2, 4}

    def test_comparison_is_on_source_not_english(self):
        # Identical English, different source → NOT a refrain. The source is the
        # immutable ground truth; the translation is downstream of it.
        rec = make_record()
        doc = make_doc(rec, [["p1l1"], ["p1l2"], ["p1l3"], ["p1l4"]])
        for u in doc.units:
            u.english = "the same sentence"
        assert refrain_units(doc, rec) == set()

    def test_a_merge_during_review_updates_the_marking(self):
        # Two units whose sources are identical are refrains; merging one of
        # them into its neighbour makes its text unique, so the marking clears
        # itself with no extra step. This is why deriving beats storing.
        rec = make_record([AR_LINES[0], "مُكَرَّر", AR_LINES[2], "مُكَرَّر"])
        doc = make_doc(rec, [["p1l1"], ["p1l2"], ["p1l3"], ["p1l4"]])
        assert refrain_units(doc, rec) == {2, 4}

        merged = make_doc(rec, [["p1l1", "p1l2"], ["p1l3"], ["p1l4"]])
        assert refrain_units(merged, rec) == set()

    def test_refrain_is_not_stored_on_the_unit(self):
        # The field is gone from the persisted shape entirely — there is nowhere
        # for a stale or model-authored value to live.
        rec = make_record()
        doc = make_doc(rec)
        assert "refrain" not in doc.units[0].to_dict()
        assert not hasattr(doc.units[0], "refrain")

    def test_payload_refrain_flags_come_from_the_derivation(self):
        rec = make_record([AR_LINES[0], "مُكَرَّر", AR_LINES[2], "مُكَرَّر"])
        doc = make_doc(rec, [["p1l1"], ["p1l2"], ["p1l3"], ["p1l4"]])
        flags = [u["refrain"] for u in render_payload(doc, rec)["units"]]
        assert flags == [False, True, False, True]


class TestRenderPayload:
    def test_source_comes_from_the_record_not_units_json(self):
        """The integrity invariant, stated as a test.

        Even if units.json somehow carried a `source` field, the payload must be
        built from the OCR record — there is no code path from units.json to the
        source column.
        """
        rec = make_record()
        doc = make_doc(rec)
        payload = render_payload(doc, rec)
        assert payload["units"][0]["source"] == f"{AR_LINES[0]} {AR_LINES[1]}"
        assert payload["units"][2]["source"] == AR_LINES[3]
        assert payload["source_language"] == "ar"

    def test_payload_matches_the_renderer_contract(self):
        rec = make_record()
        payload = render_payload(make_doc(rec), rec)
        assert set(payload) >= {"slug", "source_language", "units"}
        for u in payload["units"]:
            assert set(u) == {"n", "source", "english", "refrain"}

    def test_unknown_metadata_fields_are_dropped(self):
        rec = make_record()
        doc = make_doc(rec)
        doc.meta = {"type": "Munajat", "smuggled": "should not render"}
        payload = render_payload(doc, rec)
        assert payload["meta"] == {"type": "Munajat"}


class TestTranslationScriptGuard:
    def test_arabic_script_in_english_is_detected(self):
        from supplication.llm import _has_source_script

        assert _has_source_script("O my Lord يَا رَبِّ", "ar")
        assert _has_source_script("اے میرے پروردگار", "ur")
        assert not _has_source_script("O Most Merciful of the merciful.", "ar")


class TestRegressionFirewall:
    """The lane must not reach into the podcast pipeline. Enforced by grep.

    A test rather than a convention: the whole justification for a sibling lane
    is that it cannot perturb the podcast path, and that claim needs teeth.
    """

    FORBIDDEN = (
        "orchestrate_book",
        "build_episode_txt",
        "validate_ship_ready",
        "_translation_edition",
        "_translation_contract",
        "_book_pipeline_v2",
        "_augment_registry",
        "_progress",
        "publish_to_library",
        "render-book-pdf",
        "book-print.css",
    )

    @pytest.mark.parametrize("module", sorted(p.name for p in (SCRIPTS_PODCAST / "supplication").glob("*.py")))
    def test_no_podcast_pipeline_imports(self, module):
        src = (SCRIPTS_PODCAST / "supplication" / module).read_text(encoding="utf-8")
        code = "\n".join(
            line for line in src.splitlines() if line.strip().startswith(("import ", "from ")) or "subprocess" in line
        )
        hits = [name for name in self.FORBIDDEN if name in code]
        assert not hits, f"supplication/{module} reaches into the podcast pipeline: {hits}"

    def test_lane_declares_no_audio_deliverables(self):
        from supplication.intake import SERIES_CONFIG_TEMPLATE

        cfg = SERIES_CONFIG_TEMPLATE.format(profile="islamic_supplication", slug="x", lang="ar")
        for off in ("episodes: false", "audio: false", "slide_decks: false", "video: false"):
            assert off in cfg
        assert "pdf: true" in cfg

    def test_lane_steps_never_collide_with_podcast_phase_names(self):
        from _progress import PHASES
        from supplication.state import STEPS

        podcast_phases = {p if isinstance(p, str) else getattr(p, "name", str(p)) for p in PHASES}
        assert not (set(STEPS) & podcast_phases)
