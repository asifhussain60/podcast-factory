"""Acceptance matrix for Book Pipeline v2 (Phase 7).

The single suite that pins the whole v2 contract: the knob matrix stage sequence,
the visual-layout contract, watermark absence + caption de-dup, and — the load-
bearing one — the flag-OFF legacy invariant. If any of these break, the cutover is
not safe.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))


def _book(tmp_path: Path, config: str) -> Path:
    bd = tmp_path / "bd"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "series-config.yaml").write_text(config, encoding="utf-8")
    return bd


def _trace_stages(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Patch every v2 stage to record its name in call order."""
    import _translation_edition
    import _book_augment
    import _book_voice
    calls: list[str] = []
    monkeypatch.setattr(_translation_edition, "author_translation_edition_compose",
                        lambda bd, **k: calls.append("base") or (Path(bd) / "book" / "book.md"))
    monkeypatch.setattr(_book_voice, "apply_fluency_adapt", lambda bd, **k: calls.append("fluency"))
    monkeypatch.setattr(_book_augment, "author_phase_book_augment", lambda bd, **k: calls.append("augment"))
    monkeypatch.setattr(_book_voice, "apply_author_companion_voice", lambda bd, **k: calls.append("voice"))
    return calls


# ── The knob matrix — the four cells of {augmentation} x {voice} ─────────────
@pytest.mark.parametrize(
    "augmentation,voice,expected",
    [
        ("none",        "faithful",         ["base", "fluency"]),
        ("source_only", "faithful",         ["base", "fluency", "augment"]),
        ("none",        "author_companion", ["base", "voice"]),
        ("source_only", "author_companion", ["base", "augment", "voice"]),
    ],
)
def test_knob_matrix_stage_sequence(tmp_path, monkeypatch, augmentation, voice, expected) -> None:
    import _book_pipeline_v2
    bd = _book(
        tmp_path,
        f"book_pipeline_v2: true\nbook_augmentation: {augmentation}\nbook_voice: {voice}\n",
    )
    calls = _trace_stages(monkeypatch)
    _book_pipeline_v2.compose_book_v2(bd, log=lambda *a: None)
    assert calls == expected


def test_config_default_map_reproduces_current_routing(tmp_path, monkeypatch) -> None:
    """deliverable_mode: translation_edition -> {none, faithful}; legacy -> {source_only, author_companion}."""
    import _book_pipeline_v2
    # translation edition default -> base + fluency (faithful, no augment)
    bd1 = _book(tmp_path / "a", "book_pipeline_v2: true\ndeliverable_mode: translation_edition\n")
    calls1 = _trace_stages(monkeypatch)
    _book_pipeline_v2.compose_book_v2(bd1, log=lambda *a: None)
    assert calls1 == ["base", "fluency"]


def test_legacy_companion_default_full_pipeline(tmp_path, monkeypatch) -> None:
    import _book_pipeline_v2
    bd = _book(tmp_path, "book_pipeline_v2: true\nseries:\n  enable_book_branch: true\n")
    calls = _trace_stages(monkeypatch)
    _book_pipeline_v2.compose_book_v2(bd, log=lambda *a: None)
    assert calls == ["base", "augment", "voice"]  # {source_only, author_companion}


# ── The flag-OFF legacy invariant (load-bearing) ─────────────────────────────
def test_flag_off_never_reaches_v2(tmp_path) -> None:
    from _pipeline_flags import book_pipeline_v2_enabled
    for cfg in (
        "deliverable_mode: translation_edition\n",
        "series:\n  enable_book_branch: true\n",
        "\n",
    ):
        assert book_pipeline_v2_enabled(_book(tmp_path / cfg[:4], cfg)) is False


def test_flag_off_de_calque_is_pure_suffix() -> None:
    from _authoring._refine import build_phase_0b_window_prompt
    off = build_phase_0b_window_prompt("s", 1, 2, Path("i"), Path("o"), de_calque=False)
    on = build_phase_0b_window_prompt("s", 1, 2, Path("i"), Path("o"), de_calque=True)
    assert on.startswith(off) and "de-calque" not in off.lower()


# ── Contract + render invariants (one place to see them all) ─────────────────
def test_contract_wrap_cap_and_center_rule() -> None:
    from _visual_layout import normalize_placement
    # center can't float
    assert normalize_placement({"visual_id": "a", "align": "center", "flow": "wrap"})[0]["flow"] == "standalone"
    # wrap wider than the cap becomes standalone
    assert normalize_placement({"visual_id": "a", "flow": "wrap", "align": "left", "width_pct": 70})[0]["flow"] == "standalone"


def test_render_watermark_and_caption_gates() -> None:
    from _book_render_checks import scan_watermark, scan_duplicate_captions
    assert scan_watermark(["made with NotebookLM"])[0]["severity"] == "P0"
    dup = "Cap Line\nCap Line"
    assert scan_duplicate_captions([dup])[0]["check"] == "BR-CAPTION-DUP"
