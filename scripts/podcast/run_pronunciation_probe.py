#!/usr/bin/env python3
"""run_pronunciation_probe.py — build ONE NotebookLM bundle that settles a book's pronunciation.

The problem this exists for: a book's Arabic terms are spread across every
chapter, and the only way to know how NotebookLM will say one is to hear it.
Generating the whole book to find out costs hours and burns the chapters you
would then have to regenerate — which is what happened to `degrees-of-excellence`
on 2026-08-01, where "imamate" came back garbled in 33 of 34 utterances across
six finished episodes.

So: rank every term in the book by how likely it is to be mangled, drop the ones
the cross-book ledger already settled, and emit ONE short bundle — a source to
upload and a framing to paste — whose only job is to make the hosts say each
surviving term once, in a sentence taken verbatim from the real chapters. You
listen to a few minutes of audio instead of hours, mark what came out wrong, and
the verdicts are written to `content/knowledge-base/pronunciations.jsonl`, where
every future Arabic book inherits them.

Two deterministic steps, no model spend:

    score_pronunciation_risk.py   glossary + overrides + ledger -> probe-terms.json
    build_probe_bundle.py         probe-terms.json + chapters   -> the bundle

Usage:
    python3 scripts/podcast/run_pronunciation_probe.py <book-slug> [--top-n N] [--rebuild]

Output (all under BOOK_DIR/_system/probe/):
    probe-terms.json                          the ranked terms
    EP00-pronunciation-probe/
        pronunciation-probe.md                upload this to NotebookLM
        00-framing.md                         paste this into Customize
        listen-checklist.md                   fill this in while listening
        README.md                             the upload settings

Then, to turn what you heard into corrections every later book inherits:
    the `pronunciation-probe-analyst` agent  (transcribes, diffs, writes the ledger)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _paths import find_content, relative_to_repo  # noqa: E402

PROBE_DIR = _HERE / "probe"


def _run(script: Path, args: list[str]) -> None:
    """Run a probe step in its own process so its sys.path setup is the one it expects."""
    result = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.returncode != 0:
        sys.exit(f"ERROR: {script.name} failed:\n{result.stderr.rstrip()}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", help="book slug, e.g. degrees-of-excellence")
    ap.add_argument("--top-n", type=int, default=40, help="how many terms to probe (default 40)")
    ap.add_argument(
        "--rebuild",
        action="store_true",
        help="re-rank the terms even when probe-terms.json already exists",
    )
    args = ap.parse_args(argv)

    found = find_content(args.slug)
    if found is None:
        sys.exit(f"ERROR: no book found for slug '{args.slug}'")
    _status, _bucket, book_dir = found

    terms_path = book_dir / "_system" / "probe" / "probe-terms.json"
    if args.rebuild or not terms_path.exists():
        _run(PROBE_DIR / "score_pronunciation_risk.py", [str(book_dir), "--top-n", str(args.top_n)])
    else:
        print(f"probe-terms.json already present ({relative_to_repo(terms_path)}) — pass --rebuild to re-rank.")

    _run(PROBE_DIR / "build_probe_bundle.py", [str(book_dir)])

    data = json.loads(terms_path.read_text(encoding="utf-8"))
    bundle = book_dir / "_system" / "probe" / "EP00-pronunciation-probe"
    settled = data.get("skipped_confirmed", 0) + data.get("skipped_unfixable", 0)

    print(
        f"\n{len(data['terms'])} term(s) to hear"
        + (f" — {settled} already settled by earlier books and skipped" if settled else "")
        + ".\n\n"
        "| Chapters | Episodes | Deep dive or debate | Length |\n"
        "|---|---|---|---|\n"
        f"| [Pronunciation probe]({relative_to_repo(bundle / 'pronunciation-probe.md')}) "
        f"| [EP00 — pronunciation probe]({relative_to_repo(bundle / '00-framing.md')}) "
        "| Deep dive | Shorter |\n\n"
        "Upload the left file as the only source, paste the right one into Customize, and\n"
        "generate at the Shorter length — this is a three-minute diagnostic, not an episode.\n"
        f"Listen with {relative_to_repo(bundle / 'listen-checklist.md')} open.\n\n"
        "When the audio is down, hand it to the `pronunciation-probe-analyst` agent — it\n"
        "transcribes, compares what was said against what was intended, and writes the\n"
        "verdicts to the cross-book ledger so no later book re-derives them."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
