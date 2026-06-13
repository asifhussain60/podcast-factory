#!/usr/bin/env python3
"""build_audio_gold_standard.py — build the per-genre NotebookLM style reference.

Fingerprints the FULL m4a corpus of a content profile's NotebookLM-native books
and aggregates each metric to a median `center`, a relative tolerance `tol_rel`,
and the raw `p10`/`p90` spread. Writes the tracked asset

    content/_shared/audio-style/<profile>.json

which the post-render style gate scores ElevenLabs renders against. Calibration
rule: `tol_rel` is the SCORE_SPEC floor widened to the real corpus spread, so a
clip whose metrics sit within the genuine NotebookLM variation always passes
(an ear-approved render is never failed by an over-tight band).

Word counts (for wpm) come from each m4a's sibling transcript
(m4a/transcripts/<stem>.transcript.txt). Episodes without a transcript still
contribute every other metric.

USAGE
    python3 scripts/podcast/build_audio_gold_standard.py --profile islamic_scholarly
    python3 scripts/podcast/build_audio_gold_standard.py --profile islamic_scholarly \
        --books the-master-and-the-disciple ayyuhal-walad
    # --books omitted -> every book of the profile that has an m4a corpus.

No spend: pure local DSP. Re-run whenever episodes are added; the JSON diff is
the review artifact.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from _audio_fingerprint import (  # noqa: E402
    fingerprint_m4a, METRIC_KEYS, SCORE_SPEC,
)

# Style-gate pass threshold (0-100). This is a GROSS-DRIFT FLOOR, not a
# fidelity bar: the per-metric tolerance bands already encode the real corpus
# spread, so the threshold only needs to catch a render that does not sound
# like a two-host NotebookLM conversation at all. Calibrated 2026-06-13 so the
# ear-approved Eric/Lily demo (CLIP10, score 66.8) passes — that clip is a
# PESSIMISTIC lower bound (a pause-compressed 5-min excerpt; the production
# renderer does not compress pauses, and content-dependent share_male varies by
# chapter). DEFINITIVE confirmation happens against the first full-episode
# verification render. The gate is soft regardless: a sub-threshold episode
# earns at most ONE retake, then ships the better take with a sanity flag.
PASS_THRESHOLD = 65


def _iter_corpus_m4a(book_dir: Path):
    """Yield (m4a_path, transcript_path|None) for a book's episode audio.

    Skips working subfolders (_review/, v1/, casting/) — only the canonical
    top-level m4a/*.m4a are corpus episodes.
    """
    m4a_dir = book_dir / "m4a"
    if not m4a_dir.is_dir():
        return
    for m4a in sorted(m4a_dir.glob("*.m4a")):
        tx = m4a_dir / "transcripts" / f"{m4a.stem}.transcript.txt"
        yield m4a, (tx if tx.exists() else None)


def _books_for_profile(profile: str) -> list[Path]:
    """Every book dir whose content_profile == profile that has an m4a corpus."""
    from _paths import REPO_ROOT
    from _content_profile import resolve_content_profile
    from _rules import bucket_for_profile
    bucket = bucket_for_profile(profile)
    root = Path(REPO_ROOT) / "content" / bucket
    out: list[Path] = []
    if not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        if not (d / "m4a").is_dir() or not any((d / "m4a").glob("*.m4a")):
            continue
        try:
            if resolve_content_profile(d) == profile:
                out.append(d)
        except Exception:  # noqa: BLE001
            continue
    return out


def _resolve_book(slug: str) -> Path | None:
    from _paths import find_content
    try:
        ref = find_content(slug)   # (status, bucket, path) | None
        return Path(ref[2]) if ref else None
    except Exception:  # noqa: BLE001
        return None


def build(profile: str, book_slugs: list[str] | None,
          *, now: str, log=print) -> dict:
    if book_slugs:
        book_dirs = [b for b in (_resolve_book(s) for s in book_slugs) if b]
    else:
        book_dirs = _books_for_profile(profile)
    if not book_dirs:
        raise SystemExit(f"no books with an m4a corpus for profile {profile!r}")

    samples: dict[str, list[float]] = {k: [] for k in METRIC_KEYS}
    manifest: list[str] = []
    n_episodes = 0
    for book_dir in book_dirs:
        eps = list(_iter_corpus_m4a(book_dir))
        manifest.append(f"{book_dir.name} ({len(eps)})")
        log(f"[gold] {book_dir.name}: {len(eps)} episode(s)")
        for m4a, tx in eps:
            fp = fingerprint_m4a(m4a, transcript=tx)
            n_episodes += 1
            for k in METRIC_KEYS:
                if k in fp and fp[k]:
                    samples[k].append(float(fp[k]))
            log(f"  [gold] {m4a.name}: "
                + " ".join(f"{k}={fp.get(k)}" for k in ("wpm", "switches_per_min",
                                                        "share_male", "st_sd_male")))

    metrics: dict[str, dict] = {}
    for k in METRIC_KEYS:
        vals = samples[k]
        if not vals:
            continue
        arr = np.array(vals, dtype=float)
        center = float(np.median(arr))
        p10 = float(np.percentile(arr, 10))
        p90 = float(np.percentile(arr, 90))
        floor = SCORE_SPEC[k][1]
        # Widen the tolerance to the real corpus spread: the larger of the
        # SCORE_SPEC floor and the observed (p90-p10)/2 relative to the median.
        observed_rel = (p90 - p10) / (2 * abs(center)) if center else floor
        tol_rel = round(max(floor, observed_rel), 3)
        metrics[k] = {
            "center": round(center, 3),
            "tol_rel": tol_rel,
            "p10": round(p10, 3),
            "p90": round(p90, 3),
            "n": len(vals),
        }

    return {
        "profile": profile,
        "version": now,
        "corpus": manifest,
        "episodes_fingerprinted": n_episodes,
        "pass_threshold": PASS_THRESHOLD,
        "metrics": metrics,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="islamic_scholarly")
    ap.add_argument("--books", nargs="*", default=None,
                    help="explicit book slugs; default = all books of the profile")
    ap.add_argument("--date", default=None,
                    help="version stamp (YYYY-MM-DD); default = today (UTC)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the reference JSON, do not write")
    args = ap.parse_args()

    from _audio_fingerprint import _gold_standard_path
    if args.date:
        now = args.date
    else:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ref = build(args.profile, args.books, now=now)
    text = json.dumps(ref, indent=2) + "\n"
    if args.dry_run:
        print(text)
        return 0
    out = _gold_standard_path(args.profile)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"[gold] wrote {out} "
          f"({ref['episodes_fingerprinted']} episodes, "
          f"{len(ref['metrics'])} metrics)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
