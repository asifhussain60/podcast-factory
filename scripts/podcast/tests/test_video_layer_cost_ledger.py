"""Every Imagen image the video layer saves is one row in the cost ledger.

The two image generators recorded their spend through `append_gemini_cost` with
`input_tokens=`/`output_tokens=`/`cost_usd=` keywords that function does not
accept (it prices from `in_chars`/`out_chars` itself). The resulting TypeError was
caught by a bare `except Exception: pass`, so real image spend was never ledgered
and no one was told. These run offline: the Gemini client is replaced by one that
hands back a single inline image, and no key is read.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import generate_video_layer as gv  # noqa: E402


class _FakeClient:
    """`genai.Client` stand-in: any generate_content call yields one inline JPEG."""

    def __init__(self, **_kwargs):
        part = SimpleNamespace(inline_data=SimpleNamespace(data=b"\xff\xd8jpeg"))
        resp = SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))])
        self.models = SimpleNamespace(generate_content=lambda **_kw: resp)


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr("google.genai.Client", _FakeClient)
    monkeypatch.setattr("_secrets.get_gemini_key", lambda: "not-a-key")
    if hasattr(gv, "get_gemini_key"):
        monkeypatch.setattr(gv, "get_gemini_key", lambda: "not-a-key")
    book = tmp_path / "book"
    (book / "_system").mkdir(parents=True)
    return book


def _rows(book: Path) -> list[dict]:
    ledger = book / "_system" / "cost-ledger.jsonl"
    if not ledger.exists():
        return []
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_a_saved_scenic_image_is_one_ledger_row_at_the_image_estimate(offline: Path, tmp_path: Path) -> None:
    segments = [{"segment_id": "s01", "visual_type": "scenery", "prompt_full": "a lamp in a window"}]

    saved = gv._generate_images(segments, tmp_path / "img", offline, "EP01-white-nights")

    assert saved == 1
    rows = _rows(offline)
    assert len(rows) == 1, "one image saved, one dollar row"
    assert rows[0]["cost_usd"] == gv.IMAGE_COST_ESTIMATE
    assert rows[0]["phase"] == "video" and rows[0]["model"] == gv.IMAGE_MODEL


def test_a_saved_background_image_is_one_ledger_row_at_the_image_estimate(offline: Path, tmp_path: Path) -> None:
    manifest = {"backgrounds": [{"bg_id": "bg01", "theme": "dawn", "prompt": "a courtyard at dawn"}]}

    saved = gv._generate_background_images(manifest, tmp_path / "img", offline, "EP01-x")

    assert saved == 1
    rows = _rows(offline)
    assert len(rows) == 1 and rows[0]["cost_usd"] == gv.IMAGE_COST_ESTIMATE
    assert rows[0]["step"] == "bg/EP01-x/bg01"


def test_a_ledger_failure_is_warned_about_not_swallowed(offline: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    """The bug survived because the append's own TypeError vanished into `pass`."""

    def broken(*_a, **_k):
        raise TypeError("unexpected keyword argument")

    monkeypatch.setattr(gv, "append_precomputed_cost", broken)
    segments = [{"segment_id": "s01", "visual_type": "scenery", "prompt_full": "x"}]

    saved = gv._generate_images(segments, tmp_path / "img", offline, "EP01-x")

    assert saved == 1, "a ledger problem must not cost the image"
    assert "cost-ledger append failed" in capsys.readouterr().err
