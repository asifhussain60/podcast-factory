"""The annotation policy: classified once, by a model, reviewable forever.

The judgment (which terms help a reader) is a model's, made once per book and
written into glossary.yml where a human can override any line. The application
is deterministic and lives in _book_inline_arabic. These tests cover the
judgment's plumbing: strict parsing, refusal of partial output, durability of a
human's override, and the model never touching curated script.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _annotation_policy import (  # noqa: E402
    AnnotationPolicyError,
    load_policy,
    propose_annotation_policy,
)


def _book(tmp_path: Path, entries: list[dict]) -> Path:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text("## 1. A\n\nThe natiq met Joseph.\n", encoding="utf-8")
    (bd / "_system" / "glossary.yml").write_text(
        yaml.safe_dump({"schema_version": 1, "entries": entries}, allow_unicode=True),
        encoding="utf-8",
    )
    return bd


_ENTRIES = [
    {"phonetic": "natiq", "arabic_script": "الناطق"},
    {"phonetic": "Joseph", "arabic_script": "يوسف"},
]


def _classifier(payload: list[dict]) -> str:
    return json.dumps(payload)


def test_proposals_land_in_the_glossary_and_the_report(tmp_path: Path) -> None:
    bd = _book(tmp_path, _ENTRIES)
    report = propose_annotation_policy(
        bd,
        log=lambda *a: None,
        classifier=lambda _p: _classifier(
            [
                {"phonetic": "natiq", "class": "teach", "english_equivalent": "", "reason": "core vocabulary"},
                {"phonetic": "Joseph", "class": "familiar", "english_equivalent": "Joseph", "reason": "famous prophet"},
            ]
        ),
    )
    assert report["by_class"]["teach"] == 1 and report["by_class"]["familiar"] == 1
    policy = load_policy(bd)
    assert policy["natiq"]["class"] == "teach"
    assert policy["Joseph"] == {"class": "familiar", "english_equivalent": "Joseph"}
    assert (bd / "_system" / "annotation-policy-report.json").exists()


def test_a_human_override_survives_a_re_proposal(tmp_path: Path) -> None:
    # The learning-loop rule: a human decision is durable. Re-running the
    # proposal must not touch an entry that already carries a class.
    bd = _book(tmp_path, [{**_ENTRIES[0], "annotation_class": "silent"}, _ENTRIES[1]])
    propose_annotation_policy(
        bd,
        log=lambda *a: None,
        classifier=lambda _p: _classifier(
            [{"phonetic": "Joseph", "class": "familiar", "english_equivalent": "Joseph", "reason": "famous"}]
        ),
    )
    assert load_policy(bd)["natiq"]["class"] == "silent"  # untouched


def test_a_partial_classification_is_refused(tmp_path: Path) -> None:
    # Half a classification would print two conventions in one book: classified
    # terms once-per-book, forgotten terms once-per-chapter.
    bd = _book(tmp_path, _ENTRIES)
    with pytest.raises(AnnotationPolicyError, match="omitted"):
        propose_annotation_policy(
            bd,
            log=lambda *a: None,
            classifier=lambda _p: _classifier([{"phonetic": "natiq", "class": "teach", "reason": "x"}]),
        )


def test_an_unknown_class_from_the_model_is_refused(tmp_path: Path) -> None:
    bd = _book(tmp_path, _ENTRIES[:1])
    with pytest.raises(AnnotationPolicyError, match="unknown class"):
        propose_annotation_policy(
            bd,
            log=lambda *a: None,
            classifier=lambda _p: _classifier([{"phonetic": "natiq", "class": "shiny", "reason": "x"}]),
        )


def test_arabic_in_english_equivalent_is_refused(tmp_path: Path) -> None:
    # Script stays curated; the classifier can never smuggle any in.
    bd = _book(tmp_path, _ENTRIES[:1])
    with pytest.raises(AnnotationPolicyError, match="Arabic"):
        propose_annotation_policy(
            bd,
            log=lambda *a: None,
            classifier=lambda _p: _classifier(
                [{"phonetic": "natiq", "class": "familiar", "english_equivalent": "الناطق", "reason": "x"}]
            ),
        )


def test_the_model_cannot_touch_arabic_script(tmp_path: Path) -> None:
    bd = _book(tmp_path, _ENTRIES)
    propose_annotation_policy(
        bd,
        log=lambda *a: None,
        classifier=lambda _p: _classifier(
            [
                {"phonetic": "natiq", "class": "teach", "reason": "x"},
                {"phonetic": "Joseph", "class": "familiar", "english_equivalent": "Joseph", "reason": "y"},
            ]
        ),
    )
    data = yaml.safe_load((bd / "_system" / "glossary.yml").read_text(encoding="utf-8"))
    scripts = {e["phonetic"]: e["arabic_script"] for e in data["entries"]}
    assert scripts == {"natiq": "الناطق", "Joseph": "يوسف"}
