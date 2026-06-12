"""Tests for normalize_m4a — fingerprint matching, swap detection, transcript pairing."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from normalize_m4a import apply_plan, plan_book  # noqa: E402


def _book(tmp_path: Path) -> Path:
    """Synthetic two-chapter book with sharply distinct vocabularies."""
    (tmp_path / "chapters").mkdir()
    (tmp_path / "episodes").mkdir()
    (tmp_path / "m4a").mkdir()
    (tmp_path / "chapters" / "ch01a-the-garden-of-truth.txt").write_text(
        "The garden of truth blooms with orchards, roses, gardeners and "
        "fountains. The gardener prunes the orchard so truth may blossom.",
        encoding="utf-8")
    (tmp_path / "chapters" / "ch02b-the-iron-mountain.txt").write_text(
        "The iron mountain stands above the forge. Miners, anvils and "
        "hammers shape the summit where iron meets stone.",
        encoding="utf-8")
    (tmp_path / "episodes" / "EP01-the-garden-of-truth.txt").write_text(
        "# The Garden Of Truth\nWalk the orchard; meet the gardener; "
        "every rose and fountain in order.", encoding="utf-8")
    (tmp_path / "episodes" / "EP02-the-iron-mountain.txt").write_text(
        "# The Iron Mountain\nClimb past the forge; the miners and the "
        "anvil; the summit verbatim.", encoding="utf-8")
    return tmp_path


def test_swapped_prefixes_detected_and_corrected(tmp_path):
    book = _book(tmp_path)
    # The operator's numeric prefixes are REVERSED (the real 2026-06-12 bug).
    (book / "m4a" / "01-The_iron_mountain_and_the_forge.m4a").write_bytes(b"x")
    (book / "m4a" / "02-Garden_of_truth_and_the_gardener.m4a").write_bytes(b"x")
    plan = plan_book(book)
    by_file = {e["file"]: e for e in plan}
    e1 = by_file["01-The_iron_mountain_and_the_forge.m4a"]
    e2 = by_file["02-Garden_of_truth_and_the_gardener.m4a"]
    assert e1["verdict"] == "SWAP" and e1["action"]["rename_to"] == "ch02b-the-iron-mountain.m4a"
    assert e2["verdict"] == "SWAP" and e2["action"]["rename_to"] == "ch01a-the-garden-of-truth.m4a"


def test_creative_title_without_prefix_matches(tmp_path):
    book = _book(tmp_path)
    (book / "m4a" / "Why_the_Gardener_Prunes_the_Orchard.m4a").write_bytes(b"x")
    plan = plan_book(book)
    assert len(plan) == 1
    assert plan[0]["verdict"] == "MATCH"
    assert plan[0]["claimed"] is None
    assert plan[0]["action"]["rename_to"] == "ch01a-the-garden-of-truth.m4a"


def test_uninformative_name_is_ambiguous_not_guessed(tmp_path):
    book = _book(tmp_path)
    (book / "m4a" / "Audio_Overview_v2.m4a").write_bytes(b"x")
    plan = plan_book(book)
    assert plan[0]["verdict"] == "AMBIGUOUS"
    assert plan[0]["action"] is None


def test_collision_with_existing_canonical_audio(tmp_path):
    book = _book(tmp_path)
    (book / "m4a" / "ch01a-the-garden-of-truth.m4a").write_bytes(b"x")
    (book / "m4a" / "The_rose_fountain_orchard_garden.m4a").write_bytes(b"x")
    plan = plan_book(book)
    assert len(plan) == 1  # canonical file itself is never planned
    assert plan[0]["verdict"] == "COLLISION"
    assert plan[0]["action"] is None


def test_transcript_in_export_dir_paired_by_text(tmp_path):
    book = _book(tmp_path)
    exp = book / "m4a" / "TurboScribe Export 999"
    exp.mkdir()
    (exp / "Some_Random_Export_Name.txt").write_text(
        "Welcome. We climb past the forge today, where the miners raise "
        "their hammers and the anvil rings beneath the iron mountain summit.",
        encoding="utf-8")
    plan = plan_book(book)
    assert plan[0]["kind"] == "transcript"
    assert plan[0]["action"]["rename_to"] == "transcripts/ch02b-the-iron-mountain.transcript.txt"


def test_canonical_stem_txt_moves_into_transcripts(tmp_path):
    book = _book(tmp_path)
    (book / "m4a" / "ch01a-the-garden-of-truth.txt").write_text(
        "any text", encoding="utf-8")
    plan = plan_book(book)
    assert plan[0]["evidence"] == "canonical-stem"
    assert plan[0]["action"]["rename_to"] == "transcripts/ch01a-the-garden-of-truth.transcript.txt"


def test_apply_renames_writes_ledger_and_is_idempotent(tmp_path):
    book = _book(tmp_path)
    (book / "m4a" / "01-The_iron_mountain_and_the_forge.m4a").write_bytes(b"x")
    exp = book / "m4a" / "TurboScribe Export 1"
    exp.mkdir()
    (exp / "export.txt").write_text(
        "The gardener walks the orchard among roses and fountains in the "
        "garden of truth.", encoding="utf-8")
    plan = plan_book(book)
    n = apply_plan(book, plan, log=lambda *_: None)
    assert n == 2
    assert (book / "m4a" / "ch02b-the-iron-mountain.m4a").exists()
    assert (book / "m4a" / "transcripts" / "ch01a-the-garden-of-truth.transcript.txt").exists()
    assert not exp.exists()  # emptied export dir removed
    ledger = json.loads((book / "m4a" / "_review" / "prefix-verification.json").read_text())
    assert len(ledger) == 2
    assert all(e["tool"] == "normalize_m4a" and e["ts"] for e in ledger)
    # Second pass: everything canonical, nothing to do.
    assert plan_book(book) == []


def test_dry_run_never_mutates(tmp_path):
    book = _book(tmp_path)
    (book / "m4a" / "01-The_iron_mountain_and_the_forge.m4a").write_bytes(b"x")
    plan_book(book)
    assert (book / "m4a" / "01-The_iron_mountain_and_the_forge.m4a").exists()
    assert not (book / "m4a" / "_review").exists()


def test_shared_boilerplate_does_not_drift_to_biggest_chapter(tmp_path):
    """Regression (2026-06-12): sibling episodes share debate-frame boilerplate
    (every framing opens the same way), and token-set overlap matched 7 of 20
    KNOWN-correct real transcripts to the largest chapter corpus. The
    trigram+IDF scorer must keep the chapter-specific verbatim phrases
    decisive and zero-weight phrases that appear in every framing."""
    book = _book(tmp_path)
    boiler = ("welcome to the debate tonight we examine the master and the "
              "disciple and the rigorous assertion of its tenth century author ")
    # Boilerplate appears in EVERY framing (as real framings do)...
    for ep in ("EP01-the-garden-of-truth", "EP02-the-iron-mountain"):
        f = book / "episodes" / f"{ep}.txt"
        f.write_text(boiler + f.read_text(), encoding="utf-8")
    # ...and a third chapter has by far the LARGEST corpus.
    (book / "chapters" / "ch03c-the-grand-assembly.txt").write_text(
        boiler * 40 + " assembly elders convene the grand council hall " * 20,
        encoding="utf-8")
    (book / "episodes" / "EP03-the-grand-assembly.txt").write_text(
        boiler + " the grand assembly convenes the elders", encoding="utf-8")
    # Transcript: mostly boilerplate + the garden chapter's verbatim phrases.
    (book / "m4a" / "garden_episode.m4a").write_bytes(b"x")
    exp = book / "m4a" / "drop"
    exp.mkdir()
    (exp / "garden_transcript.txt").write_text(
        boiler * 3 + " the gardener prunes the orchard so truth may blossom "
        "and every rose and fountain in order", encoding="utf-8")
    plan = plan_book(book)
    tx = [e for e in plan if e["kind"] == "transcript"][0]
    assert tx["evidence"] == "transcript-trigrams"
    assert tx["best"] == "ch01a-the-garden-of-truth"
    assert tx["verdict"] in ("MATCH", "SWAP")
