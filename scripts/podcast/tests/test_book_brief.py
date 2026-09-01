#!/usr/bin/env python3
"""The Book in Brief — the ranking is the thesis, so the ranking is what is pinned.

Three claims carry this lane, and each one is a claim a plausible implementation
gets wrong:

  1. FREQUENCY IS NOT IMPORTANCE. A point stated once at weight 5 must outrank a
     point restated in every chapter at weight 2, or the brief becomes a summary of
     whatever the author repeated most.
  2. A PREREQUISITE IS NEVER ORPHANED. A retained point whose premise scored below
     the line pulls that premise back in, or the technical-book failure and the
     broken-causal-chain failure both ship.
  3. BUDGET FOLLOWS IMPORTANCE, NOT LENGTH. A long section carrying little must be
     allowed to receive almost nothing — that is the entire reason this exists
     rather than a proportional trim.

The gate is pinned separately, and pinned on the shapes it must REFUSE, because a
gate that accepts everything passes every test written as "the good draft is
accepted".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import _book_brief as B  # noqa: E402
import _book_brief_rank as R  # noqa: E402
from _book_brief_gate import MIN_FRACTION, gate_brief, lexical_shortlist  # noqa: E402


def _analyses(*sections):
    return [{"title": t, "purpose": "", "points": pts} for t, pts in sections]


#: Distinct vocabulary per point. The fixtures used to be "Point number 1/2/3..."
#: — which the dedup pass correctly collapsed into ONE point, since digits are not
#: content words, so every ranking test was silently ranking a single item.
_SUBJECTS = """embankment lodger grandmother canal bridge lantern letter pension theatre
    barber rooftop staircase snowfall carriage orphan violin ledger passport spring rooming
    tenant landlord mirror garret bookshop ferry courtyard chandelier omnibus telegram""".split()


def _distinct(i: int, *, weight=3, kind="claim"):
    return _pt(f"The {_SUBJECTS[i % len(_SUBJECTS)]} matters to the outcome.", weight=weight, kind=kind)


def _pt(text, *, weight=3, kind="claim", depends_on=(), entities=()):
    return {"text": text, "weight": weight, "kind": kind, "depends_on": list(depends_on), "entities": list(entities)}


# --------------------------------------------------------------------------
# 1. frequency is not importance
# --------------------------------------------------------------------------


def test_a_once_stated_essential_point_outranks_a_constantly_repeated_minor_one():
    repeated = _pt("The dreamer is lonely in the city.", weight=2, entities=["dreamer"])
    analyses = _analyses(
        (
            "One",
            [_pt("Nastenka waits for her lodger to return.", weight=5, kind="turn", entities=["Nastenka"]), repeated],
        ),
        ("Two", [dict(repeated)]),
        ("Three", [dict(repeated)]),
        ("Four", [dict(repeated)]),
    )
    plan = R.plan(analyses, total_words=3500)
    by_text = {p["text"]: p for p in plan["points"]}
    rare = by_text["Nastenka waits for her lodger to return."]
    common = max((p for p in plan["points"] if p["text"] == repeated["text"]), key=lambda p: p["score"])
    assert rare["score"] > common["score"], (rare["score"], common["score"])
    assert rare["tier"] == "essential"


def test_recurrence_is_capped_so_it_can_never_overtake_a_weight_gap_of_three():
    """The cap is 2.0 and the weight span is 1..5. Pinned as arithmetic, not as a
    property of one fixture, because raising the cap is the tempting change."""
    assert max(R.KIND_BONUS.values()) + 2.0 + 2.0 + 0.5 < 5.0 + 5.0


# --------------------------------------------------------------------------
# 2. prerequisites survive the cut
# --------------------------------------------------------------------------


def test_a_low_scoring_prerequisite_is_pulled_back_in_by_the_point_that_needs_it():
    """Capacity of one: only the thesis can be afforded, and its premise comes with
    it anyway. Squeezed deliberately — at any comfortable budget both points are
    retained by the ordinary cut and the closure is never exercised, which is how a
    broken closure passes a test that only checks membership."""
    points = R.assign_tiers(
        R.score_points(
            R.normalize_points(
                _analyses(
                    ("One", [_pt("A niche term is defined.", weight=1, kind="context")]),
                    (
                        "Two",
                        [
                            _pt(
                                "The whole argument turns on that term.",
                                weight=5,
                                kind="thesis",
                                depends_on=["S01-P01"],
                            )
                        ],
                    ),
                )
            )
        )
    )
    retained = R._retain(points, capacity=1)
    by_id = {p["id"]: p for p in retained}
    assert "S02-P01" in by_id, "the thesis must be the one point a capacity of 1 buys"
    assert "S01-P01" in by_id, "its premise must come with it"
    assert by_id["S01-P01"].get("retained_as_prerequisite") is True


def test_a_prerequisite_chain_is_closed_transitively():
    points = R.assign_tiers(
        R.score_points(
            R.normalize_points(
                _analyses(
                    ("One", [_pt("Base.", weight=1, kind="context")]),
                    ("Two", [_pt("Middle.", weight=1, kind="context", depends_on=["S01-P01"])]),
                    ("Three", [_pt("Top.", weight=5, kind="thesis", depends_on=["S02-P01"])]),
                )
            )
        )
    )
    assert {p["id"] for p in R._retain(points, capacity=1)} == {"S01-P01", "S02-P01", "S03-P01"}


def test_in_degree_raises_a_prerequisites_own_score():
    analyses = _analyses(
        ("One", [_pt("Foundation.", weight=2)]),
        ("Two", [_pt("Builds on it.", weight=2, depends_on=["S01-P01"])]),
        ("Three", [_pt("Also builds on it.", weight=2, depends_on=["S01-P01"])]),
    )
    points = {p["id"]: p for p in R.plan(analyses, total_words=3500)["points"]}
    assert points["S01-P01"]["in_degree"] == 2
    assert points["S01-P01"]["score"] > points["S02-P01"]["score"]


# --------------------------------------------------------------------------
# 3. budget follows importance, not length
# --------------------------------------------------------------------------


def test_a_long_section_of_low_value_material_gets_almost_nothing():
    """Twelve weak points against two strong ones. Source length says the digression
    wins six to one; importance says it loses."""
    digression = [_distinct(i, weight=1, kind="example") for i in range(12)]
    core = [
        _pt("The central claim of the book.", weight=5, kind="thesis"),
        _pt("The reasoning that establishes it.", weight=5, kind="claim"),
    ]
    plan = R.plan(_analyses(("Digression", digression), ("Core", core)), total_words=3500)
    assert plan["section_words"].get(2, 0) > plan["section_words"].get(1, 0)


def test_allocations_sum_to_the_body_budget_exactly():
    plan = R.plan(
        _analyses(("A", [_pt("x", weight=4)]), ("B", [_pt("y", weight=2)]), ("C", [_pt("z", weight=5)])),
        total_words=3500,
    )
    assert sum(plan["section_words"].values()) == plan["body_words"]
    assert plan["opening_words"] + plan["body_words"] + plan["closing_words"] == 3500


def test_reserves_are_capped_so_a_deep_brief_is_not_mostly_opening_and_close():
    deep = R.plan(_analyses(("A", [_pt("x", weight=5)])), total_words=R.PRESETS["deep"])
    assert deep["opening_words"] <= 260 and deep["closing_words"] <= 320
    assert deep["body_words"] / deep["total_words"] > 0.85


def test_every_essential_point_is_retained_even_at_the_quick_preset():
    analyses = _analyses(("A", [_distinct(i, weight=5, kind="thesis") for i in range(30)]))
    plan = R.plan(analyses, total_words=R.PRESETS["quick"])
    assert set(plan["essential_ids"]) <= {p["id"] for p in plan["retained"]}


def test_essential_is_never_empty_even_when_every_weight_is_low():
    plan = R.plan(_analyses(("A", [_distinct(i, weight=1, kind="context") for i in range(20)])), total_words=3500)
    assert plan["essential_ids"]


# --------------------------------------------------------------------------
# 4. the book restating itself is collapsed, not explained twice
# --------------------------------------------------------------------------


def test_the_same_point_made_in_two_sections_survives_once_as_the_richer_version():
    """A foreword's broad summary and the chapter's own account of the same event.
    White Nights ships exactly this, and before the dedup pass its ten foreword
    points all became `essential` restatements of chapters not yet read."""
    analyses = _analyses(
        ("Foreword", [_pt("Nastenka leaves the dreamer for her returning lodger.", weight=3, entities=["Nastenka"])]),
        (
            "Fourth Night",
            [
                _pt(
                    "Nastenka leaves the dreamer when her lodger returns to the bench.",
                    weight=5,
                    kind="turn",
                    entities=["Nastenka"],
                )
            ],
        ),
    )
    plan = R.plan(analyses, total_words=3500)
    assert len(plan["points"]) == 1, [p["text"] for p in plan["points"]]
    assert plan["points"][0]["section_index"] == 2, "the survivor must be the richer statement, not the earlier one"
    assert plan["duplicates"] and plan["duplicates"][0]["of"] == plan["points"][0]["id"]


def test_a_dropped_duplicates_dependents_are_repointed_at_the_survivor():
    analyses = _analyses(
        ("One", [_pt("Nastenka leaves the dreamer for the lodger.", weight=3, entities=["Nastenka"])]),
        ("Two", [_pt("Nastenka leaves the dreamer when the lodger returns.", weight=5, entities=["Nastenka"])]),
        ("Three", [_pt("He is left alone but grateful.", weight=5, kind="resolution", depends_on=["S01-P01"])]),
    )
    plan = R.plan(analyses, total_words=3500)
    dependent = next(p for p in plan["points"] if p["text"].startswith("He is left"))
    assert dependent["depends_on"] == ["S02-P01"], dependent["depends_on"]


def test_two_genuinely_different_points_are_not_collapsed():
    analyses = _analyses(
        ("One", [_pt("Nastenka waits on the embankment for her lodger.", weight=4, entities=["Nastenka"])]),
        ("Two", [_pt("The dreamer confesses that he has never spoken to a woman.", weight=4)]),
    )
    assert len(R.plan(analyses, total_words=3500)["points"]) == 2


# --------------------------------------------------------------------------
# 5. a model that ignores the weight scale cannot destroy the ranking
# --------------------------------------------------------------------------


def test_when_almost_everything_is_marked_essential_the_tiering_goes_relative():
    """The first real book came back with 71 of 85 points at weight 5. An
    `essential` set that large cannot be protected from a budget, so the protection
    silently becomes nothing and the brief is allocated evenly across every chapter
    — failure mode seven, arrived at through the guard meant to prevent it."""
    analyses = _analyses(("A", [_distinct(i, weight=5, kind="thesis") for i in range(30)]))
    plan = R.plan(analyses, total_words=3500)
    assert plan["tiered_relatively"] is True
    share = len(plan["essential_ids"]) / len(plan["points"])
    assert share <= R.ESSENTIAL_SHARE_CAP + 0.01, share


def test_honest_weights_are_left_on_the_absolute_scale():
    pts = [_distinct(i, weight=2) for i in range(15)]
    pts += [_distinct(20 + i, weight=5, kind="thesis") for i in range(2)]
    plan = R.plan(_analyses(("A", pts)), total_words=3500)
    assert plan["tiered_relatively"] is False
    assert len(plan["essential_ids"]) == 2


def test_the_relative_fallback_never_leaves_a_book_with_nothing_protected():
    analyses = _analyses(("A", [_distinct(i, weight=5) for i in range(20)]))
    assert len(R.plan(analyses, total_words=3500)["essential_ids"]) >= 3


# --------------------------------------------------------------------------
# 6. a section about the book is not part of the book
# --------------------------------------------------------------------------


def test_a_declared_excluded_section_is_not_condensed():
    titles = [s["title"] for s in B.sections_for_brief(_BOOK, exclude=["Introduction"])]
    assert titles == ["First Night"]


def test_exclusion_is_read_from_config_and_defaults_to_nothing(tmp_path):
    (tmp_path / "_system").mkdir()
    cfg = tmp_path / "_system" / "series-config.yaml"
    cfg.write_text("content_profile: audiobook\n", encoding="utf-8")
    assert B.excluded_sections(tmp_path) == []
    cfg.write_text("brief_exclude_sections:\n  - Introduction\n  - Afterword\n", encoding="utf-8")
    assert B.excluded_sections(tmp_path) == ["Introduction", "Afterword"]


def test_white_nights_declares_its_producers_introduction_as_excluded():
    """A live-config assertion, deliberately. The exclusion is the difference
    between condensing Dostoyevsky and condensing the producer's summary of him,
    and it is one line in a YAML file that nothing else would notice losing."""
    import yaml

    book = SCRIPT_DIR.parents[1] / "content" / "Audiobook" / "white-nights"
    if not book.exists():  # the suite must still run in a checkout without content
        return
    cfg = yaml.safe_load((book / "_system" / "series-config.yaml").read_text(encoding="utf-8"))
    assert cfg.get("brief_strategy") == "narrative"
    assert "Introduction" in (cfg.get("brief_exclude_sections") or [])


# --------------------------------------------------------------------------
# the gate refuses, and refuses the right things
# --------------------------------------------------------------------------


def _filler(n):
    return " ".join(["word"] * n) + "."


def test_gate_accepts_an_ordinary_brief():
    ok, reasons = gate_brief(_filler(3000), total_words=3500)
    assert ok, reasons


def test_gate_refuses_a_table_of_contents_summary():
    body = _filler(2000) + " Chapter 3 discusses incentives and motivation."
    ok, reasons = gate_brief(body, total_words=3500)
    assert not ok and any("description of the book" in r for r in reasons)


def test_gate_refuses_the_author_then_says_shape():
    ok, reasons = gate_brief(_filler(2000) + " The author then discusses the second problem.", total_words=3500)
    assert not ok and any("description of the book" in r for r in reasons)


def test_gate_refuses_bullets_and_extra_structure():
    assert not gate_brief(_filler(2000) + "\n\n- a bullet point here.", total_words=3500)[0]
    assert not gate_brief(_filler(2000) + "\n\n### a\n\n### b\n\n### c\n\n### d\n", total_words=3500)[0]
    assert not gate_brief(_filler(2000) + "\n\n## a new section\n", total_words=3500)[0]


def test_gate_refuses_a_brief_cut_mid_sentence():
    ok, reasons = gate_brief(_filler(2000)[:-1] + " and then she", total_words=3500)
    assert not ok and any("mid-sentence" in r for r in reasons)


def test_gate_refuses_over_and_under_length():
    assert not gate_brief(_filler(4000), total_words=3500)[0]
    assert not gate_brief(_filler(int(3500 * MIN_FRACTION) - 50), total_words=3500)[0]


def test_gate_refuses_process_chatter():
    assert not gate_brief(_filler(2000) + " Here is the condensed version.", total_words=3500)[0]


# --------------------------------------------------------------------------
# the coverage shortlist is a question, not a verdict
# --------------------------------------------------------------------------


def test_shortlist_flags_a_genuinely_absent_point_and_passes_a_paraphrased_one():
    draft = "Nastenka waited each evening on the embankment for the lodger who had promised to return."
    absent = {"text": "The dreamer inherits a fortune in Moscow.", "entities": ["Moscow"]}
    present = {"text": "Nastenka waits on the embankment for the lodger.", "entities": ["Nastenka"]}
    flagged = {p["text"] for p in lexical_shortlist(draft, [absent, present])}
    assert absent["text"] in flagged
    assert present["text"] not in flagged


# --------------------------------------------------------------------------
# structure: where the section goes, and that it goes there once
# --------------------------------------------------------------------------

_BOOK = """# White Nights

## Opening Credits

Narrated by someone.

## Introduction

An essay about the book.

## First Night

The story starts.
"""


def test_the_brief_lands_below_the_credits_and_above_the_introduction():
    out = B.inject_brief(_BOOK, "A condensed rendering.")
    heads = [ln for ln in out.splitlines() if ln.startswith("## ")]
    assert heads == ["## Opening Credits", B.BRIEF_HEADING, "## Introduction", "## First Night"]


def test_injection_is_idempotent_and_never_stacks():
    once = B.inject_brief(_BOOK, "A condensed rendering.")
    twice = B.inject_brief(once, "A different condensed rendering.")
    assert twice.count(B.BRIEF_HEADING) == 1
    assert "A different condensed rendering." in twice
    assert "A condensed rendering." not in twice


def test_a_book_with_no_credits_gets_the_brief_first():
    out = B.inject_brief("# T\n\n## Introduction to the Book\n\nx\n\n## One\n\ny\n", "Brief text.")
    heads = [ln for ln in out.splitlines() if ln.startswith("## ")]
    assert heads[0] == B.BRIEF_HEADING


def test_strip_removes_the_whole_section_and_nothing_else():
    out = B.inject_brief(_BOOK, "A condensed rendering.")
    assert B.strip_brief(out).strip() == _BOOK.strip()


def test_the_analysed_sections_exclude_apparatus_but_keep_a_source_introduction():
    with_brief = B.inject_brief(_BOOK, "A condensed rendering.")
    titles = [s["title"] for s in B.sections_for_brief(with_brief)]
    assert titles == ["Introduction", "First Night"]


def test_the_pipelines_own_introduction_is_not_condensed_into_the_brief():
    md = "# T\n\n## Introduction to the Book\n\nThis edition renders...\n\n## One\n\nbody\n"
    assert [s["title"] for s in B.sections_for_brief(md)] == ["One"]


# --------------------------------------------------------------------------
# configuration is declared, never sniffed
# --------------------------------------------------------------------------


def test_a_declared_strategy_wins_over_every_inference(tmp_path):
    (tmp_path / "_system").mkdir()
    (tmp_path / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_scholarly\nbrief_strategy: narrative\n", encoding="utf-8"
    )
    assert B.strategy_for(tmp_path) == "narrative"


def test_strategy_falls_back_to_profile_then_to_frame(tmp_path):
    (tmp_path / "_system").mkdir()
    cfg = tmp_path / "_system" / "series-config.yaml"
    cfg.write_text("content_profile: islamic_scholarly\n", encoding="utf-8")
    assert B.strategy_for(tmp_path) == "doctrinal"
    cfg.write_text("content_profile: audiobook\nnarrative_frame: external_narrator\n", encoding="utf-8")
    assert B.strategy_for(tmp_path) == "narrative"
    cfg.write_text("content_profile: audiobook\n", encoding="utf-8")
    assert B.strategy_for(tmp_path) == "expository"


def test_word_target_prefers_an_explicit_count_then_a_preset_then_standard(tmp_path):
    (tmp_path / "_system").mkdir()
    cfg = tmp_path / "_system" / "series-config.yaml"
    cfg.write_text("brief_words: 2200\nbrief_mode: quick\n", encoding="utf-8")
    assert B.target_words(tmp_path) == 2200
    cfg.write_text("brief_mode: quick\n", encoding="utf-8")
    assert B.target_words(tmp_path) == R.PRESETS["quick"]
    cfg.write_text("content_profile: audiobook\n", encoding="utf-8")
    assert B.target_words(tmp_path) == R.PRESETS["standard"] == 3500
    assert B.target_words(tmp_path, override=1234) == 1234


# --------------------------------------------------------------------------
# the step is declared everywhere a step has to be declared
# --------------------------------------------------------------------------


def test_the_brief_is_a_declared_page_altering_apparatus_step():
    from _apparatus_steps import APPARATUS_STEPS
    from _compose_skips import ADVISORY_STEPS, PAGE_ALTERING_STEPS

    assert "brief" in APPARATUS_STEPS
    assert "brief" in PAGE_ALTERING_STEPS and "brief" not in ADVISORY_STEPS


def test_the_brief_runs_after_the_introduction_or_the_two_land_in_the_wrong_order():
    src = (SCRIPT_DIR / "_book_apparatus.py").read_text(encoding="utf-8")
    assert src.index('_ok(book_dir, "introduction")') < src.index('_ok(book_dir, "brief")')


# --------------------------------------------------------------------------
# end to end against a stub model — no network, no spend
# --------------------------------------------------------------------------


def _stub_book(tmp_path):
    (tmp_path / "book").mkdir(parents=True)
    (tmp_path / "_system").mkdir(parents=True)
    (tmp_path / "book" / "book.md").write_text(_BOOK, encoding="utf-8")
    (tmp_path / "meta.yml").write_text("title: White Nights\nauthor: F. Dostoyevsky\n", encoding="utf-8")
    (tmp_path / "_system" / "series-config.yaml").write_text("brief_strategy: narrative\n", encoding="utf-8")
    return tmp_path


def test_end_to_end_with_a_stub_author_writes_analyses_a_plan_and_a_gated_brief(tmp_path):
    book = _stub_book(tmp_path)
    prose = " ".join(["The dreamer meets Nastenka on the embankment."] * 70)  # ~490 words, inside a 600 budget

    def stub(prompt: str) -> str:
        if "structured record" in prompt:
            return json.dumps(
                {
                    "title": "x",
                    "purpose": "p",
                    "points": [
                        {"text": "The dreamer meets Nastenka.", "kind": "turn", "weight": 5, "entities": ["Nastenka"]},
                        {"text": "He walks the city at night.", "kind": "context", "weight": 2},
                    ],
                }
            )
        if '"missing"' in prompt:
            return '{"missing": []}'
        return prose

    result = B.apply_brief(book, author=stub, words=600, log=lambda *_: None)
    assert result["applied"], result
    text = (book / "book" / "book.md").read_text(encoding="utf-8")
    heads = [ln for ln in text.splitlines() if ln.startswith("## ")]
    assert heads == ["## Opening Credits", B.BRIEF_HEADING, "## Introduction", "## First Night"]

    report = json.loads((book / "_system" / "brief" / "report.json").read_text(encoding="utf-8"))
    assert report["accepted"] is True and report["coverage"]["percent"] == 100.0
    assert (book / "_system" / "brief" / "plan.json").exists()
    assert sorted(p.name for p in (book / "_system" / "brief" / "analysis").glob("*.json")) == ["S01.json", "S02.json"]


def test_a_second_run_reuses_the_cache_and_asks_the_model_nothing(tmp_path):
    book = _stub_book(tmp_path)
    prose = " ".join(["The dreamer meets Nastenka on the embankment."] * 70)  # ~490 words, inside a 600 budget
    calls = []

    def stub(prompt: str) -> str:
        calls.append(prompt)
        if "structured record" in prompt:
            return json.dumps({"title": "x", "points": [{"text": "A.", "kind": "turn", "weight": 5}]})
        if '"missing"' in prompt:
            return '{"missing": []}'
        return prose

    B.apply_brief(book, author=stub, words=600, log=lambda *_: None)
    first = len(calls)
    assert first > 0
    B.apply_brief(book, author=stub, words=600, log=lambda *_: None)
    assert len(calls) == first, "a cached brief must not re-buy a single model call"


def test_a_refused_draft_is_not_written_into_the_book(tmp_path):
    book = _stub_book(tmp_path)

    def stub(prompt: str) -> str:
        if "structured record" in prompt:
            return json.dumps({"title": "x", "points": [{"text": "A.", "kind": "turn", "weight": 5}]})
        if '"missing"' in prompt:
            return '{"missing": []}'
        return "Chapter 3 discusses incentives. " + " ".join(["word"] * 500) + "."

    result = B.apply_brief(book, author=stub, words=600, log=lambda *_: None)
    assert not result["applied"]
    assert B.BRIEF_HEADING not in (book / "book" / "book.md").read_text(encoding="utf-8")


def test_analyses_of_sections_that_no_longer_exist_are_pruned(tmp_path):
    """Excluding a section renumbers every section after it, so the tail of the
    previous run is left holding an analysis of something else. Harmless — each
    file carries a fingerprint and a mismatch forces a re-read — but it reads like
    current state to anyone opening the folder, and White Nights left exactly one."""
    book = _stub_book(tmp_path)
    stale = book / "_system" / "brief" / "analysis"
    stale.mkdir(parents=True)
    (stale / "S09.json").write_text('{"title": "gone", "points": []}', encoding="utf-8")

    def stub(_prompt: str) -> str:
        return json.dumps({"title": "x", "points": [{"text": "A.", "kind": "turn", "weight": 5}]})

    B.analyse_sections(book, author=stub, log=lambda *_: None)
    assert not (stale / "S09.json").exists()
    assert sorted(p.name for p in stale.glob("*.json")) == ["S01.json", "S02.json"]
