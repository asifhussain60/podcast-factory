#!/usr/bin/env python3
"""A throttled vowelling call is a delay, not a verdict on the Arabic.

The vowelling pass fans out to eight concurrent Gemini calls over runs of Arabic
the reader cannot read without marks. When the API throttled one, the HTTPError
travelled straight out of the transport, the pool's `except Exception` turned it
into a refusal reading `model error: HTTP Error 429`, and the salvage pass —
which re-asks a refused run fragment by fragment — skipped it, because salvage
only ever looked at runs the VOWELLING GATE had turned away. So a throttled book
shipped bare Arabic and its report blamed the passage.

Three properties, and each one failed on its own before this file existed:

  A 429 IS RETRIED. Nothing about the request is wrong, so re-sending it is the
  whole fix. 4xx that are not 429 stay fatal, because a 400 will not change.

  A MODEL ERROR IS NOT A GATE REFUSAL. They mean opposite things — one says the
  call did not happen, the other says the answer was wrong — and only the second
  is a statement about the text. Both now reach the salvage pass; only the second
  is the salvage pass's own verdict when it fails again.

  WHAT WAS ASKED IS WHAT IS BILLED. The headroom retry — a second, larger call
  made when 2.5 Pro's thinking ate the first answer — was invisible in the
  ledger, so a book's recorded Gemini spend was systematically short by every run
  long enough to need it.
"""

from __future__ import annotations

import io
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

import vowel_book  # noqa: E402

# A short non-Qur'anic Arabic run, bare, and its marked answer. The skeleton is
# identical between the two, so the vowelling gate accepts it.
RUN = "قال العالم"
MARKED = "قَالَ الْعَالِمُ"


def _reply(text: str) -> bytes:
    import json

    return json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode()


class _FakeResponse(io.BytesIO):
    status = 200
    headers: dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def _urlopen_returning(script: list[object]):
    """A fake urlopen that plays `script` one entry per call.

    An entry is either an exception to raise or the bytes of a 200 reply. The
    calls are recorded so a test can say how many attempts were made.
    """
    attempts: list[bytes] = []

    def fake(req, timeout=None):  # noqa: ARG001
        attempts.append(req.data)
        item = script[min(len(attempts) - 1, len(script) - 1)]
        if isinstance(item, Exception):
            raise item
        return _FakeResponse(item)

    fake.attempts = attempts  # type: ignore[attr-defined]
    return fake


@pytest.fixture(autouse=True)
def _no_key_no_sleep(monkeypatch):
    import _secrets

    monkeypatch.setattr(_secrets, "get_gemini_key", lambda: "test-key")
    monkeypatch.setattr("time.sleep", lambda _s: None)


def _throttle(code: int = 429) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://example", code, "Too Many Requests", {}, io.BytesIO(b"{}"))


def test_a_throttled_call_is_retried_rather_than_raised(monkeypatch) -> None:
    fake = _urlopen_returning([_throttle(), _reply(MARKED)])
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    assert vowel_book._gemini(vowel_book.SYSTEM, RUN) == MARKED
    assert len(fake.attempts) == 2  # type: ignore[attr-defined]


def test_a_bad_request_is_not_retried(monkeypatch) -> None:
    # A 400 says the request is wrong; sending it again five times only wastes
    # the run's time budget on a reply that cannot change.
    fake = _urlopen_returning([_throttle(400)])
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    with pytest.raises(Exception):
        vowel_book._gemini(vowel_book.SYSTEM, RUN)
    assert len(fake.attempts) == 1  # type: ignore[attr-defined]


def test_both_headroom_calls_are_billed(monkeypatch) -> None:
    # The first answer comes back empty — 2.5 Pro drew its whole allowance for
    # thinking — so a second, larger call is made. Both were paid for.
    fake = _urlopen_returning([_reply(""), _reply(MARKED)])
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    before = vowel_book.meter_reading()
    assert vowel_book._ask_with_headroom(vowel_book.SYSTEM, RUN) == MARKED
    after = vowel_book.meter_reading()
    assert after["in_chars"] - before["in_chars"] == 2 * len(RUN)


def test_a_throttled_run_is_vowelled_and_never_recorded_as_refused(monkeypatch) -> None:
    fake = _urlopen_returning([_throttle(), _reply(MARKED)])
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    out, stats = vowel_book.vowel_runs(f"He said: {RUN} today.", log=lambda _m: None)
    assert MARKED in out
    assert stats["refused"] == 0
    assert stats["refusals"] == []
    assert stats["in_chars"] == len(RUN)  # one billed reply; the 429 was not billed


def test_the_glossary_pass_puts_its_spend_on_the_ledger(tmp_path: Path, monkeypatch) -> None:
    """The glossary is one metered call per bare term and recorded none of them.

    Sixty-odd calls a book, absent from cost-ledger.jsonl entirely — so the cost
    policy read a book's Gemini spend short by the whole pass, and the provenance
    audit could not say which model had set the marks a reader sees.
    """
    from vowel_glossary import vowel_glossary

    (tmp_path / "_system").mkdir()
    (tmp_path / "_system" / "glossary.yml").write_text(
        f'- term: scholar\n  transliteration: "qala al-alim"\n  arabic_script: "{RUN}"\n',
        encoding="utf-8",
    )
    fake = _urlopen_returning([_reply(MARKED)])
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    stats = vowel_glossary(tmp_path, log=lambda _m: None)
    assert stats["vowelled"] == 1
    ledger = (tmp_path / "_system" / "cost-ledger.jsonl").read_text(encoding="utf-8")
    assert "5a-glossary-vowel" in ledger
    assert "gemini" in ledger


def test_a_model_error_reaches_the_salvage_pass(monkeypatch) -> None:
    """The whole point: a call that never happened is not a verdict on the text.

    The first ask raises; the salvage pass then re-asks the run's fragments and
    gets the marks. Before this, the raise was written straight into `refusals`
    and salvage — which reads only the gate's own refusals — never saw it.
    """
    seen: list[str] = []

    def flaky(run: str) -> str:
        seen.append(run)
        if len(seen) == 1:
            raise RuntimeError("HTTP 503")
        return MARKED if run.strip() == RUN else run

    out, stats = vowel_book.vowel_runs(f"He said: {RUN} today.", log=lambda _m: None, call=flaky)
    assert len(seen) > 1, "the salvage pass never re-asked the run"
    assert stats["refused"] == 0
    assert MARKED in out
