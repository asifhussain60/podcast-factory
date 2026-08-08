"""_window_cache.py — when a cached window of a windowed phase may be reused.

Split out of `_chunking` on 2026-08-08. It is the second freshness rule in this repo
and it deliberately does NOT work like the first, so it gets its own file and its own
test rather than being a paragraph inside the dispatcher.

TWO OPPOSITE DEFECTS, and this has to avoid both.

  UNDER-invalidation — what phase 0b actually did. The resume check was a bare
  `out_path.exists()` with nothing compared against the input, so a window refined
  from one source was silently reused after the source changed, and every later phase
  then worked from prose that answered a different text.

  OVER-invalidation — what an mtime rule does. `_translation_cache` compares mtimes
  against a set of governing files. That is correct about staleness and expensive
  about everything else: a `git checkout`, a `git pull` or a whitespace edit to a
  shared module rewrites an mtime and discards work that is still perfectly valid.
  Re-refining a 28-window book costs about $8 of metered API — measured on
  `spiritual-ethos` on 2026-08-05, where four repeats of a pass it already had came to
  $8.38, 81% of that book's entire real spend. A false invalidation is not a safe
  default here; it is the bug this pass exists to stop.

So the comparison is a CONTENT fingerprint, and a pre-existing cache is ADOPTED rather
than discarded — otherwise the check would charge for its own introduction across every
book in the repo the first time it ran.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

FINGERPRINT_NAME = ".source-fingerprint"


def cache_fingerprint(text: str, *, target_words: int, overlap_words: int) -> str:
    """Identity of a windowed run's INPUT — content, never mtime.

    The window parameters are part of it because they decide where the boundaries fall:
    the same source at a different `target_words` produces different windows, so
    `win-003` from one segmentation is not the `win-003` of another and reusing it would
    splice unrelated prose together.
    """
    h = hashlib.sha256()
    h.update(f"v1|{int(target_words)}|{int(overlap_words)}|".encode("utf-8"))
    h.update(text.encode("utf-8"))
    return h.hexdigest()


@dataclass
class CacheDecision:
    """What the caller needs to know, plus what to report about it."""

    stale: bool
    #: Ledger outcome + reason, or None when there is nothing worth recording.
    outcome: str | None
    reason: str | None
    #: Human-facing line, or None.
    message: str | None


def evaluate(
    chunks_dir: Path,
    text: str,
    *,
    target_words: int,
    overlap_words: int,
    total: int,
) -> CacheDecision:
    """Decide whether `chunks_dir`'s cached windows may be reused, and say why.

    Writes the current fingerprint as a side effect, so the NEXT run has something to
    compare against — including on the adoption path, which is what makes the guarantee
    start applying without a re-spend. An unwritable fingerprint is ignored rather than
    raised: a cache bookkeeping file must never stop the phase it describes.
    """
    fp_path = chunks_dir / FINGERPRINT_NAME
    fp_now = cache_fingerprint(text, target_words=target_words, overlap_words=overlap_words)
    existing = any(chunks_dir.glob("win-*.out.md"))
    try:
        fp_prev = fp_path.read_text(encoding="utf-8").strip() if fp_path.exists() else ""
    except OSError:
        fp_prev = ""

    if fp_prev and fp_prev != fp_now:
        decision = CacheDecision(
            stale=True,
            outcome="ok",
            reason="source changed — cache invalidated",
            message=(
                f"    chunking: source CHANGED since the cached windows were written — "
                f"recomputing all {total} window(s) (fingerprint {fp_prev[:12]} -> {fp_now[:12]})"
            ),
        )
    elif not fp_prev and existing:
        decision = CacheDecision(
            stale=False,
            outcome="noop",
            reason="adopted a pre-fingerprint cache",
            message="    chunking: adopting an existing window cache (no fingerprint recorded before this run)",
        )
    elif not existing:
        # Worth a record even though nothing is wrong yet: on an UNCHANGED source this
        # is the "the cache vanished" condition that cost $8.38 five times over, and the
        # phase-review gate `window-cache-intact` reports it.
        decision = CacheDecision(stale=False, outcome="noop", reason="no cached windows present", message=None)
    else:
        decision = CacheDecision(stale=False, outcome=None, reason=None, message=None)

    try:
        fp_path.write_text(fp_now + "\n", encoding="utf-8")
    except OSError:
        pass
    return decision
