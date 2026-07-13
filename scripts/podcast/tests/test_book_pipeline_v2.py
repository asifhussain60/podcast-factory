from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import _book_augment  # noqa: E402
import _book_voice  # noqa: E402
from _book_augment import (  # noqa: E402
    _BLOCK_OPEN,
    EDITORIAL_LABEL,
    author_phase_book_augment,
    format_editorial_block,
    gate_editorial_block,
    insert_blocks,
)
from _book_voice import apply_author_companion_voice, revoice_gates  # noqa: E402


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
    blocks = {"## 1. On Knowledge": format_editorial_block("A grounded note for chapter one here now.")}
    out = insert_blocks(_BASE, blocks)
    assert "Seek knowledge from cradle to grave." in out  # base preserved
    assert EDITORIAL_LABEL in out
    # block sits under chapter 1, before chapter 2
    assert out.index(EDITORIAL_LABEL) < out.index("## 2. On Patience")


def test_insert_blocks_is_idempotent() -> None:
    blocks = {"## 1. On Knowledge": format_editorial_block("A grounded note for chapter one here now.")}
    once = insert_blocks(_BASE, blocks)
    twice = insert_blocks(once, blocks)
    assert once == twice
    assert twice.count("<!-- editorial:begin -->") == 1


# ─── Augment stage with an injected generator ───────────────────────────────
def test_augment_adds_only_gated_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bd = _book(tmp_path, _BASE, toc={"chapters": []})
    monkeypatch.setattr(_book_augment, "_load_kb_atoms", lambda limit=40: [{"text": "atom"}])

    def fake_gen(title, chapter_text, atoms, book_dir, label, log):
        if "Knowledge" in title:
            return ("This note grounds the chapter's teaching in the wider tradition of "
                    "seeking beneficial knowledge as a lifelong obligation for every believer.")
        return "NONE"  # chapter 2 offers nothing

    author_phase_book_augment(bd, log=lambda *a: None, generator=fake_gen)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert out.count("<!-- editorial:begin -->") == 1  # only chapter 1 got a block
    assert "Seek knowledge from cradle to grave." in out  # base intact
    report = json.loads((bd / "_system" / "book-augment-report.json").read_text())
    assert report["accepted"] == 1


def test_augment_drops_doctrinally_bad_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bd = _book(tmp_path, _BASE, toc={"chapters": []})
    monkeypatch.setattr(_book_augment, "_load_kb_atoms", lambda limit=40: [])
    monkeypatch.setattr(
        _book_augment, "gate_editorial_block", lambda t: (False, ["doctrinal P0: T3:test"])
    )
    author_phase_book_augment(
        bd, log=lambda *a: None,
        generator=lambda *a, **k: "some note that will be gated out by the stubbed gate here now",
    )
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "<!-- editorial:begin -->" not in out


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

    def fake_revoicer(title, base_text, book_dir, label, log):
        if "Knowledge" in title:
            return base_text + " I say this to you plainly."  # faithful expansion -> kept
        return "short"  # teaching loss -> reverted

    apply_author_companion_voice(bd, log=lambda *a: None, revoicer=fake_revoicer)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "I say this to you plainly." in out  # chapter 1 kept
    assert "The patient are rewarded without measure." in out  # chapter 2 base preserved
    report = json.loads((bd / "_system" / "book-voice-report.json").read_text())
    assert report["revoiced"] == 1 and report["reverted"] == 1


def test_voice_preserves_editorial_asides(tmp_path: Path) -> None:
    with_aside = _BASE.replace(
        "It benefits the seeker.",
        "It benefits the seeker.\n\n" + format_editorial_block("A grounded aside note for this chapter now."),
    )
    bd = _book(tmp_path, with_aside)
    apply_author_companion_voice(
        bd, log=lambda *a: None,
        revoicer=lambda title, base, *a: base,  # identity -> always kept
    )
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "<!-- editorial:begin -->" in out  # aside survived the re-voice pass


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
        _book_pipeline_v2, "author_translation_edition_compose",
        None, raising=False,
    )
    # patch the lazily-imported names by injecting fakes into the modules they come from
    import _translation_edition
    import _book_augment as aug
    import _book_voice as voice
    monkeypatch.setattr(_translation_edition, "author_translation_edition_compose",
                        lambda bd, **k: calls.append("base") or (Path(bd) / "book" / "book.md"))
    monkeypatch.setattr(aug, "author_phase_book_augment",
                        lambda bd, **k: calls.append("augment") or (Path(bd) / "book" / "book.md"))
    monkeypatch.setattr(voice, "apply_author_companion_voice",
                        lambda bd, **k: calls.append("voice") or (Path(bd) / "book" / "book.md"))
    _book_pipeline_v2.compose_book_v2(bd, log=lambda *a: None)
    assert calls == ["base", "augment", "voice"]


def test_compose_book_v2_faithful_none_runs_base_then_fluency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import _book_pipeline_v2
    import _translation_edition
    import _book_augment as aug
    import _book_voice as voice

    bd = tmp_path / "bd"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "series-config.yaml").write_text(
        "book_pipeline_v2: true\ndeliverable_mode: translation_edition\n", encoding="utf-8",
    )
    calls: list[str] = []
    monkeypatch.setattr(_translation_edition, "author_translation_edition_compose",
                        lambda bd, **k: calls.append("base") or (Path(bd) / "book" / "book.md"))
    monkeypatch.setattr(voice, "apply_fluency_adapt",
                        lambda bd, **k: calls.append("fluency"))
    monkeypatch.setattr(aug, "author_phase_book_augment",
                        lambda bd, **k: calls.append("augment"))
    monkeypatch.setattr(voice, "apply_author_companion_voice",
                        lambda bd, **k: calls.append("voice"))
    _book_pipeline_v2.compose_book_v2(bd, log=lambda *a: None)
    # {none, faithful} -> base + fluency de-calque, no augment/re-voice
    assert calls == ["base", "fluency"]


def test_fluency_reverts_calqued_drift(tmp_path: Path) -> None:
    from _book_voice import apply_fluency_adapt

    bd = _book(tmp_path, _BASE)

    def fake_adapter(title, base_text, book_dir, label, log):
        if "Knowledge" in title:
            return base_text.replace("Seek", "You should seek")  # faithful polish -> kept
        return "x"  # teaching loss -> reverted

    apply_fluency_adapt(bd, log=lambda *a: None, adapter=fake_adapter)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "You should seek knowledge" in out       # chapter 1 kept
    assert "The patient are rewarded without measure." in out  # chapter 2 reverted to base
    report = json.loads((bd / "_system" / "book-fluency-report.json").read_text())
    assert report["adapted"] == 1 and report["reverted"] == 1
