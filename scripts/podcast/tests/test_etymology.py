"""Tests for _etymology — content-driven selection + the accuracy gate (no LLM)."""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

import _etymology as ety  # noqa: E402


def _make_book(tmp: Path, *, glossary: list[str], body: str) -> Path:
    bd = tmp / "content" / "Islamic" / "test-book"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(body, encoding="utf-8")
    entries = "\n".join(f"- transliteration: {g}\n  phonetic: {g}" for g in glossary)
    (bd / "_system" / "glossary.yml").write_text(
        "schema_version: 1\nentries:\n" + textwrap.indent(entries, ""), encoding="utf-8")
    return bd


_GOOD = {
    "term": "nafs", "root": "ن-ف-س", "root_transliteration": "n-f-s",
    "root_phonetic": "NA-fa-sa", "meaning_en": "self, soul, breath",
    "morphology": "verbal noun", "semantic_field": "selfhood and breath",
    "derivatives": [{"term": "tanaffus", "phonetic": "ta-NAF-fus", "meaning_en": "breathing"}],
    "text_en": "The soul and the breath share one root. It ties inner self to the act of living.",
}


def test_norm_root_is_notation_agnostic() -> None:
    assert ety._norm_root("n-f-s") == ety._norm_root("nafs") == "nfs"
    assert ety._norm_root("ع-ل-م") == ""  # arabic drops to empty skeleton


def test_roots_compatible() -> None:
    assert ety._roots_compatible("nfs", "nfs")
    assert ety._roots_compatible("nfs", "nafasa")   # skeleton subsequence of fuller form
    assert not ety._roots_compatible("nfs", "slm")


def test_gather_candidates_ranks_by_frequency(tmp_path: Path) -> None:
    body = "The nafs and the nafs again; also sabr once. A long book title here."
    bd = _make_book(tmp_path, glossary=["nafs", "sabr", "Ihya al Ulum ad Din"], body=body)
    cands = ety.gather_candidate_terms(bd)
    terms = [t for t, _ in cands]
    assert terms[0] == "nafs"          # most frequent first
    assert "sabr" in terms
    # multi-word title is filtered out as non-concept-shaped
    assert not any("Ihya" in t for t in terms)


def test_gate_accepts_good_entry() -> None:
    ok, reason = ety.gate_entry(_GOOD, {}, {"confirmed": True, "root": "n-f-s"})
    assert ok, reason


def test_gate_rejects_missing_field() -> None:
    bad = {**_GOOD}; bad.pop("root_phonetic")
    ok, reason = ety.gate_entry(bad, {}, {"confirmed": True, "root": "n-f-s"})
    assert not ok and "root_phonetic" in reason


def test_gate_reference_veto_blocks_wrong_root() -> None:
    # term_index says nafs -> nfs; a claimed root of slm must be vetoed.
    entry = {**_GOOD, "root_transliteration": "s-l-m"}
    ok, reason = ety.gate_entry(entry, {"nafs": {"nfs"}}, {"confirmed": True, "root": "s-l-m"})
    assert not ok and "contradicts reference" in reason


def test_gate_reference_confirms_matching_root() -> None:
    ok, _ = ety.gate_entry(_GOOD, {"nafs": {"nfs"}}, {"confirmed": True, "root": "n-f-s"})
    assert ok


def test_gate_rejects_unconfirmed_verdict() -> None:
    ok, reason = ety.gate_entry(_GOOD, {}, {"confirmed": False, "root": ""})
    assert not ok and "did not confirm" in reason


def test_gate_rejects_verifier_disagreement() -> None:
    ok, reason = ety.gate_entry(_GOOD, {}, {"confirmed": True, "root": "s-l-m"})
    assert not ok and "disagrees" in reason


def test_to_atom_id_keyed_by_root() -> None:
    atom = ety.to_atom(_GOOD, "test-book")
    assert atom["id"] == "etymology:nfs"
    assert atom["type"] == "etymology"
    assert atom["body"]["root_phonetic"] == "NA-fa-sa"
    assert atom["body"]["derivatives"][0]["term"] == "tanaffus"


def test_build_pipeline_keeps_only_gated(tmp_path: Path, monkeypatch) -> None:
    body = "nafs nafs nafs. salaam salaam."
    bd = _make_book(tmp_path, glossary=["nafs", "salaam"], body=body)

    # Hermetic: isolate from the developer's real corpus. Both the reuse filter
    # (_existing_etymology_roots) and the reference veto (load_term_index) read
    # global knowledge-base state; without stubbing, an already-ingested `nafs`
    # atom makes the pipeline drop it as a reuse and the test flakes by machine.
    monkeypatch.setattr(ety, "_existing_etymology_roots", lambda: set())
    monkeypatch.setattr(ety, "load_term_index", lambda *a, **k: {})

    good2 = {**_GOOD, "term": "salaam", "root": "س-ل-م", "root_transliteration": "s-l-m",
             "root_phonetic": "sa-LA-ma", "meaning_en": "peace, wholeness",
             "derivatives": [{"term": "islam", "phonetic": "is-LAM", "meaning_en": "submission"}]}

    def fake_gen(candidates, sample, book_dir, log):
        return [_GOOD, good2]

    def fake_ver(entries, book_dir, log):
        # confirm nafs, reject salaam (unconfirmed) -> salaam must be dropped
        return {"nafs": {"term": "nafs", "confirmed": True, "root": "n-f-s"},
                "salaam": {"term": "salaam", "confirmed": False, "root": ""}}

    report = ety.build_etymology_atoms(bd, log=lambda *a: None, generator=fake_gen,
                                       verifier=fake_ver, write=False)
    assert report["kept"] == 1
    assert report["entries"][0]["term"] == "nafs"
    assert report["dropped"] == 1
