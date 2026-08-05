#!/usr/bin/env python3
"""holistic_editorial.py — Phase 0a-synthesize bridge for audio-sourced books.

Runs AFTER transcribe_audio_book.py has produced the faithful master
(_system/source/text/raw-extract.md). This is the holistic editorial pass that
the audio path needs and the windowed Phase 0b cannot do: it reviews the WHOLE
book at once, reorganizes it into a logical flow, denoises off-topic content, and
enriches the author's OWN language — bounded by a teaching-ledger fidelity gate.

Three staged `claude -p` calls (flat-rate Max, $0 marginal):
  1. TEACHING LEDGER  — extract every key teaching/claim/doctrine/scriptural
     anchor (+ source span) → _system/source/text/_teaching-ledger.json. The
     fidelity baseline.
  2. EDITORIAL        — reorganize + denoise + enrich language → unified-book.md
     (the file chapter-design prefers) + refined-english.md + _reorg-map.md +
     _curation-log.md. MUST preserve every ledger item; MAY NOT add external
     doctrine inline (external content stays a marked annotation, added later by
     the corpus/cross-book enrichment step, never here).
  3. FIDELITY GATE    — verify the enhanced text against the ledger; write
     _teaching-ledger-coverage.md; append any miss/distortion/inline-import to
     _open-questions.md. Blocks (exit 3) if coverage is incomplete.

The faithful master (raw-extract.md) is NEVER mutated. On success, advances
orchestrator-state to phase=0c (the registered phase the rest of the Islamic
pipeline resumes from).

Usage:
  python3 scripts/podcast/holistic_editorial.py --slug <book-slug>
  python3 scripts/podcast/holistic_editorial.py --slug <slug> --skip-fidelity   (debug)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _authoring._core import _run_claude_p
from _paths import REPO_ROOT, content_dir, find_content

LEDGER_TIMEOUT = 1800
EDITORIAL_TIMEOUT = 3600
FIDELITY_TIMEOUT = 1800
# Enhanced edition must retain >= this fraction of the faithful word count. Denoising
# oral redundancy + tangents removes ~25-45%; anything below this floor is summarization.
OVER_COMPRESSION_FLOOR = 0.45


def _die(msg: str) -> int:
    print(f"holistic_editorial: {msg}", file=sys.stderr)
    return 2


def _info(msg: str) -> None:
    print(msg)


def _resolve_book_dir(slug: str) -> Path | None:
    hit = find_content(slug)
    if hit:
        return hit[2]
    cand = content_dir(slug)
    return cand if cand.exists() else None


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def _ledger_prompt(raw: Path, ledger: Path) -> str:
    return f"""You are extracting a TEACHING LEDGER from an Ismaili scholarly book's faithful transcript.

Read: {_rel(raw)}

Write a JSON array to: {_rel(ledger)}

Each element is one KEY TEACHING the book conveys — a doctrine, claim, definition, ruling, named
authority, scriptural anchor (Quran/hadith), or core argument. For each, output an object:
  {{"id": "T001", "teaching": "<one-sentence statement of the teaching, plain English>",
    "kind": "doctrine|definition|claim|ruling|authority|scripture|argument",
    "source_marker": "<the <!-- lecture N --> the teaching first appears under>",
    "key_terms": ["<arabic-transliterated terms central to it>"]}}

Rules:
- Be COMPLETE: capture every distinct teaching, not a summary. A 15-lecture book typically yields
  many dozens of ledger items.
- One teaching per element; split compound teachings.
- Plain ASCII transliteration for Arabic terms (no diacritics).
- Output ONLY the JSON array to the file. No prose, no markdown fences.
"""


def _editorial_prompt(raw: Path, ledger: Path, unified: Path, refined: Path, reorg: Path, curation: Path) -> str:
    return f"""You are the holistic editor of an Ismaili scholarly book assembled from lecture transcripts.

INPUTS (read both):
- Faithful transcript: {_rel(raw)}
- Teaching ledger (the fidelity contract): {_rel(ledger)}

PRODUCE the enhanced reading edition. Write the SAME enhanced text to BOTH:
- {_rel(unified)}
- {_rel(refined)}

YOUR LATITUDE (granted): you MAY
- Reorganize the material into a logical, systematic flow (reorder, merge, and segment into
  themed sections with clear H2 headings) so a reader builds understanding progressively.
- Denoise: REMOVE content not related to the book's teaching — personal recollections, unrelated
  incidents, false starts, filler, audio/technical crosstalk ("can you hear me"), repetition.
- Enrich/augment the AUTHOR'S OWN language: smooth, clarify, and strengthen the prose for reading.

YOUR HARD LIMITS (the fidelity contract): you MUST
- Preserve EVERY teaching in the ledger — present AT FULL DEPTH and undistorted. "Present" means the
  teaching's complete exposition survives: its reasoning, its examples, its scriptural support, and
  the teacher's elaboration — NOT a one-line mention.
- DO NOT SUMMARIZE, ABRIDGE, OR COMPRESS. This is a full reading EDITION, not a summary or study
  guide. You are reorganizing and polishing the SAME material, not condensing it. Reproduce the
  teacher's full development of each point in flowing prose.
- LENGTH EXPECTATION: denoising removes oral redundancy (the same point restated 3x), filler, and
  genuine off-topic tangents — typically 25-45% of a lecture transcript. The enhanced edition should
  therefore be roughly 55-75% of the faithful word count (here: expect ~50,000-68,000 words from
  ~90,800). If your output is dramatically shorter than that, you have SUMMARIZED — that is a
  FAILURE; expand it back to full exposition before finishing.
- KEEP book-serving framing (a story/example that sets up a teaching stays; only OFF-topic asides go).
- NOT add any external doctrine, citation, verse, or authority that is not already in the transcript.
  (External enrichment is added LATER as marked annotations by a separate step — not here. This pass
  only reorganizes + polishes + fully renders what the author already said.)
- Use plain ASCII transliteration for Arabic (no diacritics); keep Quran/Arabic quotes verbatim.

ALSO write:
- {_rel(reorg)} — a markdown table mapping each enhanced H2 section -> the source <!-- lecture N -->
  span(s) it came from, so every reorganized passage traces back to origin.
- {_rel(curation)} — a markdown list of every span you REMOVED in denoise, each with a one-line
  reason, plus a closing line: "Faithful words: <N>  ->  Enhanced words: <M>  (removed ~<N-M>)".

Output files only; no chat response.
"""


def _fidelity_prompt(refined: Path, ledger: Path, coverage: Path, openq: Path) -> str:
    return f"""You are the FIDELITY GATE for an enhanced Ismaili book. Verify the editorial pass did not
deviate from the book's key teachings. Enrichment of the author's own language is ALLOWED;
deviation (dropping/distorting a teaching, or inserting external doctrine inline) is NOT.

INPUTS (read both):
- Enhanced text: {_rel(refined)}
- Teaching ledger: {_rel(ledger)}

Write a coverage report to: {_rel(coverage)}
A markdown table: | Ledger ID | Teaching | Present? (yes/no) | At full depth? (yes/no) | Note |
"Present" requires the teaching's FULL exposition to survive — its reasoning, examples, and
scriptural support — NOT a one-line mention. A teaching reduced to a bare summary is "Present=yes,
At full depth=no" and MUST be flagged (the editorial summarized instead of preserving depth).
End with a summary line: "Coverage: <present>/<total> present, <full-depth>/<total> at full depth."

For EVERY ledger item that is missing, distorted, OR any place where external doctrine/citation
appears to have been inserted inline (not in the original transcript), APPEND a section to:
- {_rel(openq)}
under a heading "## Fidelity-gate flags (holistic editorial)", each as:
  - [<severity P0/P1>] <ledger id or location>: <what is wrong> — <recommended fix>

Output files only; no chat response.
"""


def run(slug: str, *, skip_fidelity: bool = False) -> int:
    book_dir = _resolve_book_dir(slug)
    if book_dir is None:
        return _die(f"book workspace not found for slug {slug!r}")

    text_dir = book_dir / "_system" / "source" / "text"
    raw = text_dir / "raw-extract.md"
    if not raw.exists() or not raw.read_text(encoding="utf-8").strip():
        return _die(f"faithful master missing/empty: {_rel(raw)} (run transcribe_audio_book.py first)")

    ledger = text_dir / "_teaching-ledger.json"
    unified = book_dir / "_system" / "unified-book.md"
    refined = text_dir / "refined-english.md"
    reorg = text_dir / "_reorg-map.md"
    curation = text_dir / "_curation-log.md"
    coverage = text_dir / "_teaching-ledger-coverage.md"
    openq = text_dir / "_open-questions.md"

    # 1 — teaching ledger
    _info("==> [1/3] Extracting teaching ledger (claude -p) ...")
    rc, _out, err = _run_claude_p(
        _ledger_prompt(raw, ledger),
        timeout=LEDGER_TIMEOUT,
        book_dir=book_dir,
        phase="0a-synthesize",
        step="teaching-ledger",
    )
    if rc != 0 or not ledger.exists():
        return _die(f"ledger extraction failed (rc={rc}): {err[:400]}")
    try:
        items = json.loads(ledger.read_text(encoding="utf-8"))
        _info(f"    ledger: {len(items)} teachings")
    except Exception as e:
        return _die(f"ledger is not valid JSON: {e}")

    # Arabic baseline BEFORE the first mutating pass (R-ARABIC-INTEGRITY).
    try:
        import arabic_integrity as _ai

        _ai.snapshot(slug)
    except Exception as _e:
        _info(f"    (arabic-integrity snapshot skipped: {_e!r})")
        _ai = None

    # 2 — holistic editorial
    _info("==> [2/3] Holistic editorial — reorganize + denoise + enrich (claude -p) ...")
    rc, _out, err = _run_claude_p(
        _editorial_prompt(raw, ledger, unified, refined, reorg, curation),
        timeout=EDITORIAL_TIMEOUT,
        book_dir=book_dir,
        phase="0a-synthesize",
        step="holistic-editorial",
    )
    if rc != 0 or not refined.exists() or not unified.exists():
        return _die(f"editorial pass failed (rc={rc}): {err[:400]}")
    faithful_words = len(raw.read_text(encoding="utf-8").split())
    enhanced_words = len(refined.read_text(encoding="utf-8").split())
    ratio = enhanced_words / max(faithful_words, 1)
    _info(f"    wrote {_rel(refined)} ({enhanced_words:,} words = {ratio:.0%} of faithful) + unified-book.md")
    if ratio < OVER_COMPRESSION_FLOOR:
        _info(
            f"    ⚠ OVER-COMPRESSION: enhanced is {ratio:.0%} of faithful "
            f"(<{OVER_COMPRESSION_FLOOR:.0%}). That is summarization, not denoise — the full "
            f"exposition of each teaching was lost. NOT advancing; re-run the editorial."
        )
        return 3

    # 3 — fidelity gate
    if skip_fidelity:
        _info("==> [3/3] fidelity gate SKIPPED (--skip-fidelity)")
    else:
        _info("==> [3/3] Fidelity gate — verify ledger coverage (claude -p) ...")
        rc, _out, err = _run_claude_p(
            _fidelity_prompt(refined, ledger, coverage, openq),
            timeout=FIDELITY_TIMEOUT,
            book_dir=book_dir,
            phase="0a-synthesize",
            step="fidelity-gate",
        )
        if rc != 0 or not coverage.exists():
            return _die(f"fidelity gate failed (rc={rc}): {err[:400]}")
        cov = coverage.read_text(encoding="utf-8")
        _info("    " + (cov.strip().splitlines()[-1] if cov.strip() else "(coverage written)"))
        # Hard gate: refuse to advance if coverage line reports a shortfall.
        last = cov.strip().splitlines()[-1].lower() if cov.strip() else ""
        if "coverage:" in last:
            import re

            m = re.search(r"coverage:\s*(\d+)\s*/\s*(\d+)", last)
            if m and m.group(1) != m.group(2):
                _info(
                    f"    ⚠ ledger coverage incomplete ({m.group(1)}/{m.group(2)}) — see "
                    f"{_rel(openq)}. NOT advancing phase."
                )
                return 3

    # Arabic verify AFTER the editorial/fidelity passes (R-ARABIC-INTEGRITY).
    if _ai is not None and _ai.verify(slug, "0a") == _ai.EXIT_FORBIDDEN:
        _info(
            f"    ⚠ R-ARABIC-INTEGRITY: forbidden Arabic mutation — see _system/{_ai.REPORT_NAME}. NOT advancing phase."
        )
        return 3

    # advance state
    state_path = book_dir / "_system" / "orchestrator-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["last_completed_phase"] = "0a"
    state["phase"] = "0c"
    state["phase_status"] = "pending"
    state["last_error"] = None
    state["updated"] = now
    state.setdefault("phases", {})["0a-synthesize"] = {
        "completed_via": "holistic_editorial.py (claude -p)",
        "completed_at": now,
        "teachings_in_ledger": len(items),
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    _info("")
    _info("==> DONE. Enhanced text ready; state advanced to phase=0c.")
    _info(f"    review: {_rel(refined)} + {_rel(coverage)} + {_rel(openq)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--skip-fidelity", action="store_true", help="debug: skip the fidelity gate")
    args = ap.parse_args()
    return run(args.slug, skip_fidelity=args.skip_fidelity)


if __name__ == "__main__":
    sys.exit(main())
