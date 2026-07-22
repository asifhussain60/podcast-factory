from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import _book_augment
from _book_augment import (
    _BLOCK_OPEN,
    EDITORIAL_LABEL,
    author_phase_book_augment,
    format_editorial_block,
    gate_editorial_block,
    insert_blocks,
)
from _book_edits import record_edit
from _book_voice import apply_author_companion_voice, revoice_gates


def _book(tmp_path: Path, book_md: str, toc: dict | None = None) -> Path:
    bd = tmp_path / "book_dir"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(book_md, encoding="utf-8")
    if toc is not None:
        (bd / "book" / "book-toc.json").write_text(json.dumps(toc), encoding="utf-8")
    return bd


_BASE = (
    "# The Book\n\n"
    "## 1. On Knowledge\n\nSeek knowledge from cradle to grave. It benefits the seeker.\n\n"
    "## 2. On Patience\n\nPatience is light. The patient are rewarded without measure.\n"
)


# ─── Editorial-block gate ───────────────────────────────────────────────────
def test_gate_rejects_short_block() -> None:
    ok, reasons = gate_editorial_block("too short")
    assert ok is False and "short" in reasons[0]


def test_gate_accepts_reasonable_block() -> None:
    note = (
        "This chapter connects to the well-known teaching that seeking knowledge is an "
        "obligation, echoed across the reliable narrations preserved in the tradition."
    )
    ok, reasons = gate_editorial_block(note)
    assert ok is True, reasons


def test_gate_rejects_meta_commentary() -> None:
    ok, reasons = gate_editorial_block(
        "As an AI, I cannot verify this teaching but here is the editorial note anyway for you."
    )
    assert ok is False


def test_format_block_is_labeled_and_fenced() -> None:
    block = format_editorial_block("A grounded contextual note about the chapter's teaching here.")
    assert _BLOCK_OPEN in block
    assert EDITORIAL_LABEL in block
    assert block.count("<!-- editorial:begin -->") == 1


# ─── Insertion is idempotent + non-destructive ──────────────────────────────
def test_insert_blocks_appends_after_chapter() -> None:
    blocks = {1: format_editorial_block("A grounded note for chapter one here now.")}
    out = insert_blocks(_BASE, blocks)
    assert "Seek knowledge from cradle to grave." in out  # base preserved
    assert EDITORIAL_LABEL in out
    # block sits under chapter 1, before chapter 2
    assert out.index(EDITORIAL_LABEL) < out.index("## 2. On Patience")


def test_insert_blocks_is_idempotent() -> None:
    blocks = {1: format_editorial_block("A grounded note for chapter one here now.")}
    once = insert_blocks(_BASE, blocks)
    twice = insert_blocks(once, blocks)
    assert once == twice
    assert twice.count("<!-- editorial:begin -->") == 1


# ─── Augment stage with an injected generator ───────────────────────────────
def test_augment_adds_only_gated_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bd = _book(tmp_path, _BASE, toc={"chapters": []})
    monkeypatch.setattr(
        _book_augment,
        "_load_all_kb_atoms",
        lambda: [
            {
                "id": "d:1",
                "type": "doctrine",
                "body": {
                    "text_en": "seeking beneficial knowledge from cradle "
                    "to grave is a lifelong obligation for every believer"
                },
            }
        ],
    )

    def fake_gen(title, chapter_text, atoms, book_dir, label, log):
        if "Knowledge" in title:
            return (
                "This note grounds the chapter's teaching in the wider tradition of "
                "seeking beneficial knowledge as a lifelong obligation for every believer."
            )
        return "NONE"  # chapter 2 offers nothing

    author_phase_book_augment(bd, log=lambda *a: None, generator=fake_gen)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert out.count("<!-- editorial:begin -->") == 1  # only chapter 1 got a block
    assert "Seek knowledge from cradle to grave." in out  # base intact
    report = json.loads((bd / "_system" / "book-augment-report.json").read_text())
    assert report["accepted"] == 1


def test_augment_drops_doctrinally_bad_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bd = _book(tmp_path, _BASE, toc={"chapters": []})
    monkeypatch.setattr(
        _book_augment,
        "_load_all_kb_atoms",
        lambda: [{"id": "d:1", "type": "doctrine", "body": {"text_en": "knowledge and patience are grounded here"}}],
    )
    monkeypatch.setattr(_book_augment, "gate_editorial_block", lambda *a: (False, ["doctrinal P0: T3:test"]))
    author_phase_book_augment(
        bd,
        log=lambda *a: None,
        generator=lambda *a, **k: "some note that will be gated out by the stubbed gate here now",
    )
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "<!-- editorial:begin -->" not in out


# ─── Grounding-corpus construction (regression: empty-corpus bug) ────────────
# KB atoms store their text at ``body.text_en`` (doctrine/hadith/quran/quote all
# share this shape). A prior corpus builder read only top-level
# ``text``/``arabic``/``translation``, so the grounding corpus came out EMPTY for
# every real book and the model always returned NONE. These guard the real schema.
_REAL_ATOM = {
    "type": "quran",
    "body": {
        "surah": 14,
        "ayah": 7,
        "text_en": "# Heading\n\nIf you are grateful, I will surely increase you in favor ⟪ar:لئن شكرتم⟫.",
    },
}


def test_atom_text_reads_body_text_en() -> None:
    from _book_augment import atom_text

    t = atom_text(_REAL_ATOM)
    assert "grateful" in t and "increase you in favor" in t
    assert "#" not in t  # markdown header stripped
    assert "⟪" not in t and "ar:" not in t  # inline markup stripped


def test_augment_prompt_corpus_nonempty_from_real_schema() -> None:
    from _book_augment import _augment_prompt

    prompt = _augment_prompt("A Chapter", "Body about gratitude.", [_REAL_ATOM])
    assert "(none)" not in prompt  # the corpus is populated
    assert "increase you in favor" in prompt  # the atom text reached it


def test_augment_prompt_corpus_empty_only_when_no_atoms() -> None:
    from _book_augment import _augment_prompt

    assert "(none)" in _augment_prompt("A Chapter", "Body.", [])


# ─── Voice re-voice gates + revert ──────────────────────────────────────────
def test_revoice_gates_flag_arabic_loss() -> None:
    base = "The saying is العلم and it teaches patience through knowledge."
    revoiced = "The saying teaches patience through knowledge for the seeker who perseveres."
    findings = revoice_gates(base, revoiced)
    assert any("Arabic" in f for f in findings)


def test_revoice_gates_pass_when_faithful() -> None:
    base = "Patience is light and the patient are rewarded without measure by the Most Merciful."
    revoiced = "Patience is light, and the patient are rewarded without measure by the Most Merciful."
    assert revoice_gates(base, revoiced) == []


def test_voice_reverts_bad_chapter_keeps_good(tmp_path: Path) -> None:
    bd = _book(tmp_path, _BASE)

    def fake_revoicer(title, base_text, book_dir, label, log, **kw):
        if "Knowledge" in title:
            return base_text + " I say this to you plainly."  # faithful expansion -> kept
        return "short"  # teaching loss -> reverted

    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=fake_revoicer)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "I say this to you plainly." in out  # chapter 1 kept
    assert "The patient are rewarded without measure." in out  # chapter 2 base preserved
    report = json.loads((bd / "_system" / "book-voice-report.json").read_text())
    assert report["revoiced"] == 1 and report["reverted"] == 1
    # The per-chapter record is what makes a failure diagnosable without forensics.
    statuses = {c["title"]: c["status"] for c in report["chapters"]}
    assert statuses["On Knowledge"] == "adapted" and statuses["On Patience"] == "reverted"
    patience = next(c for c in report["chapters"] if c["title"] == "On Patience")
    assert any("teaching" in g or "abridged" in g for g in patience["gates"])


# ─── Composer authority: an authored chapter is never regenerated ────────────
def test_voice_leaves_a_composer_authored_chapter_alone(tmp_path: Path) -> None:
    """The chapter is the author's, so no model is asked to rewrite it.

    Before 2026-07-21 every stage re-composed every chapter and the replay then
    restored the human's text on top — so the fresh prose was paid for and thrown
    away. One rebuild regenerated all nine chapters to keep one.
    """
    bd = _book(tmp_path, _BASE)
    record_edit(bd, chapter_key="on knowledge", body_md="The author's own paragraph, kept verbatim.")
    seen: list[str] = []

    def fake_revoicer(title, base_text, book_dir, label, log, **kw):
        seen.append(title)
        return base_text + " I say this to you plainly."

    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=fake_revoicer)
    assert seen == ["On Patience"]  # the model never saw the authored chapter
    report = json.loads((bd / "_system" / "book-voice-report.json").read_text())
    assert {c["title"]: c["status"] for c in report["chapters"]}["On Knowledge"] == "composer-edit"


def test_force_really_does_re_voice_a_composer_authored_chapter(tmp_path: Path) -> None:
    bd = _book(tmp_path, _BASE)
    record_edit(bd, chapter_key="on knowledge", body_md="The author's own paragraph.")
    seen: list[str] = []

    def fake_revoicer(title, base_text, book_dir, label, log, **kw):
        seen.append(title)
        return base_text + " I say this to you plainly."

    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=fake_revoicer, force=True)
    assert seen == ["On Knowledge", "On Patience"]


def test_augment_adds_no_aside_to_a_composer_authored_chapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bd = _book(tmp_path, _BASE, toc={"chapters": []})
    record_edit(bd, chapter_key="on knowledge", body_md="The author's own paragraph.")
    monkeypatch.setattr(
        _book_augment,
        "_load_all_kb_atoms",
        lambda: [{"id": "d:1", "type": "doctrine", "body": {"text_en": "seeking knowledge is a lifelong obligation"}}],
    )

    def fake_gen(title, chapter_text, atoms, book_dir, label, log):
        raise AssertionError(f"the generator must not be called for {title!r}")

    author_phase_book_augment(bd, log=lambda *a: None, generator=fake_gen)
    report = json.loads((bd / "_system" / "book-augment-report.json").read_text())
    assert report["chapters_composer_authored"] == 1


def test_two_chapters_sharing_a_title_get_their_own_bodies() -> None:
    """Keying by heading text gave both the last block and the first one's body."""
    from _book_augment import _chapter_body

    same = "# B\n\n## 1. On Patience\n\nFirst body here.\n\n## 2. On Patience\n\nSecond body here.\n"
    assert _chapter_body(same, 1) == "First body here."
    assert _chapter_body(same, 2) == "Second body here."
    out = insert_blocks(same, {2: format_editorial_block("A grounded note for the second chapter here now.")})
    assert out.count("<!-- editorial:begin -->") == 1
    assert out.index(EDITORIAL_LABEL) > out.index("Second body here.")


def test_voice_preserves_editorial_asides(tmp_path: Path) -> None:
    with_aside = _BASE.replace(
        "It benefits the seeker.",
        "It benefits the seeker.\n\n" + format_editorial_block("A grounded aside note for this chapter now."),
    )
    bd = _book(tmp_path, with_aside)
    apply_author_companion_voice(
        bd,
        log=lambda *a: None,
        revoicer=lambda title, base, *a: base,  # identity -> always kept
    )
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "<!-- editorial:begin -->" in out  # aside survived the re-voice pass


# ─── Long-chapter windowing (regression: 2026-07-19 live failure) ────────────
# A 7,258-word chapter came back ~150 words under the anti-abridgement gate and
# reverted whole; its 14,384-word neighbour came back 98.6% identical because the
# model had degraded into copying. Both are length failures, so long chapters are
# split and gated per window.
def _long_book(tmp_path: Path, words_per_chapter: int) -> Path:
    para = " ".join(["knowledge"] * 100) + "."
    body = "\n\n".join([para] * (words_per_chapter // 100))
    return _book(tmp_path, f"# The Book\n\n## 1. On Knowledge\n\n{body}\n")


def test_long_chapter_is_split_into_windows(tmp_path: Path) -> None:
    from _book_voice import _LONG_CHAPTER_WORDS

    bd = _long_book(tmp_path, 8000)
    labels: list[str] = []

    def fake_revoicer(title, base_text, book_dir, label, log, **kw):
        labels.append(label)
        assert len(base_text.split()) < _LONG_CHAPTER_WORDS  # no window is oversized
        return base_text + " I say this plainly to you."

    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=fake_revoicer)
    assert len(labels) > 1 and labels[0].endswith("-part-01")
    report = json.loads((bd / "_system" / "book-voice-report.json").read_text())
    chapter = report["chapters"][0]
    assert chapter["windows"] == len(labels) and chapter["status"] == "adapted"


def test_short_chapter_is_not_split(tmp_path: Path) -> None:
    bd = _book(tmp_path, _BASE)
    labels: list[str] = []

    def fake_revoicer(title, base_text, book_dir, label, log, **kw):
        labels.append(label)
        return base_text + " I say this plainly to you."

    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=fake_revoicer)
    assert labels == ["voice-01", "voice-02"]  # no -part- suffix on short chapters


def test_one_bad_window_does_not_revert_the_whole_chapter(tmp_path: Path) -> None:
    bd = _long_book(tmp_path, 8000)
    seen: list[str] = []

    def fake_revoicer(title, base_text, book_dir, label, log, **kw):
        seen.append(label)
        if len(seen) == 1:
            return "short"  # first window fails its gate
        return base_text + " I say this plainly to you."

    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=fake_revoicer)
    report = json.loads((bd / "_system" / "book-voice-report.json").read_text())
    chapter = report["chapters"][0]
    assert chapter["status"] == "partial"
    assert 0 < chapter["windows_kept"] < chapter["windows"]
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "I say this plainly to you." in out  # the good windows survived


def test_near_identical_output_is_recorded_as_a_warning(tmp_path: Path) -> None:
    bd = _book(tmp_path, _BASE)
    apply_author_companion_voice(
        bd,
        log=lambda *a: None,
        revoicer=lambda title, base, *a, **k: base,  # the copy failure, exactly
    )
    report = json.loads((bd / "_system" / "book-voice-report.json").read_text())
    assert all(c["warnings"] for c in report["chapters"])
    assert "near-identical" in report["chapters"][0]["warnings"][0]


def test_only_filter_leaves_other_chapters_byte_identical(tmp_path: Path) -> None:
    bd = _book(tmp_path, _BASE)
    before = (bd / "book" / "book.md").read_text(encoding="utf-8")
    titles: list[str] = []

    def fake_revoicer(title, base_text, book_dir, label, log, **kw):
        titles.append(title)
        return base_text + " I say this plainly to you."

    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=fake_revoicer, only=[2])
    after = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert titles == ["On Patience"]  # chapter 1 never reached the model
    assert "Seek knowledge from cradle to grave. It benefits the seeker." in after
    assert before.split("## 2.")[0].strip() == after.split("## 2.")[0].strip()  # chapter 1 untouched
    report = json.loads((bd / "_system" / "book-voice-report.json").read_text())
    assert report["chapters"][0]["status"] == "skipped"


# ─── Unified driver dispatch ────────────────────────────────────────────────
def test_compose_book_v2_runs_stages_per_knobs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import _book_pipeline_v2

    bd = tmp_path / "bd"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "series-config.yaml").write_text(
        "book_pipeline_v2: true\nbook_augmentation: source_only\nbook_voice: author_companion\n",
        encoding="utf-8",
    )
    calls: list[str] = []
    monkeypatch.setattr(
        _book_pipeline_v2,
        "author_translation_edition_compose",
        None,
        raising=False,
    )
    # patch the lazily-imported names by injecting fakes into the modules they come from
    import _book_augment as aug
    import _book_voice as voice
    import _translation_edition

    monkeypatch.setattr(
        _translation_edition,
        "author_translation_edition_compose",
        lambda bd, **k: calls.append("base") or (Path(bd) / "book" / "book.md"),
    )
    monkeypatch.setattr(
        aug, "author_phase_book_augment", lambda bd, **k: calls.append("augment") or (Path(bd) / "book" / "book.md")
    )
    monkeypatch.setattr(
        voice, "apply_author_companion_voice", lambda bd, **k: calls.append("voice") or (Path(bd) / "book" / "book.md")
    )
    _book_pipeline_v2.compose_book_v2(bd, log=lambda *a: None)
    assert calls == ["base", "augment", "voice"]


def test_compose_book_v2_faithful_none_runs_base_then_fluency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import _book_augment as aug
    import _book_pipeline_v2
    import _book_voice as voice
    import _translation_edition

    bd = tmp_path / "bd"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "series-config.yaml").write_text(
        "book_pipeline_v2: true\ndeliverable_mode: translation_edition\n",
        encoding="utf-8",
    )
    calls: list[str] = []
    monkeypatch.setattr(
        _translation_edition,
        "author_translation_edition_compose",
        lambda bd, **k: calls.append("base") or (Path(bd) / "book" / "book.md"),
    )
    monkeypatch.setattr(voice, "apply_fluency_adapt", lambda bd, **k: calls.append("fluency"))
    monkeypatch.setattr(aug, "author_phase_book_augment", lambda bd, **k: calls.append("augment"))
    monkeypatch.setattr(voice, "apply_author_companion_voice", lambda bd, **k: calls.append("voice"))
    _book_pipeline_v2.compose_book_v2(bd, log=lambda *a: None)
    # {none, faithful} -> base + fluency de-calque, no augment/re-voice
    assert calls == ["base", "fluency"]


def test_fluency_reverts_calqued_drift(tmp_path: Path) -> None:
    from _book_voice import apply_fluency_adapt

    bd = _book(tmp_path, _BASE)

    def fake_adapter(title, base_text, book_dir, label, log, **kw):
        if "Knowledge" in title:
            return base_text.replace("Seek", "You should seek")  # faithful polish -> kept
        return "x"  # teaching loss -> reverted

    apply_fluency_adapt(bd, log=lambda *a: None, adapter=fake_adapter)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "You should seek knowledge" in out  # chapter 1 kept
    assert "The patient are rewarded without measure." in out  # chapter 2 reverted to base
    report = json.loads((bd / "_system" / "book-fluency-report.json").read_text())
    assert report["adapted"] == 1 and report["reverted"] == 1


def test_targeted_rerun_keeps_the_prior_runs_records(tmp_path: Path) -> None:
    """A pass run with only= must not erase the full run's per-chapter records.

    Writing the `skipped` markers straight out made the report say "0 adapted,
    8 skipped" for a book whose chapters had all been adapted an hour earlier —
    which reads as "the pass did nothing" and misled a reviewer into exactly
    that conclusion on 2026-07-20.
    """
    bd = _book(tmp_path, _BASE)
    good = lambda title, base, *a, **k: base + " I say this plainly to you."  # noqa: E731
    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=good)
    full = json.loads((bd / "_system" / "book-voice-report.json").read_text())
    assert full["revoiced"] == 2

    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=good, only=[2])
    after = json.loads((bd / "_system" / "book-voice-report.json").read_text())
    statuses = {c["title"]: c["status"] for c in after["chapters"]}
    assert statuses["On Knowledge"] == "adapted"  # carried through, not "skipped"
    assert after["revoiced"] == 2


# ─── Report honesty after the Composer-edit replay (RCA-001) ─────────────────
# The fluency/voice reports are written BEFORE the replay, so "adapted" is a
# claim about a moment the replay can invalidate in the same compose. On
# 2026-07-21 exactly that report — `adapted: 9` with 8 chapters discarded
# minutes later — shipped un-articulated prose through every downstream gate.
_GOOD = lambda title, base, *a, **k: base + " I say this plainly to you."  # noqa: E731


def test_replay_overwrite_restamps_adapted_as_overwritten(tmp_path: Path) -> None:
    from _book_edits import apply_composer_edits
    from _book_pass_reports import reconcile_reports_after_replay
    from _book_voice import apply_fluency_adapt

    bd = _book(tmp_path, _BASE)
    apply_fluency_adapt(bd, log=lambda *a: None, adapter=_GOOD)
    # The save lands AFTER the pass adapted the chapter — the RCA-001 shape.
    record_edit(bd, chapter_key="on knowledge", body_md="The author's own paragraph, kept verbatim.")
    replay = apply_composer_edits(bd, log=lambda *a: None)
    assert reconcile_reports_after_replay(bd, replay, log=lambda *a: None) == 1

    report = json.loads((bd / "_system" / "book-fluency-report.json").read_text())
    chapters = {c["title"]: c for c in report["chapters"]}
    assert chapters["On Knowledge"]["status"] == "adapted-then-overwritten"
    assert chapters["On Knowledge"]["pre_replay_status"] == "adapted"
    assert chapters["On Patience"]["status"] == "adapted"  # untouched by the replay
    # Top-level counts only ever count SURVIVING work.
    assert report["adapted"] == 1
    assert report["overwritten_by_replay"] == 1
    assert report["schema"] == "podcast.book-fluency/v4"


def test_reconcile_is_a_noop_without_applied_edits(tmp_path: Path) -> None:
    from _book_edits import apply_composer_edits
    from _book_pass_reports import reconcile_reports_after_replay
    from _book_voice import apply_fluency_adapt

    bd = _book(tmp_path, _BASE)
    apply_fluency_adapt(bd, log=lambda *a: None, adapter=_GOOD)
    replay = apply_composer_edits(bd, log=lambda *a: None)  # no edits saved
    assert reconcile_reports_after_replay(bd, replay, log=lambda *a: None) == 0
    report = json.loads((bd / "_system" / "book-fluency-report.json").read_text())
    assert report["adapted"] == 2 and all(c["status"] == "adapted" for c in report["chapters"])


def test_merge_cannot_resurrect_stale_adapted_for_an_edited_chapter(tmp_path: Path) -> None:
    """A targeted --force re-run must not inherit a live "adapted" claim for a
    chapter the Composer now owns — the replay overwrites that chapter's text."""
    bd = _book(tmp_path, _BASE)
    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=_GOOD)
    record_edit(bd, chapter_key="on knowledge", body_md="The author's own paragraph.")

    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=_GOOD, only=[2], force=True)
    report = json.loads((bd / "_system" / "book-voice-report.json").read_text())
    chapters = {c["title"]: c for c in report["chapters"]}
    assert chapters["On Knowledge"]["status"] == "adapted-then-overwritten"  # not "adapted"
    assert chapters["On Knowledge"]["pre_replay_status"] == "adapted"
    assert report["revoiced"] == 1
    assert report["overwritten_by_replay"] == 1


def test_compose_v2_warns_loudly_when_replay_discards_adapted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import _book_frontmatter
    import _book_pipeline_v2
    import _book_voice as voice
    import _translation_edition

    bd = _book(tmp_path, _BASE)
    (bd / "_system" / "series-config.yaml").write_text(
        "book_pipeline_v2: true\ndeliverable_mode: translation_edition\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        _translation_edition,
        "author_translation_edition_compose",
        lambda bd_, **k: Path(bd_) / "book" / "book.md",  # book.md already on disk
    )
    monkeypatch.setattr(voice, "_fluency_chapter", _GOOD)
    monkeypatch.setattr(_book_frontmatter, "apply_introduction", lambda bd_, **k: {"applied": False})
    record_edit(bd, chapter_key="on knowledge", body_md="The author's own paragraph.")

    logs: list[str] = []
    # --force re-composes over the author's chapter; the replay then restores it.
    _book_pipeline_v2.compose_book_v2(bd, log=logs.append, force=True)
    assert any("WARNING" in m and "DISCARDED" in m for m in logs)
    report = json.loads((bd / "_system" / "book-fluency-report.json").read_text())
    assert {c["title"]: c["status"] for c in report["chapters"]}["On Knowledge"] == "adapted-then-overwritten"
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "The author's own paragraph." in out  # the replay still won


def test_reconcile_failure_does_not_relabel_the_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A reconcile crash after a SUCCESSFUL replay must be recorded as its own
    skip — sharing the replay's try block recorded it as a "composer-edits" skip,
    telling the operator their edits were dropped when the replay had applied
    them, while silently keeping the stale "adapted" the reconcile exists to end.
    """
    import _book_frontmatter
    import _book_pass_reports
    import _book_pipeline_v2
    import _book_voice as voice
    import _translation_edition

    bd = _book(tmp_path, _BASE)
    (bd / "_system" / "series-config.yaml").write_text(
        "book_pipeline_v2: true\ndeliverable_mode: translation_edition\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        _translation_edition,
        "author_translation_edition_compose",
        lambda bd_, **k: Path(bd_) / "book" / "book.md",
    )
    monkeypatch.setattr(voice, "_fluency_chapter", _GOOD)
    monkeypatch.setattr(_book_frontmatter, "apply_introduction", lambda bd_, **k: {"applied": False})
    record_edit(bd, chapter_key="on knowledge", body_md="The author's own paragraph.")

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(_book_pass_reports, "reconcile_reports_after_replay", boom)
    _book_pipeline_v2.compose_book_v2(bd, log=lambda *a: None, force=True)

    skips = json.loads((bd / "_system" / "compose-skips.json").read_text())["skips"]
    steps = [s["step"] for s in skips]
    assert "report-reconcile" in steps  # the failure is named for what actually failed
    assert "composer-edits" not in steps  # the successful replay is not disowned
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "The author's own paragraph." in out  # the replay's work stands
