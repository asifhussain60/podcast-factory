from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _pipeline_flags import (  # noqa: E402
    BOOK_AUGMENTATION_NONE,
    BOOK_AUGMENTATION_SOURCE_ONLY,
    BOOK_VOICE_AUTHOR_COMPANION,
    BOOK_VOICE_FAITHFUL,
    FEATURE_FLAG_ENV,
    book_augmentation,
    book_knobs,
    book_pipeline_v2_enabled,
    book_voice,
)


def _book(tmp_path: Path, config: str) -> Path:
    bd = tmp_path / "book"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "series-config.yaml").write_text(config, encoding="utf-8")
    return bd


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(FEATURE_FLAG_ENV, raising=False)


# ─── Flag default is OFF ────────────────────────────────────────────────────
def test_flag_defaults_off_when_absent(tmp_path: Path) -> None:
    bd = _book(tmp_path, "deliverable_mode: translation_edition\n")
    assert book_pipeline_v2_enabled(bd) is False


def test_flag_defaults_off_when_no_config(tmp_path: Path) -> None:
    bd = tmp_path / "no_config"
    bd.mkdir()
    assert book_pipeline_v2_enabled(bd) is False


def test_flag_reads_true_from_config(tmp_path: Path) -> None:
    bd = _book(tmp_path, "book_pipeline_v2: true\n")
    assert book_pipeline_v2_enabled(bd) is True


def test_flag_env_override_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bd = _book(tmp_path, "book_pipeline_v2: false\n")
    monkeypatch.setenv(FEATURE_FLAG_ENV, "1")
    assert book_pipeline_v2_enabled(bd) is True
    monkeypatch.setenv(FEATURE_FLAG_ENV, "off")
    assert book_pipeline_v2_enabled(bd) is False


# ─── Zero-regression default knob map ───────────────────────────────────────
def test_translation_edition_defaults_to_none_faithful(tmp_path: Path) -> None:
    bd = _book(tmp_path, "deliverable_mode: translation_edition\n")
    assert book_augmentation(bd) == BOOK_AUGMENTATION_NONE
    assert book_voice(bd) == BOOK_VOICE_FAITHFUL


def test_legacy_companion_defaults_to_source_only_author_companion(tmp_path: Path) -> None:
    bd = _book(tmp_path, "series:\n  enable_book_branch: true\n")
    assert book_augmentation(bd) == BOOK_AUGMENTATION_SOURCE_ONLY
    assert book_voice(bd) == BOOK_VOICE_AUTHOR_COMPANION


def test_empty_config_defaults_to_companion(tmp_path: Path) -> None:
    bd = _book(tmp_path, "\n")
    assert book_augmentation(bd) == BOOK_AUGMENTATION_SOURCE_ONLY
    assert book_voice(bd) == BOOK_VOICE_AUTHOR_COMPANION


# ─── Explicit knobs override the default map ────────────────────────────────
def test_explicit_knobs_override_translation_default(tmp_path: Path) -> None:
    bd = _book(
        tmp_path,
        "deliverable_mode: translation_edition\n"
        "book_augmentation: source_only\n"
        "book_voice: author_companion\n",
    )
    assert book_augmentation(bd) == BOOK_AUGMENTATION_SOURCE_ONLY
    assert book_voice(bd) == BOOK_VOICE_AUTHOR_COMPANION


def test_invalid_knob_falls_back_to_default(tmp_path: Path) -> None:
    bd = _book(
        tmp_path,
        "deliverable_mode: translation_edition\n"
        "book_augmentation: bogus\n"
        "book_voice: nonsense\n",
    )
    # A typo can never harden into a silent behaviour change — fall back to map.
    assert book_augmentation(bd) == BOOK_AUGMENTATION_NONE
    assert book_voice(bd) == BOOK_VOICE_FAITHFUL


def test_book_knobs_bundle(tmp_path: Path) -> None:
    bd = _book(tmp_path, "book_pipeline_v2: true\ndeliverable_mode: translation_edition\n")
    knobs = book_knobs(bd)
    assert knobs == {
        "book_pipeline_v2": True,
        "augmentation": BOOK_AUGMENTATION_NONE,
        "voice": BOOK_VOICE_FAITHFUL,
    }
