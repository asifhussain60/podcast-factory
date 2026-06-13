#!/usr/bin/env python3
"""normalize_m4a.py — drop-and-normalize step for NotebookLM audio + transcripts.

PURPOSE

    NotebookLM names its exported audio after the Audio Overview's creative
    title ("Why_Scholars_Silence_the_Living_Witness.m4a"), and any manual
    chapter prefix the operator adds is a CLAIM that can be wrong (a real
    19/20 swap shipped on 2026-06-12 and was caught only by hand). This
    script makes the filename irrelevant: after dropping new .m4a files
    (and/or TurboScribe .txt transcripts) anywhere under BOOK_DIR/m4a/, run

        python3 scripts/podcast/normalize_m4a.py <slug>            # dry-run plan
        python3 scripts/podcast/normalize_m4a.py <slug> --apply    # execute

    and every non-canonical file is fingerprint-matched to its chapter and
    renamed to the canonical layout:

        m4a/ch<NN><s>-<chapter-slug>.m4a
        m4a/transcripts/ch<NN><s>-<chapter-slug>.transcript.txt

EVIDENCE MODEL (strongest first)

    1. Transcript text — the first ~500 words of a .txt against each
       episode's framing + chapter source (token containment). Near-certain.
    2. Creative-title tokens — NotebookLM titles from what the hosts actually
       discussed, so the filename words fingerprint the episode even when a
       numeric prefix is wrong.
    3. Numeric prefix — recorded as the operator's CLAIM and compared against
       the verdict (a mismatch is reported as a SWAP), never trusted alone.

    A rename happens only when the best match beats the runner-up by a clear
    margin AND the target chapter has no canonical file already. Anything
    ambiguous is left untouched and reported for human resolution.

LEDGER

    Every decision (including dry-run verdicts on --apply) is appended to
    BOOK_DIR/m4a/_review/prefix-verification.json — the same ledger the
    2026-06 manual verifications used.

NON-GOALS

    Audio transcription (no STT dependency); challenger-grade content QA
    (postprod-review owns that); moving files between books.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import find_content  # noqa: E402

CH_STEM_RE = re.compile(r"^ch(\d{2})([a-z]?)-([a-z0-9][a-z0-9-]*)$")
EP_FILE_RE = re.compile(r"^EP(\d{2})-([a-z0-9][a-z0-9-]*)\.txt$")
CLAIM_RE = re.compile(r"^(?:ch)?(\d{1,2})\b")

# Words too common in this corpus to discriminate between episodes.
STOPWORDS = frozenset(
    "the a an and or of to in on for with as at by is are was were be this "
    "that it its from into your you we our their his her they he she not no "
    "what why how when who which one two three master disciple book episode "
    "chapter podcast audio overview notebooklm deep dive debate".split()
)

MIN_SCORE = 0.18          # filename probe: best match must clear this floor
MIN_MARGIN = 1.35         # ... and beat the runner-up by this ratio
MIN_TEXT_SCORE = 0.03     # transcript probe (trigram evidence is sparser but sharper)
MIN_TEXT_MARGIN = 1.5
TRANSCRIPT_PROBE_WORDS = 500


def _tokens(text: str) -> set[str]:
    words = re.split(r"[^a-z0-9']+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9']+", text.lower()) if w]


def _trigrams(words: list[str]) -> set[str]:
    return {" ".join(words[i:i + 3]) for i in range(len(words) - 2)}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Chapter:
    """One canonical chapter/episode pair and its fingerprint corpus."""

    def __init__(self, stem: str, num: int, episode_file: Path | None,
                 chapter_file: Path):
        self.stem = stem                      # ch19c-the-conspiracy-formula
        self.num = num
        self.episode_file = episode_file
        self.chapter_file = chapter_file
        title_part = CH_STEM_RE.match(stem).group(3).replace("-", " ")
        self.title_tokens = _tokens(title_part)
        body = ""
        if episode_file is not None and episode_file.exists():
            body += episode_file.read_text(encoding="utf-8", errors="replace")
        try:
            body += " " + chapter_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        self.body_tokens = _tokens(body)
        self.body_trigrams = _trigrams(_words(body))

    def score(self, probe: set[str], idf: dict[str, float] | None = None,
              max_idf: float = 1.0) -> float:
        """IDF-weighted containment of probe tokens in this chapter's corpus.

        Sibling episodes of one book share most of their vocabulary (debate
        framing, the book's own recurring terms), so a raw-overlap score
        drifts toward whichever chapter has the LARGEST corpus — a 2026-06-12
        live run matched two correct transcripts to the wrong (biggest)
        chapter that way. Weighting each token by inverse document frequency
        across the book's chapters makes shared vocabulary worthless and
        chapter-specific phrases decisive. Title tokens stay separately
        weighted: they are the strongest discriminator for filename probes.
        """
        if not probe:
            return 0.0
        title_hit = len(probe & self.title_tokens) / max(len(self.title_tokens), 1)
        if idf is None:
            body_hit = len(probe & self.body_tokens) / len(probe)
        else:
            num = sum(idf.get(t, 0.0) for t in probe & self.body_tokens)
            den = sum(idf.get(t, max_idf) for t in probe)
            body_hit = num / den if den > 0 else 0.0
        return 0.6 * title_hit + 0.4 * body_hit


def load_chapters(book_dir: Path) -> list[Chapter]:
    chapters: list[Chapter] = []
    episodes: dict[int, Path] = {}
    ep_dir = book_dir / "episodes"
    if ep_dir.is_dir():
        for p in sorted(ep_dir.glob("EP*.txt")):
            m = EP_FILE_RE.match(p.name)
            if m:
                episodes[int(m.group(1))] = p
    for p in sorted((book_dir / "chapters").glob("ch*.txt")):
        m = CH_STEM_RE.match(p.stem)
        if m:
            num = int(m.group(1))
            chapters.append(Chapter(p.stem, num, episodes.get(num), p))
    return chapters


def _claimed_number(name: str) -> int | None:
    m = CLAIM_RE.match(name)
    return int(m.group(1)) if m else None


def _build_idf(chapters: list[Chapter], attr: str) -> tuple[dict[str, float], float]:
    """Inverse document frequency over a per-chapter feature set (`attr` names
    a set attribute: 'body_tokens' or 'body_trigrams'; title_tokens fold into
    the token table).

    A feature present in every chapter scores 0 (no signal); one unique to a
    single chapter scores log(N). Probe features absent from all chapters get
    max_idf in the denominator so noise still dilutes confidence.
    """
    from math import log
    n = len(chapters)
    df: dict[str, int] = {}
    for c in chapters:
        feats = set(getattr(c, attr))
        if attr == "body_tokens":
            feats |= c.title_tokens
        for t in feats:
            df[t] = df.get(t, 0) + 1
    max_idf = log(n) if n > 1 else 1.0
    return {t: log(n / d) for t, d in df.items()}, max_idf


def _rank(scored: list[tuple[float, "Chapter"]]) -> tuple["Chapter | None", float, float, "Chapter | None"]:
    scored.sort(key=lambda t: t[0], reverse=True)
    best_score, best = scored[0]
    runner_score, runner = (scored[1] if len(scored) > 1 else (0.0, None))
    margin = best_score / runner_score if runner_score > 0 else float("inf")
    return best, best_score, margin, runner


def _match(probe: set[str], chapters: list[Chapter]) -> tuple[Chapter | None, float, float, Chapter | None]:
    """Filename-token match: (best, best_score, margin_ratio, runner_up)."""
    if not chapters:
        return None, 0.0, 0.0, None
    idf, max_idf = _build_idf(chapters, "body_tokens")
    return _rank([(c.score(probe, idf, max_idf), c) for c in chapters])


def _match_text(probe_words: list[str], chapters: list[Chapter]) -> tuple[Chapter | None, float, float, Chapter | None]:
    """Transcript-text match via IDF-weighted trigram containment.

    Token-set overlap fails on transcript probes: sibling episodes of one
    book share most vocabulary (debate framing, the book's recurring
    theology), so the biggest chapter corpus wins — a 2026-06-12 live run
    mismatched 7 of 20 KNOWN-correct transcripts that way. Verbatim PHRASES
    are the real signal (framings dictate exact spine lines the hosts speak),
    so we match word-trigrams, IDF-discounted so boilerplate shared across
    framings ("welcome to the debate") carries no weight. Validated 20/20 on
    the-master-and-the-disciple with min margin 2.2.
    """
    if not chapters:
        return None, 0.0, 0.0, None
    probe = _trigrams(probe_words)
    if not probe:
        return None, 0.0, 0.0, None
    idf, max_idf = _build_idf(chapters, "body_trigrams")
    den = sum(idf.get(t, max_idf) for t in probe)
    scored = [
        (sum(idf.get(t, 0.0) for t in probe & c.body_trigrams) / den if den > 0 else 0.0, c)
        for c in chapters
    ]
    return _rank(scored)


def plan_book(book_dir: Path) -> list[dict]:
    """Build the rename plan. Pure read — never mutates."""
    chapters = load_chapters(book_dir)
    m4a_dir = book_dir / "m4a"
    tx_dir = m4a_dir / "transcripts"
    plan: list[dict] = []
    if not m4a_dir.is_dir() or not chapters:
        return plan

    canonical_stems = {c.stem for c in chapters}
    taken_audio = {p.stem for p in m4a_dir.glob("*.m4a") if p.stem in canonical_stems}
    taken_tx = {p.name.removesuffix(".transcript.txt")
                for p in tx_dir.glob("*.transcript.txt")} if tx_dir.is_dir() else set()

    # ── Audio: any *.m4a in m4a/ root whose stem is not canonical ────────────
    for p in sorted(m4a_dir.glob("*.m4a")):
        if p.stem in canonical_stems:
            continue
        probe = _tokens(p.stem.replace("_", " ").replace("-", " "))
        best, score, margin, runner = _match(probe, chapters)
        entry = {
            "file": p.name, "kind": "audio",
            "claimed": _claimed_number(p.name),
            "best": best.stem if best else None,
            "best_num": best.num if best else None,
            "score": round(score, 3), "margin": round(margin, 2),
            "runner_up": runner.stem if runner else None,
            "evidence": "title-tokens",
        }
        if best is None or score < MIN_SCORE or margin < MIN_MARGIN:
            entry.update(verdict="AMBIGUOUS",
                         action=None,
                         note="no confident match — resolve by transcript or by hand")
        elif best.stem in taken_audio:
            entry.update(verdict="COLLISION", action=None,
                         note=f"canonical {best.stem}.m4a already exists — duplicate drop?")
        else:
            verdict = "MATCH"
            if entry["claimed"] is not None and entry["claimed"] != best.num:
                verdict = "SWAP"  # the operator's prefix disagrees with the content
            entry.update(verdict=verdict,
                         action={"rename_to": f"{best.stem}.m4a"})
            taken_audio.add(best.stem)
        plan.append(entry)

    # ── Transcripts: loose .txt in m4a/ root + any export subdirs ────────────
    candidates: list[Path] = [p for p in m4a_dir.glob("*.txt")]
    for sub in m4a_dir.iterdir():
        if sub.is_dir() and sub.name not in ("transcripts", "_review", "v1"):
            candidates.extend(sorted(sub.glob("*.txt")))
    for p in sorted(candidates):
        stem = p.stem.removesuffix(".transcript")
        if stem in canonical_stems and stem not in taken_tx:
            # Right stem already — just needs to move into transcripts/.
            plan.append({
                "file": str(p.relative_to(m4a_dir)), "kind": "transcript",
                "claimed": _claimed_number(p.name), "best": stem,
                "best_num": int(CH_STEM_RE.match(stem).group(1)),
                "score": 1.0, "margin": float("inf"), "runner_up": None,
                "evidence": "canonical-stem", "verdict": "MATCH",
                "action": {"rename_to": f"transcripts/{stem}.transcript.txt"},
            })
            taken_tx.add(stem)
            continue
        probe_words = _words(p.read_text(encoding="utf-8", errors="replace"))[:TRANSCRIPT_PROBE_WORDS]
        best, score, margin, runner = _match_text(probe_words, chapters)
        entry = {
            "file": str(p.relative_to(m4a_dir)), "kind": "transcript",
            "claimed": _claimed_number(p.name),
            "best": best.stem if best else None,
            "best_num": best.num if best else None,
            "score": round(score, 3), "margin": round(margin, 2),
            "runner_up": runner.stem if runner else None,
            "evidence": "transcript-trigrams",
        }
        if best is None or score < MIN_TEXT_SCORE or margin < MIN_TEXT_MARGIN:
            entry.update(verdict="AMBIGUOUS", action=None,
                         note="no confident match — resolve by hand")
        elif best.stem in taken_tx:
            entry.update(verdict="COLLISION", action=None,
                         note=f"transcripts/{best.stem}.transcript.txt already exists")
        else:
            verdict = "MATCH"
            if entry["claimed"] is not None and entry["claimed"] != best.num:
                verdict = "SWAP"
            entry.update(verdict=verdict,
                         action={"rename_to": f"transcripts/{best.stem}.transcript.txt"})
            taken_tx.add(best.stem)
        plan.append(entry)

    return plan


def apply_plan(book_dir: Path, plan: list[dict], *, log=print) -> int:
    """Execute the rename actions; append every entry to the ledger."""
    m4a_dir = book_dir / "m4a"
    renamed = 0
    for entry in plan:
        action = entry.get("action")
        if not action:
            continue
        src = m4a_dir / entry["file"]
        dst = m4a_dir / action["rename_to"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():  # re-check at execution time
            log(f"  SKIP {entry['file']} — target appeared: {action['rename_to']}")
            entry["verdict"] = "COLLISION"
            entry["action"] = None
            continue
        src.rename(dst)
        renamed += 1
        log(f"  {entry['verdict']:9s} {entry['file']} -> {action['rename_to']}")
    _append_ledger(book_dir, plan)
    # Clean up any export dir left empty by transcript moves.
    for sub in m4a_dir.iterdir():
        if sub.is_dir() and sub.name not in ("transcripts", "_review", "v1"):
            if not any(sub.iterdir()):
                sub.rmdir()
                log(f"  removed empty {sub.name}/")
    return renamed


def _append_ledger(book_dir: Path, plan: list[dict]) -> None:
    review = book_dir / "m4a" / "_review"
    review.mkdir(parents=True, exist_ok=True)
    ledger = review / "prefix-verification.json"
    data = json.loads(ledger.read_text()) if ledger.exists() else []
    ts = _utc_now()
    for entry in plan:
        data.append({**entry, "ts": ts, "tool": "normalize_m4a"})
    ledger.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def render_plan(plan: list[dict]) -> str:
    if not plan:
        return "nothing to normalize — all audio/transcripts already canonical."
    lines = [f"{'verdict':9s}  {'kind':10s}  file -> action"]
    for e in plan:
        act = e["action"]["rename_to"] if e.get("action") else f"(none — {e.get('note','')})"
        lines.append(f"{e['verdict']:9s}  {e['kind']:10s}  {e['file']} -> {act}"
                     f"   [score={e['score']}, margin={e['margin']}, claimed={e['claimed']}]")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Rename dropped NotebookLM audio/transcripts to canonical chapter order.")
    ap.add_argument("slug", help="book slug (any bucket)")
    ap.add_argument("--apply", action="store_true", help="execute the plan (default: dry-run)")
    ap.add_argument("--json", action="store_true", help="emit the plan as JSON")
    args = ap.parse_args()

    found = find_content(args.slug)
    if not found:
        print(f"ERROR: no content directory matches slug {args.slug!r}", file=sys.stderr)
        return 2
    book_dir = found[2]
    plan = plan_book(book_dir)

    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        print(render_plan(plan))

    ambiguous = [e for e in plan if e["verdict"] in ("AMBIGUOUS", "COLLISION")]
    if args.apply:
        if not plan:
            return 0
        n = apply_plan(book_dir, plan)
        print(f"\napplied: {n} rename(s); ledger updated "
              f"({book_dir.name}/m4a/_review/prefix-verification.json)")
        return 1 if ambiguous else 0
    if plan:
        print("\ndry-run only — re-run with --apply to execute.")
    return 1 if ambiguous else 0


if __name__ == "__main__":
    raise SystemExit(main())
