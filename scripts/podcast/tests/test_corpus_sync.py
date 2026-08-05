"""Unit tests for corpus_sync reconciliation logic.

Covers the merge/collision primitives that resolve duplicate-id JSONL lines
produced by cross-machine git union-merges. These are pure functions (no DB),
so they run fast and deterministically.
"""

import sys
from pathlib import Path

_INTEL = Path(__file__).resolve().parent.parent / "intelligence"
if str(_INTEL) not in sys.path:
    sys.path.insert(0, str(_INTEL))

import corpus_sync as cs


def _atom(atom_id, text_en=None, arabic=None, sources=None, variants=None, date="2026-01-01", confidence=1.0):
    body = {}
    if text_en is not None:
        body["text_en"] = text_en
    if arabic is not None:
        body["arabic"] = arabic
    return {
        "id": atom_id,
        "type": "quran",
        "body": body,
        "first_seen": {"book": "b", "chapter": "c", "date": date},
        "confidence": confidence,
        "tradition": "universal",
        "content_level": None,
        "sources": sources or [],
        "variants": variants or [],
    }


def test_merge_is_lossless_field_union():
    a = _atom("x", text_en="hello")
    b = _atom("x", text_en="hello", arabic="AR")
    m = cs._merge_envelopes(a, b)
    assert m["body"]["text_en"] == "hello"
    assert m["body"]["arabic"] == "AR"  # field added, nothing dropped


def test_merge_unions_sources_and_variants():
    a = _atom("x", text_en="t", sources=[{"book": "b1", "chapter": "c1", "locator": None}])
    b = _atom("x", text_en="t", sources=[{"book": "b2", "chapter": "c2", "locator": None}])
    m = cs._merge_envelopes(a, b)
    assert len(m["sources"]) == 2


def test_merge_keeps_earliest_first_seen_and_max_confidence():
    a = _atom("x", text_en="t", date="2026-06-15", confidence=0.5)
    b = _atom("x", text_en="t", date="2026-01-01", confidence=0.9)
    m = cs._merge_envelopes(a, b)
    assert m["first_seen"]["date"] == "2026-01-01"
    assert m["confidence"] == 0.9


def test_same_text_versions_merge_to_one():
    versions = [_atom("x", text_en="same"), _atom("x", text_en="same", arabic="AR")]
    kept, collisions = cs._reconcile_group("x", versions)
    assert len(kept) == 1
    assert collisions == []
    assert kept[0][1]["body"]["arabic"] == "AR"


def test_id_collision_splits_and_rekeys():
    # two genuinely different atoms under one id -> keep earliest, re-key the rest
    versions = [
        _atom("x", text_en="hadith ONE", date="2026-06-14"),
        _atom("x", text_en="hadith TWO different", date="2026-06-15"),
    ]
    kept, collisions = cs._reconcile_group("x", versions)
    ids = {k for k, _ in kept}
    assert ids == {"x", "x~1"}
    # earliest first_seen keeps the original id; nothing is lost
    texts = {e["body"]["text_en"] for _, e in kept}
    assert texts == {"hadith ONE", "hadith TWO different"}
    assert len(collisions) == 2


def test_unique_id_count_ignores_duplicate_lines(tmp_path):
    p = tmp_path / "quran.jsonl"
    import json

    lines = [
        json.dumps(_atom("a", text_en="t")),
        json.dumps(_atom("a", text_en="t", arabic="AR")),  # dup id
        json.dumps(_atom("b", text_en="t2")),
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert cs._jsonl_unique_id_count(p) == 2  # not 3


if __name__ == "__main__":
    import subprocess

    raise SystemExit(subprocess.call(["python3", "-m", "pytest", "-q", __file__]))
