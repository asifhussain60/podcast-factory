"""Tests for _etymology — content-driven selection + the accuracy gate (no LLM)."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

import _etymology as ety


def _make_book(tmp: Path, *, glossary: list[str], body: str) -> Path:
    bd = tmp / "content" / "Islamic" / "test-book"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(body, encoding="utf-8")
    entries = "\n".join(f"- transliteration: {g}\n  phonetic: {g}" for g in glossary)
    (bd / "_system" / "glossary.yml").write_text(
        "schema_version: 1\nentries:\n" + textwrap.indent(entries, ""), encoding="utf-8"
    )
    return bd


_GOOD = {
    "term": "nafs",
    "root": "ن-ف-س",
    "root_transliteration": "n-f-s",
    "root_phonetic": "NA-fa-sa",
    "meaning_en": "self, soul, breath",
    "morphology": "verbal noun",
    "semantic_field": "selfhood and breath",
    "derivatives": [{"term": "tanaffus", "phonetic": "ta-NAF-fus", "meaning_en": "breathing"}],
    "text_en": "The soul and the breath share one root. It ties inner self to the act of living.",
}


def test_norm_root_is_notation_agnostic() -> None:
    assert ety._norm_root("n-f-s") == ety._norm_root("nafs") == "nfs"
    assert ety._norm_root("ع-ل-م") == ""  # arabic drops to empty skeleton


def test_roots_compatible() -> None:
    assert ety._roots_compatible("nfs", "nfs")
    assert ety._roots_compatible("nfs", "nafasa")  # skeleton subsequence of fuller form
    assert not ety._roots_compatible("nfs", "slm")


def test_gather_candidates_ranks_by_frequency(tmp_path: Path) -> None:
    body = "The nafs and the nafs again; also sabr once. A long book title here."
    bd = _make_book(tmp_path, glossary=["nafs", "sabr", "Ihya al Ulum ad Din"], body=body)
    cands = ety.gather_candidate_terms(bd)
    terms = [t for t, _ in cands]
    assert terms[0] == "nafs"  # most frequent first
    assert "sabr" in terms
    # multi-word title is filtered out as non-concept-shaped
    assert not any("Ihya" in t for t in terms)


def test_gate_accepts_good_entry() -> None:
    ok, reason = ety.gate_entry(_GOOD, {}, {"confirmed": True, "root": "n-f-s"})
    assert ok, reason


def test_gate_rejects_missing_field() -> None:
    bad = {**_GOOD}
    bad.pop("root_phonetic")
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
    monkeypatch.setattr(ety, "load_morphology_reference", lambda *a, **k: {})
    monkeypatch.setattr(ety, "_resolve_corpus_terms", lambda *a, **k: {})

    good2 = {
        **_GOOD,
        "term": "salaam",
        "root": "س-ل-م",
        "root_transliteration": "s-l-m",
        "root_phonetic": "sa-LA-ma",
        "meaning_en": "peace, wholeness",
        "derivatives": [{"term": "islam", "phonetic": "is-LAM", "meaning_en": "submission"}],
    }

    def fake_gen(candidates, sample, book_dir, log):
        return [_GOOD, good2]

    def fake_ver(entries, book_dir, log):
        # confirm nafs, reject salaam (unconfirmed) -> salaam must be dropped
        return {
            "nafs": {"term": "nafs", "confirmed": True, "root": "n-f-s"},
            "salaam": {"term": "salaam", "confirmed": False, "root": ""},
        }

    report = ety.build_etymology_atoms(bd, log=lambda *a: None, generator=fake_gen, verifier=fake_ver, write=False)
    assert report["kept"] == 1
    assert report["entries"][0]["term"] == "nafs"
    assert report["dropped"] == 1


# ─── Morphology-corpus grounding (tmp DB built from the test excerpt) ────────
def _tiny_morphology_db(tmp_path: Path, monkeypatch) -> Path:
    import quranic_morphology as qm

    monkeypatch.setattr(qm, "_assert_expected", lambda counts: None)
    repo = Path(__file__).resolve().parents[3]
    db = tmp_path / "morphology.db"
    qm.build_db(db_path=db, source_path=repo / "tests" / "fixtures" / "morphology-excerpt.txt")
    return db


def test_load_morphology_reference_folds_lemmas_to_roots(tmp_path: Path, monkeypatch) -> None:
    db = _tiny_morphology_db(tmp_path, monkeypatch)
    ref = ety.load_morphology_reference(db)
    # lemma r~aHoma`n (رحمن -> "rhmn") and the root's own fold both key to root rhm.
    assert ref["rhmn"] == {"rhm"}
    assert ref["rhm"] == {"rhm"}
    # lemma Sabor (صبر) keys to its root fold "sbr".
    assert ref["sbr"] == {"sbr"}


def test_gate_veto_works_through_corpus_fold_keys(tmp_path: Path, monkeypatch) -> None:
    db = _tiny_morphology_db(tmp_path, monkeypatch)
    ref = ety.load_morphology_reference(db)
    entry = {**_GOOD, "term": "rahman", "root_transliteration": "r-h-m"}
    ok, _ = ety.gate_entry(entry, ref, {"confirmed": True, "root": "r-h-m"})
    assert ok
    wrong = {**_GOOD, "term": "rahman", "root_transliteration": "s-l-m"}
    ok, reason = ety.gate_entry(wrong, ref, {"confirmed": True, "root": "s-l-m"})
    assert not ok and "contradicts reference" in reason


def test_resolve_corpus_terms_grounds_unambiguous_terms_only(tmp_path: Path, monkeypatch) -> None:
    db = _tiny_morphology_db(tmp_path, monkeypatch)
    import lexicon_ingest

    monkeypatch.setattr(
        lexicon_ingest,
        "load_lexicon",
        lambda *a, **k: {"رحم": {"root_skel": "رحم", "lane_en": "had mercy; tenderness"}},
    )
    resolved = ety._resolve_corpus_terms([("rahman", 3), ("unknownword", 1)], db_path=db)
    assert set(resolved) == {"rahman"}
    rec = resolved["rahman"]
    assert rec["root_ar"] == "رحم" and rec["root_dashed"] == "ر-ح-م"
    assert {lem["lemma_bw"] for lem in rec["family"]} == {"r~aHoma`n", "r~aHiym"}
    assert rec["family"][0]["first_location"] in {"1:1:3", "1:1:4"}
    assert rec["lexicon"]["lane_en"].startswith("had mercy")
    grounding = ety._grounding_block(resolved)
    assert "ر-ح-م" in grounding and "Lane's Lexicon" in grounding


def test_to_atom_corpus_enrichment(tmp_path: Path, monkeypatch) -> None:
    db = _tiny_morphology_db(tmp_path, monkeypatch)
    import lexicon_ingest

    monkeypatch.setattr(lexicon_ingest, "load_lexicon", lambda *a, **k: {"رحم": {"lane_en": "mercy gloss"}})
    corpus = ety._resolve_corpus_terms([("rahman", 3)], db_path=db)["rahman"]
    entry = {
        **_GOOD,
        "term": "rahman",
        "root": "ر-ح-م",
        "root_transliteration": "r-h-m",
        "derivatives": [{"term": "rahman", "phonetic": "rah-MAN", "meaning_en": "the merciful"}],
    }
    atom = ety.to_atom(entry, "test-book", corpus=corpus)
    body = atom["body"]
    assert body["arabic"] == "رحم"  # corpus script, never model recall
    assert body["root"] == "ر-ح-م"  # canonical dashed root
    assert body["lexicon"] == {"lane_en": "mercy gloss"}
    assert body["derivatives"][0]["location"] == "1:1:3"  # real verse location
    # audio contract untouched
    assert body["root_phonetic"] and body["meaning_en"] and body["derivatives"][0]["term"]


def test_to_atom_without_corpus_matches_legacy_shape() -> None:
    atom = ety.to_atom(_GOOD, "test-book")
    assert atom["body"]["root"] == "ن-ف-س"
    assert atom["body"]["arabic"] == "ن-ف-س"  # falls back to the model's root script
    assert "lexicon" not in atom["body"]
    assert "location" not in atom["body"]["derivatives"][0]
