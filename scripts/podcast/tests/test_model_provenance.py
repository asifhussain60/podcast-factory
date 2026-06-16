"""Tests for model-provenance recording (WS2).

Locks the contract that every authoring call records which model produced it, and
that a non-default model (the Sonnet timeout-fallback) is flagged as a divergence
so mixed-model books are visible rather than silent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _authoring._core import record_model_provenance, DEFAULT_MODEL_LABEL  # noqa: E402


def _rows(book_dir: Path):
    p = book_dir / "_system" / "model-provenance.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def test_default_model_is_not_a_divergence(tmp_path):
    record_model_provenance(tmp_path, phase="0d", step="design",
                            model=DEFAULT_MODEL_LABEL)
    rows = _rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["model"] == DEFAULT_MODEL_LABEL
    assert rows[0]["divergence"] is False


def test_fallback_model_is_flagged_divergence(tmp_path):
    record_model_provenance(tmp_path, phase="0d", step="design-retry-sonnet",
                            model="claude-sonnet-4-6", fallback=True)
    rows = _rows(tmp_path)
    assert rows[0]["divergence"] is True
    assert rows[0]["fallback"] is True
    assert rows[0]["model"] == "claude-sonnet-4-6"


def test_non_default_model_is_divergence_even_without_fallback_flag(tmp_path):
    record_model_provenance(tmp_path, phase="x", step="y", model="claude-haiku-4-5")
    assert _rows(tmp_path)[0]["divergence"] is True


def test_appends_multiple_rows(tmp_path):
    record_model_provenance(tmp_path, phase="0d", step="a", model=DEFAULT_MODEL_LABEL)
    record_model_provenance(tmp_path, phase="0e", step="b", model="claude-sonnet-4-6",
                            fallback=True)
    rows = _rows(tmp_path)
    assert len(rows) == 2
    assert sum(1 for r in rows if r["divergence"]) == 1


def test_none_book_dir_is_noop(tmp_path):
    record_model_provenance(None, phase="x", step="y", model=DEFAULT_MODEL_LABEL)  # no raise
