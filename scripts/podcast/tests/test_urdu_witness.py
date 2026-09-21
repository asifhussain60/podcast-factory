"""Pure-logic tests for the Urdu second-witness audit (no network, no model)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _urdu_witness as uw  # noqa: E402


def test_parse_ranges_expands_and_dedupes():
    assert uw.parse_ranges("1-3,3,7") == [1, 2, 3, 7]


def test_parse_ranges_rejects_backwards():
    import pytest

    with pytest.raises(ValueError):
        uw.parse_ranges("5-2")


def test_page_stats_mean_confidence_and_low_flag():
    page = {
        "pageNumber": 4,
        "lines": [{"content": "الف"}, {"content": "ب"}],
        "words": [{"confidence": 0.9}, {"confidence": 0.5}],
    }
    s = uw.page_stats(page, low_conf=0.8)
    assert s["n_words"] == 2 and s["conf"] == 0.7 and s["low"] is True
    assert s["text"] == "الف\nب"


def test_page_stats_empty_page_is_low():
    s = uw.page_stats({"pageNumber": 1, "lines": [], "words": []}, low_conf=0.8)
    assert s["conf"] == 0.0 and s["low"] is True


def test_ocr_confidence_is_capped_into_flag_certainty():
    # Flag certainty may never exceed what the Urdu OCR itself supports.
    assert uw.cap_certainty(95, ocr_conf=0.60) == 60
    assert uw.cap_certainty(40, ocr_conf=0.99) == 40


def test_rank_orders_by_severity_then_certainty():
    flags = [{"sev": "P1", "certainty": 90}, {"sev": "P0", "certainty": 30}, {"sev": "P0", "certainty": 80}]
    out = uw.rank_flags(flags)
    assert [(f["sev"], f["certainty"]) for f in out] == [("P0", 80), ("P0", 30), ("P1", 90)]
