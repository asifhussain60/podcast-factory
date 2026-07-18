"""Voice library — pools, deterministic casting, resolution priority."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _voice_library as vl


def test_pools_load_with_unique_ids():
    males, females = vl.male_pool(), vl.female_pool()
    assert len(males) >= 4 and len(females) >= 4
    ids = [e["voice_id"] for e in males + females]
    assert len(ids) == len(set(ids))
    for e in males + females:
        assert e["voice_id"].strip() and e["name"].strip()


def test_pair_for_slug_deterministic_and_rotating():
    a = vl.pair_for_slug("kitab-al-riyad")
    b = vl.pair_for_slug("kitab-al-riyad")
    assert a == b  # stable across re-renders
    assert set(a) == {"host_a", "host_b"}
    male_ids = {e["voice_id"] for e in vl.male_pool()}
    female_ids = {e["voice_id"] for e in vl.female_pool()}
    assert a["host_a"] in male_ids and a["host_b"] in female_ids
    pairs = {tuple(sorted(vl.pair_for_slug(f"book-{i}").items())) for i in range(24)}
    assert len(pairs) > 1  # pools actually rotate


def test_resolve_name_short_and_full_case_insensitive():
    eric = vl.resolve_name("eric")
    assert eric == "cjVigY5qzO86Huf0OWal"
    assert vl.resolve_name("Lily - Velvety Actress") == "pFZP5JQG7iQjIQuC4Bku"
    assert vl.resolve_name("nope-not-a-voice") is None


def test_voices_for_book_resolution_priority(tmp_path):
    from _audio_engines import voices_for_book

    sysdir = tmp_path / "_system"
    sysdir.mkdir()
    # library pair applies when no override
    (sysdir / "series-config.yaml").write_text("audio_engine: elevenlabs\n")
    v = voices_for_book(tmp_path)
    assert v == vl.pair_for_slug(tmp_path.name)
    # voice_cast names beat the library pick
    (sysdir / "series-config.yaml").write_text(
        "audio_engine: elevenlabs\nvoice_cast:\n  host_a: George\n  host_b: Millie\n"
    )
    v = voices_for_book(tmp_path)
    assert v["host_a"] == vl.resolve_name("George")
    assert v["host_b"] == vl.resolve_name("Millie")
    # explicit elevenlabs_voices IDs beat everything
    (sysdir / "series-config.yaml").write_text(
        "audio_engine: elevenlabs\nvoice_cast:\n  host_a: George\nelevenlabs_voices:\n  host_a: EXPLICIT123\n"
    )
    v = voices_for_book(tmp_path)
    assert v["host_a"] == "EXPLICIT123"
