"""Glossary rebuild must never destroy human curation.

Phase 0c calls `build_glossary.py --force` on EVERY refine run of an
islamic_scholarly book (_authoring/_refine.py). The rebuild re-derives rows from
_phonetics.md, which carries only term/transliteration/phonetic/snippet — so any
field a human owns (the Arabic script they confirmed, the term decisions they
made) is unrecoverable if the rebuild drops it. Worse, `fill_glossary_arabic.py`
then re-populates `arabic_script` by LLM, which makes the loss look like a
healthy file.

These tests pin the preservation contract: every other writer in the glossary
lane already merges and respects `decided_by`; this one must too.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from build_glossary import (  # noqa: E402
    _CURATED_FIELDS,
    emit_glossary_yaml,
    merge_curation,
    read_existing_curation,
)

CURATED_ROWS = [
    {
        "term": "tawhid",
        "transliteration": "tawhid",
        "phonetic": "tow-HEED",
        "first_seen_snippet": "the doctrine of oneness",
        "arabic_script": "توحيد",
        "audio_phonetic": "tow-HEED",
        "decision": "keep",
        "decided_by": "asif",
        "decided_at": "2026-07-19",
        "english_override": "divine oneness",
    }
]


def _write(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "glossary.yml"
    p.write_text(emit_glossary_yaml(rows), encoding="utf-8")
    return p


def test_read_existing_curation_round_trips_every_curated_field(tmp_path: Path) -> None:
    curated = read_existing_curation(_write(tmp_path, CURATED_ROWS))
    assert "tawhid" in curated, "keyed by the romanized phonetic anchor"
    entry = curated["tawhid"]
    for field in ("arabic_script", "decision", "decided_by", "decided_at", "english_override"):
        assert entry[field] == CURATED_ROWS[0][field], f"{field} must survive the read"


def test_absent_file_yields_nothing_to_preserve(tmp_path: Path) -> None:
    assert read_existing_curation(tmp_path / "nope.yml") == {}


def test_rebuild_preserves_curation_that_phonetics_md_cannot_supply(tmp_path: Path) -> None:
    prior = read_existing_curation(_write(tmp_path, CURATED_ROWS))
    # What parse_phonetics_md would hand back on a fresh run: no curated fields.
    fresh = [
        {
            "term": "tawhid",
            "transliteration": "tawhid",
            "phonetic": "tow-HEED",
            "first_seen_snippet": "the doctrine of oneness",
        }
    ]

    merged, preserved = merge_curation(fresh, prior)

    assert preserved == 1
    assert merged[0]["arabic_script"] == "توحيد", "the confirmed Arabic script survives"
    assert merged[0]["decided_by"] == "asif", "the human decision marker survives"
    assert merged[0]["english_override"] == "divine oneness"
    # And it round-trips back out to disk.
    assert "توحيد" in emit_glossary_yaml(merged)
    assert 'decided_by: "asif"' in emit_glossary_yaml(merged)


def test_a_fresh_value_never_overwrites_a_curated_one(tmp_path: Path) -> None:
    prior = read_existing_curation(_write(tmp_path, CURATED_ROWS))
    fresh = [
        {
            "term": "tawhid",
            "transliteration": "tawhid",
            "phonetic": "tow-HEED",
            "first_seen_snippet": "x",
            "audio_phonetic": "MACHINE-GUESS",
        }
    ]
    merged, _ = merge_curation(fresh, prior)
    assert merged[0]["audio_phonetic"] == "MACHINE-GUESS", (
        "a value already present on the fresh row is kept; merge only FILLS gaps"
    )


def test_a_new_term_is_unaffected_by_prior_curation(tmp_path: Path) -> None:
    prior = read_existing_curation(_write(tmp_path, CURATED_ROWS))
    fresh = [
        {
            "term": "barakah",
            "transliteration": "barakah",
            "phonetic": "BA-ra-kah",
            "first_seen_snippet": "blessing",
        }
    ]
    merged, preserved = merge_curation(fresh, prior)
    assert preserved == 0
    assert not merged[0].get("decided_by"), "no curation leaks onto an unrelated term"


def test_every_curated_field_is_covered_by_the_reader() -> None:
    """A field added to the emitter must also be preserved, or it silently dies."""
    rows = [
        {
            "term": "t",
            "transliteration": "t",
            "phonetic": "p",
            "first_seen_snippet": "s",
            **{f: f"val-{f}" for f in _CURATED_FIELDS},
        }
    ]
    curated = read_existing_curation_from_text(emit_glossary_yaml(rows))
    for field in _CURATED_FIELDS:
        assert curated.get("t", {}).get(field) == f"val-{field}", f"{field} not preserved"


def read_existing_curation_from_text(text: str) -> dict:
    """Helper: run the parser over an in-memory document."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "g.yml"
        p.write_text(text, encoding="utf-8")
        return read_existing_curation(p)
