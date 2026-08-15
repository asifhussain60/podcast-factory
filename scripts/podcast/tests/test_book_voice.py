"""0book-voice — the author-companion re-voice pass's deterministic gates.

These tests pin the fidelity gates a re-voiced chapter must survive before it
replaces the faithful base, above all the narrative-opening gate: a chapter must
begin as a chapter, not with the narrator announcing the act of narration.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _book_voice import narrative_opening_findings, revoice_gates  # noqa: E402


# ─── the reported bug, verbatim ──────────────────────────────────────────────
def test_the_reported_sentence_trips_the_gate() -> None:
    """Found live 2026-07-19 on the-master-and-the-disciple, chapter opening."""
    text = (
        "Let me set down, as faithfully as I can, how my Master opened the "
        "matter — the first of the causes of the manifest order, and how its "
        "creation began."
    )
    assert narrative_opening_findings(text)


# ─── other real instances found across the corpus ────────────────────────────
def test_let_me_tell_you_how_trips_the_gate() -> None:
    text = "Let me tell you how a certain conversation reached us, because everything about the way you read it depends on hearing it the way it was first spoken."
    assert narrative_opening_findings(text)


def test_i_want_to_tell_you_trips_the_gate() -> None:
    text = "I want to tell you what happened next, because everything that follows in this book turns on it."
    assert narrative_opening_findings(text)


def test_before_i_set_down_trips_the_gate() -> None:
    text = "Before I set down a single word of what follows, let me speak the words I have always begun with, for they are not ornament but the doorway itself."
    assert narrative_opening_findings(text)


def test_i_held_this_book_back_trips_the_gate() -> None:
    text = "I held this book back from the press for a long time, and I want to tell you why before I tell you anything else."
    assert narrative_opening_findings(text)


# ─── the voice is intentionally first-person and warm — don't over-match ─────
def test_a_chapter_that_simply_begins_in_first_person_is_not_flagged() -> None:
    """The prompt explicitly wants first-person, warm address — only the specific
    'I am now going to narrate' framing move is forbidden, not first person itself."""
    text = "I remember the courtyard well, the smell of rain on stone, and the old man who waited there for us."
    assert narrative_opening_findings(text) == []


def test_let_me_used_mid_sentence_for_emphasis_is_not_flagged() -> None:
    """'Let me be clear' as emphasis, not narrated at the chapter's very start,
    must not trip the gate — position matters, not just the phrase."""
    text = "The courtyard was quiet. Let me be clear: nothing about that silence was peaceful."
    assert narrative_opening_findings(text) == []


def test_let_me_be_clear_at_the_opening_is_not_flagged() -> None:
    """Emphasis, not narration-announcement — 'let me be clear' is not in the
    forbidden verb set (tell/set down/speak/recount/say)."""
    text = "Let me be clear about what happened that morning: nothing was as it seemed."
    assert narrative_opening_findings(text) == []


def test_a_short_chapter_opening_is_not_flagged() -> None:
    assert narrative_opening_findings("The rain had not stopped in three days.") == []


# ─── wired into the full gate set ─────────────────────────────────────────────
def test_revoice_gates_reverts_a_narrative_announcement_opening() -> None:
    base = "The teacher began his lesson at dawn, as he always did, speaking first of patience."
    revoiced = "Let me tell you how the teacher began his lesson at dawn, as he always did, speaking first of patience."
    gate = revoice_gates(base, revoiced)
    assert any("narrative-announcement" in f for f in gate)


def test_revoice_gates_keeps_a_clean_re_voice() -> None:
    base = "The teacher began his lesson at dawn, as he always did, speaking first of patience."
    revoiced = "The teacher always began at dawn, and that morning he spoke first of patience."
    assert revoice_gates(base, revoiced) == []


# ─── the gate is differential: only an ADDED announcement is a finding ───────
def test_an_announcement_the_author_wrote_is_not_the_re_voices_fault() -> None:
    """Found live 2026-08-01 on Islamic/ayyuhal-walad, chapter 2.

    The source itself opens "Let me tell you of a man among the Children of
    Israel". Preserving that is fidelity — reverting it left the chapter
    un-articulated and made the articulation report permanently red.
    """
    base = (
        "My dear son, be firmly convinced of this: without effort you will not "
        "find its reward.\n\nLet me tell you of a man among the Children of "
        "Israel who worshipped Allah the Exalted with great devotion."
    )
    revoiced = (
        "My dear son, hold firmly to this: you will not find the reward until "
        "you have made the effort.\n\nLet me tell you of a man among the "
        "Children of Israel who worshipped Allah the Exalted with great devotion."
    )
    assert narrative_opening_findings(revoiced, base) == []
    assert not any("narrative-announcement" in f for f in revoice_gates(base, revoiced))


def test_an_announcement_the_re_voice_invented_is_still_caught() -> None:
    """The differential must not become a blanket amnesty — a base that opens
    plainly and a re-voice that announces the telling is the original bug."""
    base = "The teacher began his lesson at dawn, as he always did."
    revoiced = "Let me tell you how the teacher began his lesson at dawn, as he always did."
    assert narrative_opening_findings(revoiced, base)


def test_a_different_announcement_over_an_announcing_base_is_still_permitted() -> None:
    """The author already frames the telling; which words the re-voice uses to
    keep that frame is a craft choice, not a fidelity breach."""
    base = "Let me set down what happened that morning, for it is the root of everything after."
    revoiced = "Let me recount what happened that morning, for it is the root of everything after."
    assert narrative_opening_findings(revoiced, base) == []


def test_the_single_argument_contract_still_flags_a_bare_announcement() -> None:
    """Callers that pass no base keep the older, stricter reading."""
    assert narrative_opening_findings("Let me tell you how it began, and why it matters.")


def test_revoice_gates_reverts_a_leaked_articulation_notes_marker() -> None:
    """REQ-BA-160 belt-and-suspenders: a marker that survives extraction (e.g. a
    malformed block missing its END-NOTES terminator) must never ship."""
    base = "The teacher began his lesson at dawn, as he always did, speaking first of patience."
    revoiced = base + "\n\n===ARTICULATION-NOTES===\nAMBIGUITY: something\n"
    gate = revoice_gates(base, revoiced)
    assert any("leaked articulation" in f for f in gate)


# ─── prompt / frame agreement ─────────────────────────────────────────────────
def test_articulation_prompt_does_not_contradict_its_own_frame_directive() -> None:
    """The articulation prompt must not forbid the person its directives just mandated.

    A predecessor prompt hardcoded a register clause independent of the frame
    directive, and a first-person book was told to narrate first person and then,
    in the same prompt, forbidden from doing it. `_articulation_prompt` has no
    such hardcoded clause — person comes ONLY from `frame_prompt_directive` — so
    this is now a structural guarantee rather than something each route must get
    right on its own.
    """
    from _book_voice_prompts import _articulation_prompt

    for frame in ("first_person_author", "participant_narrator"):
        prompt = _articulation_prompt("Ch", "text", frame=frame, narrator="Salih")
        assert "Narrate in the FIRST PERSON" in prompt, frame
        assert "Narrate in the THIRD PERSON" not in prompt, frame

    for frame in ("transmitted_report", "external_narrator", ""):
        prompt = _articulation_prompt("Ch", "text", frame=frame)
        if frame:
            assert "Narrate in the THIRD PERSON" in prompt, frame
        assert "Narrate in the FIRST PERSON" not in prompt, frame


def test_fluency_and_rearticulate_share_the_same_prompt_builder() -> None:
    """0book-fluency (automatic) and the Rearticulator (on-demand) must build from
    the SAME function object — the guarantee that the two routes cannot drift
    apart, per docs/standards/book-articulation.md."""
    from _book_voice_prompts import _articulation_prompt
    from rearticulate_chapter import _articulation_prompt as rearticulate_prompt_fn

    assert rearticulate_prompt_fn is _articulation_prompt
    assert rearticulate_prompt_fn("Ch", "some prose", frame="external_narrator") == _articulation_prompt(
        "Ch", "some prose", frame="external_narrator"
    )


def test_articulation_prompt_carries_the_notes_block_instruction() -> None:
    """REQ-BA-160: the prompt must teach the out-of-band notes format so a pass
    never writes an ambiguity/comprehension/terminology note into the prose."""
    from _book_voice_prompts import _articulation_prompt

    prompt = _articulation_prompt("Ch", "text")
    assert "===ARTICULATION-NOTES===" in prompt
    assert "REQ-BA-160" in prompt


def test_articulation_prompt_names_the_defect_the_source_actually_has() -> None:
    """A book WRITTEN in English is not calqued, and saying it is aims the pass
    at a defect that is not there.

    `spiritual-ethos` is fluent academic English whose difficulty is long
    periodic sentences and unexplained specialist vocabulary. Told to hunt for
    Arabic calques it would find none and change little. Translated sources keep
    the original wording, which is why this is a branch and not a rewrite.
    """
    from _book_voice_prompts import _articulation_prompt

    english = _articulation_prompt("Ch", "text", source_language="en")
    assert "already fluent English" in english
    assert "Do not hunt for calques" in english
    assert "Arabic-calqued draft" not in english

    for lang in ("ar", "ur", ""):
        translated = _articulation_prompt("Ch", "text", source_language=lang)
        assert "Arabic-calqued draft" in translated, lang
        assert "already fluent English" not in translated, lang

    # The contract itself is identical on both sides — only the diagnosis moves.
    for prompt in (english, translated):
        assert "REQ-BA-010..160" in prompt
        assert "REQ-BA-020" in prompt


def test_source_language_defaults_do_not_mislabel_a_translation(tmp_path) -> None:
    """Absent `source_language`, a book declaring a TARGET language is still a
    translation and must not be told its source is already English."""
    from _content_profile import source_language

    book = tmp_path / "book"
    (book / "_system").mkdir(parents=True)
    cfg = book / "_system" / "series-config.yaml"

    cfg.write_text("content_profile: islamic_scholarly\n")
    assert source_language(book) == "en"

    cfg.write_text("target_language: en\n")
    assert source_language(book) == ""

    cfg.write_text("source_language: AR\n")
    assert source_language(book) == "ar"


# ── _merge_records: the superseded chain keeps its origin ────────────────────
# RCA-001 follow-up: a composer-edit record used to carry the PRIOR RUN's status
# verbatim, so from the second run onward superseded_status chained
# "composer-edit" onto itself and the "was adapted before the takeover" origin —
# the fact the field exists to preserve, and the fact the Composer's
# articulation guard classifies by — was erased.


def test_merge_records_carries_superseded_origin_through_repeat_runs() -> None:
    from _book_pass_reports import merge_records

    adapted = [{"title": "T", "status": "adapted", "windows": 1, "windows_kept": 1}]
    takeover = [{"title": "T", "status": "composer-edit", "windows": 0, "windows_kept": 0}]
    run1 = merge_records(adapted, takeover)
    assert run1[0]["superseded_status"] == "adapted"
    run2 = merge_records(run1, takeover)
    assert run2[0]["superseded_status"] == "adapted"  # NOT "composer-edit"
    run3 = merge_records(run2, takeover)
    assert run3[0]["superseded_status"] == "adapted"


def test_merge_records_takeover_before_any_adaptation_stays_composer_edit() -> None:
    from _book_pass_reports import merge_records

    never_adapted = [{"title": "T", "status": "composer-edit", "windows": 0, "windows_kept": 0}]
    takeover = [{"title": "T", "status": "composer-edit", "windows": 0, "windows_kept": 0}]
    run2 = merge_records(never_adapted, takeover)
    # No adaptation in the history: the chain resolves to composer-edit, which
    # the articulation guard treats as "frozen before articulation succeeded".
    assert run2[0]["superseded_status"] == "composer-edit"


def test_the_introduction_is_never_touched_by_a_prose_pass(tmp_path: Path) -> None:
    """It is APPARATUS: authored under the articulation register already, with no
    source to be faithful to, so the fidelity gates judge it on evidence that does
    not apply.

    During a compose it is not there yet. Standalone on a finished book it IS
    there and is the FIRST `## ` section — so `only=[1]` would mean the
    introduction rather than chapter one, which is the accident this prevents.
    """
    from _book_edits import anchor_key
    from _book_frontmatter import INTRO_HEADING
    from _book_voice import _INTRODUCTION_KEY, apply_fluency_adapt

    assert _INTRODUCTION_KEY == anchor_key(INTRO_HEADING)

    bd = tmp_path / "b"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(
        f"# T\n\n{INTRO_HEADING}\n\nThe edition's own introduction.\n\n"
        "## 1. The Sealed Lamp\n\nThe chapter's first-person lecture.\n",
        encoding="utf-8",
    )

    seen: list[str] = []

    def adapter(title, body, *a, **k):
        seen.append(title)
        return "REWRITTEN " + body

    apply_fluency_adapt(bd, log=lambda _m: None, adapter=adapter)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")

    assert "The edition's own introduction." in out
    assert "REWRITTEN The edition's own introduction." not in out
    assert "Introduction to the Book" not in seen


def test_the_legacy_bare_introduction_heading_is_also_never_touched(tmp_path: Path) -> None:
    """mukhtasar-ul-asar-1/2 (pre-v2 legacy books) carry `## Introduction`, not
    `## Introduction to the Book`. Found live 2026-08-15: the fluency pass
    treated it as an ordinary numbered section, rewrote it, and dropped the
    `<!-- edition-intro:end -->` marker the Composer needs to know where the
    apparatus ends and chapter 1 begins."""
    from _book_voice import apply_fluency_adapt

    bd = tmp_path / "b"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(
        "# T\n\n<!-- edition-intro:begin -->\n## Introduction\n\n"
        "The edition's own introduction.\n<!-- edition-intro:end -->\n\n"
        "## 1. The Sealed Lamp\n\nThe chapter's first-person lecture.\n",
        encoding="utf-8",
    )

    seen: list[str] = []

    def adapter(title, body, *a, **k):
        seen.append(title)
        return "REWRITTEN " + body

    apply_fluency_adapt(bd, log=lambda _m: None, adapter=adapter)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")

    assert "The edition's own introduction." in out
    assert "REWRITTEN The edition's own introduction." not in out
    assert "<!-- edition-intro:end -->" in out
    assert "Introduction" not in seen


# ── record_rearticulation: the report tells the truth after an on-demand fix ──
# `rearticulate_chapter` put articulated prose back, but the pass report was
# written by the LAST COMPOSE and still described what the replay had discarded.
# The Composer computes its articulation warning from that report, so the tool
# fixed the book and the reader went on being told it had not.


def _fluency_report(tmp_path: Path, records: list[dict]) -> Path:
    import json

    bd = tmp_path / "bk"
    (bd / "_system").mkdir(parents=True)
    path = bd / "_system" / "book-fluency-report.json"
    path.write_text(
        json.dumps(
            {
                "schema": "podcast.book-fluency/v5",
                "chapters": records,
                "adapted": sum(1 for r in records if r["status"] in ("adapted", "partial")),
                "reverted": 0,
                "overwritten_by_replay": sum(1 for r in records if r["status"] == "adapted-then-overwritten"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return bd


def _read(bd: Path) -> dict:
    import json

    return json.loads((bd / "_system" / "book-fluency-report.json").read_text(encoding="utf-8"))


def test_record_rearticulation_clears_the_overwritten_stamp(tmp_path: Path) -> None:
    from _book_pass_reports import record_rearticulation

    bd = _fluency_report(
        tmp_path,
        [
            {"title": "Knowledge That Will Not Save You", "status": "adapted"},
            {
                "title": "The Striving That Mercy Meets",
                "status": "adapted-then-overwritten",
                "pre_replay_status": "adapted",
            },
        ],
    )
    # The heading carries its printed ordinal; the report's titles do not. Both
    # sides go through anchor_key, which is what makes them the same chapter.
    assert record_rearticulation(bd, "2. The Striving That Mercy Meets", "adapted", log=lambda _m: None) == 1

    data = _read(bd)
    fixed = next(r for r in data["chapters"] if r["title"] == "The Striving That Mercy Meets")
    assert fixed["status"] == "composer-edit"
    assert fixed["superseded_status"] == "adapted"
    assert "pre_replay_status" not in fixed
    assert data["overwritten_by_replay"] == 0
    assert data["adapted"] == 1  # the other chapter; a takeover is not a kept claim


def test_a_rearticulated_chapter_is_no_longer_at_risk_in_the_composer(tmp_path: Path) -> None:
    """The point of the stamp: `articulationWarningsFrom` reads exactly these two
    fields, and a takeover whose superseded status is `adapted` is safe."""
    from _book_pass_reports import record_rearticulation

    bd = _fluency_report(tmp_path, [{"title": "T", "status": "adapted-then-overwritten"}])
    record_rearticulation(bd, "1. T", "adapted", log=lambda _m: None)
    rec = _read(bd)["chapters"][0]
    assert (rec["status"], rec["superseded_status"]) == ("composer-edit", "adapted")


def test_record_rearticulation_survives_a_later_targeted_rerun(tmp_path: Path) -> None:
    """Why the stamp is a takeover and not a bare `adapted`: the chapter now
    carries a Composer edit, so `merge_records` would demote a live `adapted`
    claim straight back to `adapted-then-overwritten` on the next `only=` run."""
    from _book_edits import anchor_key
    from _book_pass_reports import merge_records, record_rearticulation

    bd = _fluency_report(tmp_path, [{"title": "T", "status": "adapted-then-overwritten"}])
    record_rearticulation(bd, "1. T", "adapted", log=lambda _m: None)
    prior = _read(bd)["chapters"]

    rerun = [{"title": "T", "status": "skipped"}]
    merged = merge_records(prior, rerun, edited_keys={anchor_key("T")})
    assert merged[0]["status"] == "composer-edit"
    assert merged[0]["superseded_status"] == "adapted"


def test_record_rearticulation_refuses_to_launder_a_reverted_window(tmp_path: Path) -> None:
    from _book_pass_reports import record_rearticulation

    bd = _fluency_report(tmp_path, [{"title": "T", "status": "adapted-then-overwritten"}])
    assert record_rearticulation(bd, "1. T", "reverted", log=lambda _m: None) == 0
    assert _read(bd)["chapters"][0]["status"] == "adapted-then-overwritten"


def test_record_rearticulation_ignores_a_chapter_the_report_never_named(tmp_path: Path) -> None:
    from _book_pass_reports import record_rearticulation

    bd = _fluency_report(tmp_path, [{"title": "T", "status": "adapted"}])
    assert record_rearticulation(bd, "9. Somewhere Else", "adapted", log=lambda _m: None) == 0
    assert _read(bd)["chapters"][0]["status"] == "adapted"


# ─── model-emitted headings inside a chapter body ────────────────────────────
# Kitab al-Riyad, 2026-08-08: the source prints 113 of its own numbered divisions
# ("Chapter Two of Title IX"). The model formalised those plain lines as Markdown
# `##`, which made them indistinguishable from chapters — chapter 10 shipped as a
# 27-word stub with five sibling `##` sections carrying its body.
def test_model_emitted_body_headings_are_demoted_not_deleted() -> None:
    from _translation_text import subordinate_body_headings as _subordinate_body_headings

    body = "Opening prose.\n\n## The First Section\n\nIts prose.\n\n# A Title\n\nMore."
    out = _subordinate_body_headings(body)

    lines = out.splitlines()
    assert "## The First Section" not in lines, "must not stay at chapter level"
    assert "### The First Section" in lines, "the heading must survive, demoted"
    assert "### A Title" in lines
    assert not [ln for ln in lines if ln.startswith("## ") or ln.startswith("# ")]


def test_body_heading_demotion_leaves_prose_and_hashes_alone() -> None:
    from _translation_text import subordinate_body_headings as _subordinate_body_headings

    body = "He wrote #1 on the tablet.\n\nA line ending in #\n\n#### Already deep"
    assert _subordinate_body_headings(body) == body


def test_a_demoted_body_heading_no_longer_splits_as_a_chapter() -> None:
    """The compounding failure: `_CHAPTER_HEADING_RE` would treat a section as a
    chapter boundary on the NEXT run, truncating the real chapter's body."""
    from _book_voice import _CHAPTER_HEADING_RE
    from _translation_text import subordinate_body_headings as _subordinate_body_headings

    book = "## 10. Adam and the Law\n\nStub.\n\n" + _subordinate_body_headings(
        "## The First Section\n\nThe body that belongs to chapter 10."
    )
    heads = _CHAPTER_HEADING_RE.findall(book)

    assert heads == ["## 10. Adam and the Law"], "only the real chapter may split"
