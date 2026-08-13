"""_kashkole_gates.py — judging a Kashkole rendering, apart from producing one.

Split out of `translate_kashkole.py` under the repo's DR-005 600-line module
gate, following the pattern ADR-0001 established: extract verbatim, re-export one
line per name. The gate was right about the seam, as it was there — a judgement
ABOUT a rendering is a different concern from the pass that produces one, and
this module's existence is what makes `--rescore` honest: a corrected gate
re-scores stored English without paying to translate it again.

Two gates, and both exist because of something that actually went wrong:

  * LENGTH. REQ-BA-100 says a rendering is never shorter than its source, and a
    whole-body call on a 300,000-character topic comes back abridged. Below 60%
    the rendering is `short`.
  * QUR'ANIC RETENTION. The source is Urdu in Arabic script, so "did Arabic
    survive" is meaningless here; "did the Qur'an verse this passage quotes
    survive" is exactly what REQ-BA-060 is asking, and the canonical mushaf can
    answer it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
for _p in (str(_SCRIPTS), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _arabic_coverage import ARABIC_BODY, arabic_span_is_grounded  # noqa: E402

try:
    from _mushaf import is_quranic, mushaf_available
except Exception:  # pragma: no cover - the mirror may be absent on a fresh clone

    def mushaf_available() -> bool:
        return False

    def is_quranic(span: str) -> bool:
        return False


# Output shorter than this share of its source is an abridgement, not a
# translation. Same 60% floor the rearticulation gate uses, and for the same
# reason: REQ-BA-100 says a rendering is never shorter.
SHORT_RATIO = 0.60

_ARABIC_RUN_RE = re.compile(rf"[{ARABIC_BODY}]+(?:\s+[{ARABIC_BODY}]+)*")


def quranic_runs(text: str, *, min_words: int = 4) -> list[str]:
    """Arabic-script runs in ``text`` the canonical mushaf recognises as scripture.

    Used as a RETENTION check rather than a translation aid. The whole source is
    Arabic script, so "did Arabic survive" is meaningless here — but "did the
    Qur'an verse this passage quotes survive" is exactly the question REQ-BA-060
    is asking on a corpus like this one, and the mushaf can answer it.
    """
    if not mushaf_available():
        return []
    found: list[str] = []
    for run in _ARABIC_RUN_RE.findall(text or ""):
        if len(run.split()) < min_words:
            continue
        try:
            if is_quranic(run):
                found.append(run)
        except Exception:
            continue
    return found


def _normalize(text: str) -> str:
    return " ".join((text or "").split())


def check(source: str, rendered: str) -> tuple[str, list[str]]:
    """`(status, concerns)` for one rendering. Never raises."""
    concerns: list[str] = []
    src, out = _normalize(source), _normalize(rendered)
    if not out:
        return "failed", ["empty rendering"]

    ratio = len(out) / max(1, len(src))
    if ratio < SHORT_RATIO:
        concerns.append(f"abridged: rendering is {ratio:.0%} of the source")

    # A Qur'an verse quoted in the source must still be there.
    #
    # COMPARED ON THE CONSONANTAL SKELETON, via the same `arabic_span_is_grounded`
    # the provenance code uses to ask whether a run was copied rather than
    # remembered. A raw substring test was the first implementation and it was
    # wrong in the way that matters: the renderer wraps a verse in bidi marks and
    # may set it in the mushaf's own spelling, so `in` reported a verse missing
    # while it sat in the output two lines further down. Two of the first three
    # probe topics were flagged for verses that were plainly there.
    for run in quranic_runs(source):
        if not arabic_span_is_grounded(run, rendered):
            concerns.append(f"quranic run not carried through: {run[:40]}")

    status = "short" if any(c.startswith("abridged") for c in concerns) else "ok"
    if any(c.startswith("quranic") for c in concerns):
        status = "short" if status == "short" else "review"
    return status, concerns
