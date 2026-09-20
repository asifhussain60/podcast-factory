"""Pure helpers for the Urdu second-witness audit (urdu_witness.py drives them).

The Urdu PDF is a TRANSLATION of the Arabic primary, so it is a second witness
on claims (rulings, numbers, names, negations), never a text to diff.
"""

from __future__ import annotations

SEV_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def parse_ranges(spec: str) -> list[int]:
    """'1-3,7' -> [1, 2, 3, 7] (sorted, de-duplicated)."""
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        lo, _, hi = part.partition("-")
        a, b = int(lo), int(hi or lo)
        if b < a:
            raise ValueError(f"backwards range: {part}")
        pages.update(range(a, b + 1))
    return sorted(pages)


def page_stats(page: dict, *, low_conf: float = 0.8) -> dict:
    words = page.get("words") or []
    confs = [w.get("confidence", 0.0) for w in words]
    conf = round(sum(confs) / len(confs), 4) if confs else 0.0
    text = "\n".join(l.get("content", "") for l in page.get("lines") or [])
    return {
        "page": page.get("pageNumber"),
        "n_words": len(words),
        "conf": conf,
        "low": conf < low_conf or not words,
        "text": text,
    }


def cap_certainty(certainty: int, *, ocr_conf: float) -> int:
    """A flag can never be more certain than the Urdu OCR beneath it."""
    return min(int(certainty), int(round(ocr_conf * 100)))


def rank_flags(flags: list[dict]) -> list[dict]:
    return sorted(flags, key=lambda f: (SEV_ORDER.get(f["sev"], 9), -f["certainty"]))
