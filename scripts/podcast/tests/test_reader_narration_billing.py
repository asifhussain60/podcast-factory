#!/usr/bin/env python3
"""Narration bills what it bought, and retries only what a retry can fix.

Two defects, both invisible while a run succeeds:

  A CHAPTER THAT FAILS LATE BILLED NOTHING. The Azure Speech cost row was
  appended only after the whole chapter concatenated, so a chapter that bought
  twenty-nine paragraphs and then failed on the thirtieth recorded no spend at
  all -- while the twenty-nine clips stayed in the block cache and were reused,
  free, by the next run. Real money left the account and the book's ledger, which
  the cost ceiling reads, never saw it.

  EVERY HTTP ERROR WAS RETRIED. A 401 -- a wrong or expired Speech key -- was
  sent three times with 2s and 4s of sleep between, per paragraph, across every
  chapter of the book, and the answer was never going to change.
"""

from __future__ import annotations

import io
import sys
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import reader_narration as rn  # noqa: E402
from test_reader_narration import make_book  # noqa: E402


class _Creds:
    region = "eastus"
    key = "test-key"


@pytest.fixture(autouse=True)
def _creds_and_no_sleep(monkeypatch):
    monkeypatch.setattr(rn._azure, "load_speech_creds", lambda: _Creds())
    monkeypatch.setattr(rn, "engine_guard", lambda *_a, **_k: None)
    monkeypatch.setattr(rn.time, "sleep", lambda _s: None)


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://example", code, "nope", {}, io.BytesIO(b""))


def _urlopen_playing(script: list[object]):
    calls: list[int] = []

    def fake(_req, timeout=None):  # noqa: ARG001
        calls.append(1)
        item = script[min(len(calls) - 1, len(script) - 1)]
        if isinstance(item, Exception):
            raise item
        return _Response(item)

    fake.calls = calls  # type: ignore[attr-defined]
    return fake


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def test_an_unauthorised_key_is_not_retried(monkeypatch) -> None:
    # Nothing about a 401 changes on the second try; retrying it three times per
    # paragraph turns one wrong credential into a slow failure of the whole book.
    fake = _urlopen_playing([_http_error(401)])
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    with pytest.raises(urllib.error.HTTPError):
        rn.synthesize_text("A sentence.", rn.VOICE_PRESETS["jenny"])
    assert len(fake.calls) == 1  # type: ignore[attr-defined]


def test_a_throttled_or_failing_service_is_retried(monkeypatch) -> None:
    fake = _urlopen_playing([_http_error(429), _http_error(503), b"MP3"])
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    assert rn.synthesize_text("A sentence.", rn.VOICE_PRESETS["jenny"]) == b"MP3"
    assert len(fake.calls) == 3  # type: ignore[attr-defined]


def test_a_chapter_that_fails_late_still_bills_what_it_bought(tmp_path: Path) -> None:
    """Two paragraphs bought, then the concatenation fails.

    The clips stay in the block cache -- that is the point of the cache -- so the
    next run reuses them for free. If this run bills nothing, those characters
    are never billed by anybody.
    """
    book = make_book(tmp_path)
    durations = iter([1.2, 0.4, 0.8, 2.4, 2.4])

    def boom(_parts, _out_path):
        raise RuntimeError("ffmpeg died")

    with (
        mock.patch.object(rn, "synthesize_text", side_effect=lambda t, p: b"AUDIO"),
        mock.patch.object(rn, "audio_duration_seconds", side_effect=lambda _p: next(durations)),
        mock.patch.object(rn, "concat_audio", side_effect=boom),
        mock.patch.object(rn, "append_azure_speech_cost") as cost,
    ):
        result = rn.render_reader_narration(book)

    assert result.failed == ["opening"]
    cost.assert_called_once()
    assert cost.call_args.kwargs["char_count"] > 0


def test_a_chapter_that_buys_nothing_bills_nothing(tmp_path: Path) -> None:
    # The second run reuses every clip from the block cache, so there is no spend
    # to report and a zero row would be noise in the ledger.
    book = make_book(tmp_path)
    durations = iter([1.2, 0.4, 0.8] + [2.4] * 20)

    with (
        mock.patch.object(rn, "synthesize_text", side_effect=lambda t, p: b"AUDIO"),
        mock.patch.object(rn, "audio_duration_seconds", side_effect=lambda _p: next(durations)),
        mock.patch.object(rn, "concat_audio", side_effect=lambda parts, out: out.write_bytes(b"MP3")),
        mock.patch.object(rn, "append_azure_speech_cost") as cost,
    ):
        rn.render_reader_narration(book)
        cost.reset_mock()
        (book / "book" / "narration" / "manifest.json").unlink()
        rn.render_reader_narration(book)

    cost.assert_not_called()
