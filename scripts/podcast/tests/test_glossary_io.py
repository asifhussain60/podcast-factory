"""The one glossary reader and the one writer.

This file is the regression test for a bug that was LIVE until 2026-08-02: the
glossary format had forked, three of the five real glossaries parsed as ZERO
entries by two of the three parsers that read them, and one of those readers
writes its result back. A 161-entry glossary could be replaced by an empty one
behind a log line reading "non-blocking".

The three properties worth pinning, in order of what they cost when broken:

  1. Every real glossary in the repo parses to a non-empty list. A parser that
     returns [] on a full file is worse than one that raises.
  2. A round-trip is LOSSLESS. Both emitters used to carry a fixed field
     allow-list, so `annotation_class` — added later, elsewhere — was destroyed
     by the act of reading and rewriting. An unclassified term is annotated once
     per CHAPTER rather than once per book, so the loss reaches the printed page.
  3. A round-trip is IDEMPOTENT, or every future glossary diff is noise.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _glossary_io import dump_glossary, load_glossary, save_glossary  # noqa: E402

CONTENT = SCRIPT_DIR.parents[1] / "content"

# Both shapes that exist in the wild. The first is what the hand-rolled parsers
# required; the second is what `yaml.safe_dump` produced and none of them matched.
QUOTED_SHAPE = """schema_version: 1
entries:
  - phonetic: "hudud"
    transliteration: "hudud"
    arabic_script: "حُدُود"
    audio_phonetic: "hu-dood"
    first_seen_snippet: "the ranks"
    annotation_class: "teach"
    annotation_reason: "load-bearing"
"""

SAFE_DUMP_SHAPE = """schema_version: 1
entries:
- phonetic: hudud
  transliteration: hudud
  arabic_script: حُدُود
  audio_phonetic: hu-dood
  first_seen_snippet: the ranks
  annotation_class: teach
  annotation_reason: load-bearing
"""


def _real_glossaries() -> list[Path]:
    return sorted(CONTENT.glob("*/*/_system/glossary.yml")) + sorted(CONTENT.glob("*/*/*/_system/glossary.yml"))


@pytest.mark.parametrize("text", [QUOTED_SHAPE, SAFE_DUMP_SHAPE], ids=["quoted", "safe_dump"])
def test_both_shapes_in_the_wild_read_identically(tmp_path: Path, text: str) -> None:
    path = tmp_path / "glossary.yml"
    path.write_text(text, encoding="utf-8")

    entries, top = load_glossary(path)

    assert len(entries) == 1, "a full glossary must never read as empty — that is the bug"
    assert entries[0]["phonetic"] == "hudud"
    assert entries[0]["arabic_script"] == "حُدُود"
    assert entries[0]["annotation_class"] == "teach"
    assert top["schema_version"] == 1


def test_an_unknown_field_survives_a_round_trip(tmp_path: Path) -> None:
    """No allow-list. A field added elsewhere must not die here."""
    path = tmp_path / "glossary.yml"
    save_glossary(path, [{"phonetic": "x", "arabic_script": "س", "some_future_field": "keep me"}], {})

    entries, _ = load_glossary(path)

    assert entries[0]["some_future_field"] == "keep me"


def test_an_absent_file_is_empty_but_a_malformed_one_raises(tmp_path: Path) -> None:
    """Absent means new; malformed means something is wrong.

    Reading a file you cannot parse as "no curation here" is exactly how the
    curation was lost, so the two cases must not share an answer.
    """
    assert load_glossary(tmp_path / "absent.yml") == ([], {})

    bad = tmp_path / "bad.yml"
    bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_glossary(bad)


def test_a_newline_in_a_snippet_cannot_corrupt_the_following_entries(tmp_path: Path) -> None:
    path = tmp_path / "glossary.yml"
    save_glossary(
        path,
        [
            {"phonetic": "a", "first_seen_snippet": "line one\nline two"},
            {"phonetic": "b", "arabic_script": "ب"},
        ],
        {},
    )

    entries, _ = load_glossary(path)

    assert [e["phonetic"] for e in entries] == ["a", "b"]
    assert entries[0]["first_seen_snippet"] == "line one\nline two"


@pytest.mark.parametrize("path", _real_glossaries(), ids=lambda p: p.parent.parent.name)
def test_every_real_glossary_parses_round_trips_and_keeps_every_field(path: Path) -> None:
    entries, top = load_glossary(path)
    assert entries, f"{path} parsed as EMPTY — the failure this module exists to prevent"

    once = dump_glossary(entries, top)
    reparsed, reparsed_top = load_glossary_from_text(once, path)
    twice = dump_glossary(reparsed, reparsed_top)

    assert once == twice, "a second write must be byte-identical, or every diff is noise"
    keys_before = {k for e in entries for k in e}
    keys_after = {k for e in reparsed for k in e}
    assert keys_before == keys_after, f"fields lost in the round trip: {sorted(keys_before - keys_after)}"


def load_glossary_from_text(text: str, like: Path) -> tuple[list[dict], dict]:
    """`load_glossary` over a string, keeping the real file untouched."""
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False, encoding="utf-8") as fh:
        fh.write(text)
        tmp = Path(fh.name)
    try:
        return load_glossary(tmp)
    finally:
        tmp.unlink(missing_ok=True)
