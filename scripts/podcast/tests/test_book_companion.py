"""Companion-card generation: the guardrails and the balance rule.

The generator's value is not its prose — it is that a card cannot reach disk
without proving itself, and that no single kind can take over a chapter.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _book_companion import (  # noqa: E402
    KIND_ANALOGY,
    KIND_ETYMOLOGY,
    KIND_EXPLANATION,
    KIND_NOTE,
    KIND_QUESTION,
    TARGET_MAX,
    TARGET_MIN,
    author_phase_book_companion,
    book_chapters,
    dedupe_cards,
    episode_ref,
    gate_card,
    map_transcripts_to_chapters,
    mix_report,
    parse_cards,
    safe_chapter_key,
    select_balanced,
)

PROSE = (
    "The Master answered the boy plainly. He said that gratitude is not a feeling but a debt, "
    "and that a debt is paid by walking the road it opens. The boy listened and asked for the "
    "conditions of the covenant."
)


def card(kind: str, body: str = "", **kw) -> dict:
    return {
        "kind": kind,
        "body": body or ("word " * 40).strip(),
        **kw,
    }


# ─── keys and chapter splitting ──────────────────────────────────────────────
def test_chapter_key_matches_the_readers_shape() -> None:
    assert safe_chapter_key("3. The Boy at the Door — Limits and Conditions") == (
        "3-the-boy-at-the-door-limits-and-conditions"
    )
    assert safe_chapter_key("!!!") == "general"


def test_book_chapters_strips_editorial_asides_from_quotable_prose() -> None:
    md = "# Book\n\n## One\n\nreal prose here\n\n<!-- editorial:begin -->\n> aside prose\n<!-- editorial:end -->\n"
    chapters = book_chapters(md)
    assert len(chapters) == 1
    assert "real prose" in chapters[0]["prose"]
    assert "aside prose" not in chapters[0]["prose"]


def test_episode_ref_reads_the_canonical_stem() -> None:
    assert episode_ref("ch07d-air-and-the-instance-beyond-air") == "EP07"


# ─── guardrails ──────────────────────────────────────────────────────────────
def test_card_with_a_verbatim_quote_passes() -> None:
    ok, reasons = gate_card(card(KIND_EXPLANATION, quote="gratitude is not a feeling but a debt"), prose=PROSE)
    assert ok, reasons


def test_quote_that_is_not_in_the_chapter_is_rejected() -> None:
    ok, reasons = gate_card(card(KIND_EXPLANATION, quote="gratitude is a warm feeling"), prose=PROSE)
    assert not ok
    assert "verbatim" in reasons[0]


def test_curly_quotes_do_not_fail_a_real_match() -> None:
    prose = "He said “gratitude is a debt” and left."
    ok, _ = gate_card(card(KIND_NOTE, quote='"gratitude is a debt"'), prose=prose)
    assert ok


def test_too_short_card_is_rejected() -> None:
    ok, reasons = gate_card(card(KIND_ANALOGY, body="too short"), prose=PROSE)
    assert not ok
    assert "too short" in reasons[0]


def test_unknown_kind_is_rejected() -> None:
    ok, reasons = gate_card(card("haiku"), prose=PROSE)
    assert not ok
    assert "unknown kind" in " ".join(reasons)


def test_arabic_not_traceable_to_a_source_is_rejected() -> None:
    body = ("word " * 30) + "حسبنا الله ونعم الوكيل"
    ok, reasons = gate_card(card(KIND_NOTE, body=body), prose=PROSE, arabic_src="")
    assert not ok
    assert "Arabic not traceable" in " ".join(reasons)


def test_arabic_copied_from_the_source_is_accepted() -> None:
    arabic = "حسبنا الله ونعم الوكيل"
    ok, reasons = gate_card(card(KIND_NOTE, body=("word " * 30) + arabic), prose=PROSE, arabic_src=arabic)
    assert ok, reasons


def test_etymology_card_must_name_a_term_the_corpus_carries() -> None:
    body = ("word " * 30) + "the root of tawakkul is instructive"
    ok, _ = gate_card(card(KIND_ETYMOLOGY, body=body), prose=PROSE, etymology_terms=frozenset({"tawakkul"}))
    assert ok
    ok, reasons = gate_card(card(KIND_ETYMOLOGY, body=body), prose=PROSE, etymology_terms=frozenset({"ikhlas"}))
    assert not ok
    assert "names no term" in " ".join(reasons)


def test_meta_commentary_is_rejected() -> None:
    ok, reasons = gate_card(card(KIND_NOTE, body="As an AI " + ("word " * 30)), prose=PROSE)
    assert not ok
    assert "meta-commentary" in " ".join(reasons)


def test_dedupe_drops_the_same_idea_found_by_two_lanes() -> None:
    a = card(KIND_ANALOGY, body="Gratitude is like a road you walk rather than a gift you shelve away somewhere")
    b = dict(a)
    assert len(dedupe_cards([a, b])) == 1


# ─── the balance rule ────────────────────────────────────────────────────────
def test_one_kind_cannot_take_over_a_chapter() -> None:
    cards = [card(KIND_ANALOGY, body=f"analogy number {i} " + ("word " * 30)) for i in range(20)]
    cards += [card(KIND_EXPLANATION, body=f"explanation {i} " + ("word " * 30)) for i in range(6)]
    cards += [card(KIND_QUESTION, body=f"question {i} " + ("word " * 30)) for i in range(4)]

    chosen = select_balanced(cards)
    report = mix_report(chosen)

    assert TARGET_MIN <= report["total"] <= TARGET_MAX
    assert report["within_ceiling"], report["kinds"]
    assert report["kinds"][KIND_ANALOGY] <= 5


def test_every_kind_present_in_the_pool_gets_at_least_one_slot() -> None:
    cards = [card(KIND_ANALOGY, body=f"a{i} " + ("word " * 30)) for i in range(12)]
    cards += [card(KIND_ETYMOLOGY, body="the root " + ("word " * 30))]
    cards += [card(KIND_QUESTION, body="what is " + ("word " * 30))]

    chosen = select_balanced(cards)
    kinds = {c["kind"] for c in chosen}

    assert KIND_ETYMOLOGY in kinds
    assert KIND_QUESTION in kinds


def test_ranking_order_is_respected_where_balance_allows() -> None:
    cards = [card(KIND_EXPLANATION, body=f"e{i} " + ("word " * 30)) for i in range(20)]
    chosen = select_balanced(cards)
    bodies = [c["body"] for c in chosen]
    assert bodies == sorted(bodies, key=lambda b: cards.index(next(c for c in cards if c["body"] == b)))


def test_a_single_kind_pool_reaches_the_floor_but_is_flagged_for_review() -> None:
    cards = [card(KIND_EXPLANATION, body=f"e{i} " + ("word " * 30)) for i in range(20)]

    report = mix_report(select_balanced(cards))

    assert report["total"] == TARGET_MIN, "a one-kind chapter still reaches the floor"
    assert not report["within_ceiling"], "and the breach is reported, never silent"


def test_a_thin_chapter_yields_what_it_has_rather_than_padding() -> None:
    cards = [card(KIND_EXPLANATION, body=f"e{i} " + ("word " * 30)) for i in range(3)]
    chosen = select_balanced(cards)
    assert len(chosen) == 3


# ─── parsing and transcript mapping ──────────────────────────────────────────
def test_parse_cards_survives_a_code_fence_and_stray_prose() -> None:
    raw = 'Sure!\n```json\n[{"kind":"note","body":"b","anchor":"a"}]\n```\nHope that helps.'
    assert parse_cards(raw) == [{"kind": "note", "body": "b", "anchor": "a"}]


def test_parse_cards_returns_empty_on_junk() -> None:
    assert parse_cards("no json at all") == []


def test_transcripts_are_assigned_to_the_chapter_they_cover() -> None:
    chapters = [
        {"key": "one", "title": "One", "prose": "gratitude covenant debt boy master road walking"},
        {"key": "two", "title": "Two", "prose": "cosmology heavens spheres creation origins pairs"},
    ]
    transcripts = {
        "ch01a-gratitude": "gratitude covenant debt the boy and the master talk about the road",
        "ch04a-cosmology": "cosmology heavens spheres creation origins and the pairs discussed",
    }
    mapping = map_transcripts_to_chapters(chapters, transcripts)
    assert mapping["one"][0][0] == "ch01a-gratitude"
    assert mapping["two"][0][0] == "ch04a-cosmology"


def test_no_transcripts_means_every_chapter_simply_loses_that_lane() -> None:
    chapters = [{"key": "one", "title": "One", "prose": "text"}]
    assert map_transcripts_to_chapters(chapters, {}) == {"one": []}


# ─── end to end, with the model stubbed ──────────────────────────────────────
def test_phase_writes_the_readers_on_disk_shape(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(f"# Book\n\n## 1. One\n\n{PROSE}\n", encoding="utf-8")

    def fake_gen(prompt: str, book_dir: Path, label: str, log) -> str:
        if label.startswith("comp-judge"):
            return "[0,1,2]"
        return json.dumps(
            [
                {
                    "kind": KIND_EXPLANATION,
                    "anchor": "debt",
                    "body": "A debt " + ("word " * 30),
                    "quote": "gratitude is not a feeling but a debt",
                },
                {"kind": KIND_ANALOGY, "anchor": "road", "body": "Like a road " + ("word " * 30)},
                {"kind": KIND_QUESTION, "anchor": "ask", "body": "What debt " + ("word " * 30)},
            ]
        )

    report = author_phase_book_companion(bd, log=lambda *a: None, generator=fake_gen)

    doc = json.loads((bd / "_system" / "companion-notes" / "1-one.json").read_text(encoding="utf-8"))
    assert doc["chapter"] == "1-one"
    assert doc["slug"] == "slug"
    assert {n["kind"] for n in doc["notes"]} == {KIND_EXPLANATION, KIND_ANALOGY, KIND_QUESTION}
    assert all(n["id"] and n["createdAt"] and n["updatedAt"] for n in doc["notes"])
    assert report["chapters"][0]["chapter"] == "1-one"


def test_phase_without_a_composed_book_fails_loudly(tmp_path: Path) -> None:
    import pytest
    from _authoring._core import AuthoringError

    with pytest.raises(AuthoringError):
        author_phase_book_companion(tmp_path, log=lambda *a: None, generator=lambda *a: "[]")
