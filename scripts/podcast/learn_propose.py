#!/usr/bin/env python3
"""learn_propose.py — emit rule-promotion proposals from patterns.md.

PURPOSE

  Stage 3 of the podcast-skill learning pipeline (sense → aggregate → PROPOSE
  → test → promote). Reads the latest `_learning/patterns.md`, finds every
  proposer-eligible signature (≥ 2 books OR ≥ 3 episodes), and emits one
  markdown proposal per signature under `_learning/proposals/`.

  Proposals are idempotent: re-running this script against the same
  `patterns.md` produces byte-identical proposal files. A proposal that
  already exists is overwritten in place ONLY if the signature's record
  set has changed; otherwise the existing file is left alone (mtime
  preserved).

USAGE

  python3 scripts/podcast/learn_propose.py

  Optional flags:
    --patterns <path>     Use a non-default patterns.md (for testing).
    --proposals-dir <p>   Write proposals to a non-default directory.
    --dry-run             Print what would be written; do not write.

OUTPUT

  One markdown file per proposer-eligible signature under
  `content/podcast/.skill/_learning/proposals/YYYY-MM-DD-<slug>.md`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER = REPO_ROOT / "content/podcast/.skill/_learning/findings.jsonl"
DEFAULT_PROPOSALS_DIR = REPO_ROOT / "content/podcast/.skill/_learning/proposals"
DEFAULT_PROMOTED_DIR = REPO_ROOT / "content/podcast/.skill/_learning/promoted"

THRESHOLD_BOOKS = 2
THRESHOLD_EPISODES = 3

PROPOSER_VERSION = "1.0"

# Routing: check_id → suggested target rule file. Used to pre-fill the
# "Target file(s)" section of a proposal. Authors override as needed.
CHECK_ID_TO_TARGET = {
    "TX-MODERNIZE": "content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md (R-NOMODERNIZE) + scripts/podcast/_rules.py (MODERNIZE_DENY)",
    "TX-SURPRISE": "content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md (R-NOSURPRISE) + scripts/podcast/_rules.py (SURPRISE_DENY)",
    "TX-WELCOME-COLD": "content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md (R-WELCOME) + scripts/podcast/_rules.py (WELCOME_COLD)",
    "TX-MANGLE": "content/podcast/.skill/handbook/_mangle-map.md (or per-book mangle-map.md)",
    "TX-PHON-DOUBLE": "content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md (R-PHONETICS-OUT)",
    "TX-HONORIFIC-REPEAT": "content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md (R-HONORIFIC-ONCE)",
    "TX-ABBREV": "scripts/podcast/_rules.py (ABBREVIATIONS_MAP)",
    "TX-FILLER": "scripts/podcast/_rules.py (FILLER_INTERJECTIONS)",
}


def load_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return out


def signature_to_slug(sig: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", sig).strip("-").lower()
    return s[:80] if len(s) > 80 else s


def is_already_promoted(slug: str, promoted_dir: Path) -> Path | None:
    """If a promoted/ file ending in -<slug>.md exists, return its path."""
    if not promoted_dir.exists():
        return None
    for p in promoted_dir.glob(f"*-{slug}.md"):
        return p
    return None


def render_proposal(
    sig: str,
    records: list[dict[str, Any]],
    check_id: str,
    severity: str,
) -> str:
    books = sorted({r.get("book", "") for r in records if r.get("book")})
    episodes = sorted({r.get("episode", "") for r in records if r.get("episode")})
    ts_values = sorted([r.get("ts", "") for r in records if r.get("ts")])
    first_seen = ts_values[0] if ts_values else "?"
    last_seen = ts_values[-1] if ts_values else "?"

    sample_excerpts = []
    seen_excerpts: set[str] = set()
    for r in records:
        ex = r.get("context_excerpt", "").strip()
        if ex and ex not in seen_excerpts and len(sample_excerpts) < 5:
            sample_excerpts.append(ex)
            seen_excerpts.add(ex)

    target = CHECK_ID_TO_TARGET.get(check_id, "(determine target normative file)")

    lines = [
        f"# Rule Promotion Proposal — `{sig}`",
        "",
        f"**Trigger.** Signature `{sig}` recurs across {len(books)} book(s) "
        f"and {len(episodes)} episode(s); {len(records)} total ledger records.",
        f"**Occurrences.** {len(records)} records.",
        f"**Distinct books.** {len(books)} — {', '.join(books) if books else '(none)'}",
        f"**Distinct episodes.** {len(episodes)} — {', '.join(episodes) if episodes else '(none)'}",
        f"**First seen.** {first_seen}",
        f"**Last seen.** {last_seen}",
        f"**Severity carried.** {severity}",
        f"**Check id.** `{check_id}`",
        f"**Producer:** `scripts/podcast/learn_propose.py` v{PROPOSER_VERSION}",
        "",
        "## Sample excerpts",
        "",
    ]
    for ex in sample_excerpts:
        lines.append(f"- `{ex}`")
    if not sample_excerpts:
        lines.append("_(no context excerpts in ledger records)_")
    lines += [
        "",
        "## Candidate rule",
        "",
        f"_Author drafts the rule text here. Suggested shape: add the offending phrase / "
        f"pattern to the canonical list named in 'Target file(s)' so future runs of the "
        f"challenger or audit catch it deterministically. If `{check_id}` is empirical-only "
        f"(transcript-level), consider whether a framing-side directive can prevent it at "
        f"generation time._",
        "",
        "## Target file(s)",
        "",
        f"- {target}",
        "",
        "## Fixture",
        "",
        f"Add to `_learning/fixtures/{check_id}/`:",
        "- `input.txt` — minimal artifact exhibiting the failure (e.g., a 3-sentence "
        "framing snippet that contains the phrase)",
        "- `expected.json` — challenger findings the new rule should emit when run "
        "against `input.txt`",
        "",
        "## Acceptance",
        "",
        "- `scripts/podcast/test_challenger.py` exits 0 after the rule lands.",
        "- `_learning/findings.jsonl` shows the signature **stops appearing** (or appears "
        "only as `resolution: auto-fixed`) in subsequent runs.",
        "- `content/podcast/.skill/ROADMAP.md` Section A gains an entry referencing this "
        "proposal with the merging commit hash.",
        "",
        "## Verdict (human)",
        "",
        "- [ ] **Accept** — promote rule to the normative file named in Target, move this "
        "file to `_learning/promoted/` with the merging commit hash appended below.",
        "- [ ] **Reject** — move this file to `_learning/archive/` with a `Rejected because…` "
        "line appended below.",
        "- [ ] **Defer** — leave in place; revisit after N more episodes.",
        "",
        "## Decision log",
        "",
        "_(append commit hash + one-line rationale when promoted/rejected)_",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    p.add_argument("--proposals-dir", type=Path, default=DEFAULT_PROPOSALS_DIR)
    p.add_argument("--promoted-dir", type=Path, default=DEFAULT_PROMOTED_DIR)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    records = load_ledger(args.ledger)
    if not records:
        print("No records in ledger; nothing to propose.")
        return 0

    by_sig: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        sig = r.get("signature", "")
        if sig:
            by_sig[sig].append(r)

    args.proposals_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    written: list[Path] = []
    skipped_promoted: list[str] = []
    skipped_below_threshold: list[str] = []

    for sig, recs in sorted(by_sig.items()):
        books = {r.get("book", "") for r in recs if r.get("book")}
        episodes = {r.get("episode", "") for r in recs if r.get("episode")}
        if not (len(books) >= THRESHOLD_BOOKS or len(episodes) >= THRESHOLD_EPISODES):
            skipped_below_threshold.append(sig)
            continue

        slug = signature_to_slug(sig)
        already = is_already_promoted(slug, args.promoted_dir)
        if already:
            skipped_promoted.append(sig)
            continue

        check_id = recs[0].get("check_id", "")
        severity = recs[0].get("severity", "")
        body = render_proposal(sig, recs, check_id, severity)

        out_path = args.proposals_dir / f"{today}-{slug}.md"

        if args.dry_run:
            print(f"[dry-run] would write: {out_path.relative_to(REPO_ROOT) if REPO_ROOT in out_path.parents else out_path}")
            continue

        if out_path.exists() and out_path.read_text(encoding="utf-8") == body:
            continue

        out_path.write_text(body, encoding="utf-8")
        written.append(out_path)

    print(f"Proposer summary:")
    print(f"  records read:         {len(records)}")
    print(f"  signatures grouped:   {len(by_sig)}")
    print(f"  proposals written:    {len(written)}")
    print(f"  skipped (already promoted): {len(skipped_promoted)}")
    print(f"  skipped (below threshold):  {len(skipped_below_threshold)}")
    for p in written:
        print(f"  → {p.relative_to(REPO_ROOT) if REPO_ROOT in p.parents else p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
