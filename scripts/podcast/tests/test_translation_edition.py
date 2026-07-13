from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _translation_edition import (  # noqa: E402
    contract_findings,
    is_translation_edition,
    monochrome_svg,
    normalize_translation_prose,
    requires_monochrome_visuals,
    source_title_drift_findings,
    translation_output_findings,
    _iter_source_windows,
)
from phases.book_driver import _book_branch_enabled  # noqa: E402


def _book(tmp_path: Path, config: str) -> Path:
    bd = tmp_path / "book"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "series-config.yaml").write_text(config, encoding="utf-8")
    return bd


def test_translation_edition_contract_passes(tmp_path: Path) -> None:
    bd = _book(
        tmp_path,
        """
content_profile: islamic_scholarly
deliverable_mode: translation_edition
visual_style: black_white
translation_policy:
  augmentation: forbidden
  denoise: teaching_only
  preserve_arabic_terms: true
""",
    )

    assert is_translation_edition(bd)
    assert requires_monochrome_visuals(bd)
    assert contract_findings(bd) == []


def test_translation_edition_contract_rejects_augmentation(tmp_path: Path) -> None:
    bd = _book(
        tmp_path,
        """
deliverable_mode: translation_edition
visual_style: black_white
translation_policy:
  augmentation: outside_sources
""",
    )

    findings = contract_findings(bd)
    assert any("augmentation" in finding for finding in findings)


def test_translation_edition_enables_book_branch_without_meta_flag(tmp_path: Path) -> None:
    bd = _book(
        tmp_path,
        """
deliverable_mode: translation_edition
visual_style: black_white
translation_policy:
  augmentation: forbidden
""",
    )

    assert _book_branch_enabled(bd)


def test_monochrome_svg_rewrites_theme_colours() -> None:
    svg = '<svg><rect fill="#8b4513" stroke="#d2b48c"/><text fill="#1f1d18">x</text></svg>'

    mono = monochrome_svg(svg)

    assert "#8b4513" not in mono
    assert "#d2b48c" not in mono
    assert 'fill="#000000"' in mono
    assert 'stroke="#d9d9d9"' in mono


def test_source_windows_preserve_line_ranges() -> None:
    lines = []
    for page in range(1, 5):
        lines.append(f"<!-- page {page} -->")
        lines.append(("word " * 20).strip())
        lines.append("")

    windows = _iter_source_windows(lines, [[1, len(lines)]], target_words=35)

    assert len(windows) >= 2
    assert windows[0][1][0][0] == 1
    assert windows[-1][1][-1][-1] == len(lines)


def test_translation_output_findings_rejects_model_commentary() -> None:
    prose = (
        "Since you didn't pick an option, I cannot produce \"Dress\" prose "
        "from a source passage about hunting. Here is the faithful chapter."
    )

    findings = translation_output_findings(prose, expected_title="Dress")

    assert findings
    assert any("option" in f or "refuses" in f for f in findings)


def test_translation_output_findings_rejects_model_owned_headings() -> None:
    prose = "# What We Hunt and What We Slaughter\n\nThe source teaches..."

    findings = translation_output_findings(prose, expected_title="What We Wear")

    assert any("opening heading" in f for f in findings)


def test_normalize_translation_prose_compacts_long_salutations() -> None:
    prose = (
        "The Messenger of Allah, may Allah's peace and blessings be upon him and his family, said this. "
        "The Imams, may Allah's prayers be upon them all, preserved it. "
        "Ali, may Allah be pleased with him, narrated it."
    )

    normalized = normalize_translation_prose(prose)

    assert "(ع)" in normalized
    assert "(عليهم السلام)" in normalized
    assert "(رض)" in normalized
    assert "peace and blessings" not in normalized.lower()


def test_source_title_drift_detects_dress_title_on_hunting_source() -> None:
    findings = source_title_drift_findings(
        "What We Wear: Dress, Adornment, and Fragrance",
        "A discussion of hunting, game, slaughter, sacrifice, prey, and the knife.",
    )

    assert findings
