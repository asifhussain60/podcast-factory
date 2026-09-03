#!/usr/bin/env python3
"""Running the proofreader's windows at once must change speed and nothing else.

The windows were made concurrent on 2026-09-03 because one 10,700-word lecture
chapter took 52 minutes to proofread — ~15 windows twice over, plus a resolution
per Arabic run, each a `claude -p` call of roughly 110 seconds spent almost
entirely waiting. Eleven chapters came to ten hours of wall clock.

Concurrency is safe here only because every call is independent, and these cases
pin the three things that would silently stop being true if that changed:

  ORDER      a chapter is REASSEMBLED from its windows. Completion order reaching
             the page would shuffle the lecture into nonsense.
  THE GATES  a window whose correction drifts is reverted to the transcription.
             The gate must stay per-window, not per-batch.
  FAILURE    one window that blows up must cost that window, never the chapter.

No model is called: `_run_claude_p_with_retry` is replaced, so these run offline
and in milliseconds.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _verbatim_correct as vc  # noqa: E402


def _chapter(window_count: int, words_per_window: int = 800) -> str:
    """Text long enough to split into exactly `window_count` windows."""
    return "\n\n".join(" ".join([f"w{i}"] * words_per_window) for i in range(window_count))


class _FakeCall:
    """Stands in for `_run_claude_p_with_retry`, recording what it was asked."""

    def __init__(self, reply=lambda prompt: None, delay: float = 0.0):
        self.reply = reply
        self.delay = delay
        self.steps: list[str] = []

    def __call__(self, prompt, **kwargs):
        if self.delay:
            time.sleep(self.delay)
        self.steps.append(kwargs.get("step", ""))
        out = self.reply(prompt)
        return (0, out, "") if out is not None else (1, "", "boom")


def _echo(prompt: str) -> str:
    """A perfect corrector: returns the window unchanged, so every gate passes."""
    return prompt.split("TRANSCRIPTION:\n", 1)[-1].strip()


def _run(monkeypatch, text, reply=_echo, workers=8, delay=0.0):
    fake = _FakeCall(reply, delay)
    monkeypatch.setattr(vc, "_run_claude_p_with_retry", fake)
    monkeypatch.setattr(vc, "_WINDOW_WORKERS", workers)
    out, warnings = vc.correct(Path("/tmp"), text, phase="p", label="ch", log=lambda *_: None)
    return out, warnings, fake


# ── order ────────────────────────────────────────────────────────────────────


def test_windows_are_reassembled_in_order_not_completion_order(monkeypatch):
    """The defining risk of concurrency here: a shuffled lecture."""
    text = _chapter(6)

    # Reply late for early windows and fast for late ones, so completion order is
    # the REVERSE of window order. Sequential code cannot tell the difference;
    # unordered assembly would fail loudly.
    def slow_first(prompt: str) -> str:
        body = _echo(prompt)
        time.sleep(0.05 if body.startswith("w0") else 0.0)
        return body

    out, warnings, _ = _run(monkeypatch, text, reply=slow_first)
    assert out == text, "windows came back out of order"
    assert warnings == []


def test_parallel_output_is_identical_to_sequential(monkeypatch):
    text = _chapter(5)
    parallel, _, _ = _run(monkeypatch, text, workers=8)
    sequential, _, _ = _run(monkeypatch, text, workers=1)
    assert parallel == sequential


def test_every_window_is_asked_for_exactly_once(monkeypatch):
    _out, _warn, fake = _run(monkeypatch, _chapter(4))
    assert sorted(fake.steps) == ["ch-window-01", "ch-window-02", "ch-window-03", "ch-window-04"]


# ── the gates still bite, per window ─────────────────────────────────────────


def test_a_rewritten_window_is_reverted_and_the_others_are_not(monkeypatch):
    """The gate is per-window: one bad window must not revert the chapter."""
    text = _chapter(3)

    def rewrite_second(prompt: str) -> str:
        body = _echo(prompt)
        return "totally different prose about something else entirely" if body.startswith("w1") else body

    out, warnings, _ = _run(monkeypatch, text, reply=rewrite_second)
    windows = out.split("\n\n")
    assert windows[0].startswith("w0") and windows[2].startswith("w2")
    assert windows[1].startswith("w1"), "the drifting window kept its transcription"
    assert len(warnings) == 1 and "reverted" in warnings[0]


def test_an_empty_reply_keeps_the_transcription(monkeypatch):
    out, warnings, _ = _run(monkeypatch, _chapter(2), reply=lambda _p: None)
    assert out == _chapter(2)
    assert len(warnings) == 2 and all("no usable reply" in w for w in warnings)


# ── one bad window never costs the chapter ───────────────────────────────────


def test_an_exception_in_one_window_keeps_that_window_and_the_rest(monkeypatch):
    text = _chapter(3)

    def explode_on_second(prompt: str):
        if _echo(prompt).startswith("w1"):
            raise RuntimeError("network gone")
        return _echo(prompt)

    out, warnings, _ = _run(monkeypatch, text, reply=explode_on_second)
    assert out == text, "the failed window must fall back to its own transcription"
    assert len(warnings) == 1 and "RuntimeError" in warnings[0]


# ── it is actually concurrent ────────────────────────────────────────────────


def test_the_windows_really_do_overlap(monkeypatch):
    """Six windows that each sleep 100ms finish in well under six sequential slots."""
    started = time.monotonic()
    _run(monkeypatch, _chapter(6), workers=6, delay=0.1)
    elapsed = time.monotonic() - started
    assert elapsed < 0.4, f"expected overlap, took {elapsed:.2f}s (sequential would be ~0.6s)"


def test_workers_of_one_is_still_supported(monkeypatch):
    """The escape hatch: PODCAST_FACTORY_CORRECT_WORKERS=1 restores the old path."""
    out, warnings, fake = _run(monkeypatch, _chapter(3), workers=1)
    assert out == _chapter(3)
    assert warnings == []
    assert fake.steps == ["ch-window-01", "ch-window-02", "ch-window-03"]
