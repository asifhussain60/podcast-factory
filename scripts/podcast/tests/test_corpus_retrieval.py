"""Tests for _corpus_retrieval — per-passage relevance + within-book non-repetition."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

from _corpus_retrieval import (  # noqa: E402
    RetrievalIndex,
    UsedLedger,
    attribute_used,
    select_relevant,
)

_ATOMS = [
    {"id": "a1", "type": "doctrine",
     "body": {"text_en": "Divine justice governs the decree of the Creator over all beings.",
              "topic_tags": ["justice", "tawhid"]}},
    {"id": "a2", "type": "quote",
     "body": {"text_en": "The believer stands in prayer through the long nights, fasting by day.",
              "speaker": "Ahmad"}},
    {"id": "a3", "type": "quran",
     "body": {"surah": 14, "ayah": 7,
              "text_en": "If you are grateful, I will surely increase you in favor."}},
]


def test_relevance_picks_the_related_atom_first() -> None:
    idx = RetrievalIndex(_ATOMS)
    picks = idx.select("A chapter about divine justice and the Creator's decree over all beings.",
                       k=3, threshold=0.05)
    assert picks, "expected at least one relevant atom"
    assert picks[0].id == "a1"
    assert picks[0].score >= picks[-1].score  # best-first


def test_different_passages_pick_different_atoms() -> None:
    idx = RetrievalIndex(_ATOMS)
    justice = {p.id for p in idx.select("divine justice decree Creator beings", k=1, threshold=0.05)}
    prayer = {p.id for p in idx.select("standing in prayer through the nights, fasting", k=1, threshold=0.05)}
    assert justice == {"a1"}
    assert prayer == {"a2"}


def test_threshold_drops_unrelated_atoms() -> None:
    idx = RetrievalIndex(_ATOMS)
    # A passage sharing no meaningful vocabulary with any atom.
    picks = idx.select("quarterly revenue forecast spreadsheet logistics", k=3, threshold=0.10)
    assert picks == []


def test_topic_tag_boosts_relevance() -> None:
    picks = select_relevant(_ATOMS, "themes of justice", k=1, threshold=0.05)
    assert picks and picks[0].id == "a1"


def test_quran_ref_overlap_matches() -> None:
    picks = select_relevant(_ATOMS, "as taught in Q14:7 about gratitude", k=1, threshold=0.05)
    assert picks and picks[0].id == "a3"


def test_exclude_ids_enforces_non_repetition() -> None:
    idx = RetrievalIndex(_ATOMS)
    first = idx.select("divine justice Creator decree beings", k=3, threshold=0.05)
    assert first
    again = idx.select("divine justice Creator decree beings", k=3, threshold=0.05,
                       exclude_ids={p.id for p in first})
    assert {p.id for p in again}.isdisjoint({p.id for p in first})


def test_atoms_without_id_are_dropped() -> None:
    idx = RetrievalIndex([{"type": "doctrine", "body": {"text_en": "no id here justice"}}])
    assert idx.select("justice", k=3, threshold=0.0) == []


def test_attribute_used_keys_on_actual_overlap() -> None:
    note = "A connected teaching: divine justice governs the decree over all beings."
    used = attribute_used(note, _ATOMS)
    assert "a1" in used          # note echoes a1's distinctive vocabulary
    assert "a2" not in used      # prayer/fasting atom not reflected in the note


def test_used_ledger_round_trip(tmp_path: Path) -> None:
    led = UsedLedger(tmp_path).reset()
    led.record(["a1", "a2"])
    assert led.used() == {"a1", "a2"}
    # Reloaded from disk (cross-surface accumulation within a book).
    again = UsedLedger(tmp_path).load()
    assert again.used() == {"a1", "a2"}
    again.record(["a3"])
    assert UsedLedger(tmp_path).load().used() == {"a1", "a2", "a3"}


def test_used_ledger_reset_keeps_reruns_idempotent(tmp_path: Path) -> None:
    UsedLedger(tmp_path).reset().record(["a1"])
    # A fresh run resets in memory, so it is not starved by the prior run.
    fresh = UsedLedger(tmp_path).reset()
    assert fresh.used() == set()
