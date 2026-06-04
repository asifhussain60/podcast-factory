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
from _paths import REPO_ROOT
from typing import Any

DEFAULT_LEDGER = REPO_ROOT / "content/podcast/.skill/_learning/findings.jsonl"
DEFAULT_PROPOSALS_DIR = REPO_ROOT / "content/podcast/.skill/_learning/proposals"
DEFAULT_PROMOTED_DIR = REPO_ROOT / "content/podcast/.skill/_learning/promoted"
DEFAULT_ARCHIVE_DIR = REPO_ROOT / "content/podcast/.skill/_learning/archive"

THRESHOLD_BOOKS = 2
THRESHOLD_EPISODES = 3

# In-book-density threshold (v1.1, 2026-05-18). When the same `check_id` fires
# ≥ this many times in a single (book, episode), emit one *consolidated*
# proposal grouped by check_id. This catches the strongest learning signal in
# an early-stage repo (one or two books in flight) where signatures are
# distinct but the *kind* of finding is recurring — e.g., N3 firing 6× in one
# framing or J2 firing 3× in one chapter.
THRESHOLD_DENSITY = 3

PROPOSER_VERSION = "1.3"  # 2026-05-18: skip when ALL records are auto-fixed (post-promotion noise suppression)

# Routing: check_id → suggested target rule file. Used to pre-fill the
# "Target file(s)" section of a proposal. Authors override as needed.
# Covers (a) TX-* empirical-transcript checks (audit_transcript.py) and
# (b) Loop A-R catalog check IDs from .github/agents/podcast-challenger.agent.md.
# Path constants for proposal target-file hints. The earlier handbook tree at
# content/podcast/.skill/handbook/ was retired 2026-05-23; the rules previously
# carried there now live in the in-code authority below. These constants point
# at the current canonical homes so proposers see paths that actually exist.
SOURCE_RULES = "infra/claude-agents/podcast-challenger.md (chapter-source check Categories) + scripts/podcast/_rules.py"
CUSTOMIZE_RULES = "infra/claude-agents/podcast-challenger.md (customize-prompt check Categories) + scripts/podcast/_rules.py"
ENRICHMENT = "scripts/podcast/_authoring.py Phase 0e prompt + infra/claude-agents/podcast-challenger.md Category D"
SHARED_ARABIC = "content/_shared/arabic/"   # still exists; canonical pronunciation reference
CONTRACT_TPL = "scripts/podcast/extract_chapter.py (stub_contract + validate_contract — the in-code schema)"
DEBATE = "infra/claude-agents/podcast-challenger.md Category P + scripts/podcast/_blueprint_schema.py (DebateBlock)"
RULES_PY = "scripts/podcast/_rules.py"
BUILD_PY = "scripts/podcast/build_episode_txt.py"

CHECK_ID_TO_TARGET = {
    # ── Transcript-empirical (audit_transcript.py + _rules.py lists) ──────
    "TX-MODERNIZE": f"{CUSTOMIZE_RULES} (R-NOMODERNIZE) + {RULES_PY} (MODERNIZE_DENY)",
    "TX-SURPRISE": f"{CUSTOMIZE_RULES} (R-NOSURPRISE) + {RULES_PY} (SURPRISE_DENY)",
    "TX-WELCOME-COLD": f"{CUSTOMIZE_RULES} (R-WELCOME) + {RULES_PY} (WELCOME_COLD)",
    "TX-MANGLE": "BOOK_DIR/_system/mangle-map.md (per-book; the cross-book generic mangle-map.md was retired 2026-05-23 and load_generic_mangle_map() returns {} when missing)",
    "TX-PHON-DOUBLE": f"{CUSTOMIZE_RULES} (R-PHONETICS-OUT)",
    "TX-HONORIFIC-REPEAT": f"{SOURCE_RULES} (R-HONORIFIC-ONCE) + {RULES_PY} (HONORIFICS)",
    "TX-ABBREV": f"{RULES_PY} (ABBREVIATIONS_MAP)",
    "TX-FILLER": f"{RULES_PY} (FILLER_INTERJECTIONS) + {CUSTOMIZE_RULES} (R-NOINTERRUPT)",
    # ── Category A: Authenticity ─────────────────────────────────────────
    "A1": f"{ENRICHMENT} §2 (citation format)",
    "A2": f"{ENRICHMENT} §2 (citation authenticity) + author resolves",
    "A3": f"{ENRICHMENT} §2 (translation provenance) + author resolves",
    "A4": f"{ENRICHMENT} §2 (verbatim quote integrity) + author resolves",
    "A5": "author resolution — semantic source-shifting requires human judgment",
    "A6": "author resolution — cross-tradition annotation requires human judgment",
    # ── Category B: NotebookLM literalness ──────────────────────────────
    "B1": f"{BUILD_PY} (META_PROSE_TELLS + META_PROSE_REGEX_TELLS)",
    "B2": f"{BUILD_PY} (cross-episode regex) — auto-fix",
    "B3": "author resolution — file-length self-reference needs rewrite",
    "B4": "author resolution — translator-apparatus prefix needs rewrite",
    "B5": f"{BUILD_PY} (em-dash auto-fix)",
    "B6": "author resolution — invented dialogue requires human verification",
    # ── Category C: Pronunciation discipline ─────────────────────────────
    "C1": f"{SHARED_ARABIC}03-arabic-english-manifest.md + BOOK_DIR/_system/source/text/_phonetics.md",
    "C2": f"{SHARED_ARABIC}03-arabic-english-manifest.md (manifest wins)",
    "C3": f"{SOURCE_RULES} (R-HONORIFIC-ONCE) + {RULES_PY} (HONORIFICS)",
    "C4": f"{SHARED_ARABIC}04-common-term-substitutions.md §2",
    # ── Category D: Enrichment & depth ──────────────────────────────────
    "D1": f"{ENRICHMENT} (tier diversity) — author decision",
    "D2": f"{ENRICHMENT} (enrichment ratio) — author decision",
    "D3": "author resolution — tradition coherence requires human judgment",
    "D4": "author resolution — quote-stacking needs prose bridges",
    "D5": f"{BUILD_PY} (CONTEXT-NEEDED marker hard-fail)",
    # ── Category E: Articulation & shape ────────────────────────────────
    "E1": f"{BUILD_PY} (FRAMING_WORD_MIN/MAX; CHAPTER_WORD_MIN/MAX_HARD) + {CUSTOMIZE_RULES} length-target gating",
    "E2": "author resolution — one-sentence summarizability",
    "E3": "author resolution — beginning/middle/end arc",
    "E4": f"{RULES_PY} (FILLER_INTERJECTIONS) + {CUSTOMIZE_RULES} (R-NOINTERRUPT)",
    "E5": "author resolution — translation-residue rewrite",
    # ── Category F: Framing integrity ───────────────────────────────────
    "F1": f"{BUILD_PY} (framing file presence)",
    "F2": f"{CUSTOMIZE_RULES} (4-part structure)",
    "F3": "author resolution — audience profile",
    "F4": "author resolution — central tensions naming",
    "F5": "author resolution — discussion-spine beat count",
    "F6": "infra/claude-agents/podcast-challenger.md Category F (steering phrases — formerly two-host-framing.md, retired 2026-05-23)",
    # ── Category G: Extract Mode contracts ──────────────────────────────
    "G1": f"{CONTRACT_TPL} + scripts/podcast/extract_chapter.py",
    "G2": f"{CONTRACT_TPL} + scripts/podcast/extract_chapter.py",
    "G3": f"scripts/podcast/extract_chapter.py (CONTRACT_META_PROSE_TELLS)",
    "G4": f"{CONTRACT_TPL} (derived_from)",
    "G5": "scripts/podcast/extract_chapter.py (Splitting Policy — formerly extract-capability.md, retired 2026-05-23)",
    "G6": "scripts/podcast/check_lineage.py",
    # ── Category H: Welcome opening + closing landing ───────────────────
    "H1": f"{CUSTOMIZE_RULES} (R-WELCOME)",
    "H2": f"{CUSTOMIZE_RULES} (R-WELCOME, summary clause)",
    "H3": f"{CUSTOMIZE_RULES} (R-SUMMARYTAIL)",
    # ── Category I: Anti-repetition + no-irrelevant-background ──────────
    "I1": f"{CUSTOMIZE_RULES} (R-NOREPEAT)",
    "I2": f"{CUSTOMIZE_RULES} (R-NOBACKGROUND)",
    "I3": "author resolution — chapter movement structure",
    "I4": "author resolution — chapter background bound",
    # ── Category J: Name aliasing ───────────────────────────────────────
    "J1": f"{CUSTOMIZE_RULES} (R-NAMEALIAS) + {SHARED_ARABIC}05-name-alias-policy.md",
    "J2": f"{SOURCE_RULES} (R-NAMES) + {SHARED_ARABIC}05-name-alias-policy.md",
    "J3": f"{SHARED_ARABIC}03-arabic-english-manifest.md (manifest wins)",
    # ── Category K: Interruption avoidance + host dynamic ───────────────
    "K1": f"{CUSTOMIZE_RULES} (R-NOINTERRUPT)",
    "K2": f"{CUSTOMIZE_RULES} (R-NOINTERRUPT, filler vocab)",
    # ── Category M: Modernization + surprise-noise empirical ────────────
    "M1": f"{CUSTOMIZE_RULES} (R-NOMODERNIZE)",
    "M2": f"{CUSTOMIZE_RULES} (R-NOSURPRISE)",
    "M3": f"{CUSTOMIZE_RULES} (R-NOMODERNIZE) + {RULES_PY} (MODERNIZE_DENY)",
    "M4": f"{CUSTOMIZE_RULES} (R-NOSURPRISE) + {RULES_PY} (SURPRISE_DENY)",
    # ── Category N: Phonetic-as-content audit ───────────────────────────
    "N1": f"{SOURCE_RULES} (R-PHONETICS-OUT) + {BUILD_PY} (INLINE_PHONETIC_PATTERNS)",
    "N2": f"{CUSTOMIZE_RULES} (R-PRONUNCIATION-IMPERATIVE) + {BUILD_PY} (LEGACY_PASSIVE_PRONUNCIATION)",
    "N3": f"{CUSTOMIZE_RULES} (R-PRONUNCIATION-IMPERATIVE) + BOOK_DIR/_system/source/text/_phonetics.md",
    "N4": f"{CUSTOMIZE_RULES} (R-NO-READ-PROMPT)",
    "N5": f"{CUSTOMIZE_RULES} (R-PHONETICS-OUT) + {RULES_PY} (NAME_MANGLING_MAP via _mangle-map.md)",
    # ── Category O: Honorific + abbreviation audit ──────────────────────
    "O1": f"{SOURCE_RULES} (R-HONORIFIC-ONCE) + {RULES_PY} (HONORIFICS)",
    "O2": f"{SOURCE_RULES} (R-NO-ABBREVIATION) + {RULES_PY} (ABBREVIATIONS_MAP)",
    "O3": f"{RULES_PY} (HONORIFICS) — empirical transcript flag-only",
    # ── Category P: Debate-format integrity ─────────────────────────────
    "P1": f"{CONTRACT_TPL} (debate block schema)",
    "P2": f"{CONTRACT_TPL} (debate.resolution enum)",
    "P3": f"{DEBATE} §Vocabulary",
    "P4": f"{DEBATE} §Vocabulary",
    "P5": f"{DEBATE} §Source moves",
    "P6": f"{DEBATE} §Rules of debate",
    "P7": f"{DEBATE} §NotebookLM steering",
    "P8": f"{DEBATE} §Resolution",
    "P9": f"{DEBATE} §Resolution",
    "P10": f"{DEBATE} §NotebookLM steering",
    "P11": f"{DEBATE} §Conversation discipline",
    "P12": f"{DEBATE} (empirical transcript flag-only)",
    "P13": f"{DEBATE} (empirical transcript flag-only)",
    # ── Category Q: Chapter-set design ──────────────────────────────────
    "Q1": "scripts/podcast/check_chapter_set.py + author renames",
    "Q2": "scripts/podcast/check_chapter_set.py + author tightens title",
    "Q3": "scripts/podcast/check_chapter_set.py + author titles",
    "Q4": f"{CONTRACT_TPL} (length_target) + author rebalances",
    "Q5": "scripts/podcast/check_chapter_set.py + author resegments",
    "Q6": "BOOK_DIR/_system/mangle-map.md + author verifies",
    # ── Category R: Conversation choreography ───────────────────────────
    "R1": f"{CUSTOMIZE_RULES} (R-SURPRISE-MOVE)",
    "R2": f"{CUSTOMIZE_RULES} (R-RESET)",
    "R3": f"{CUSTOMIZE_RULES} (R-CADENCE)",
    "R4": f"{CUSTOMIZE_RULES} (R-NOFORMAL)",
    "R5": f"{CUSTOMIZE_RULES} (R-NOMODERNIZE — analogy permission half)",
    "R6": f"{CUSTOMIZE_RULES} (R-NOFORMAL) — empirical transcript flag-only",
    "R7": f"{CUSTOMIZE_RULES} (R-NOMODERNIZE) — empirical transcript flag-only",
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


def is_already_resolved(slug: str, *dirs: Path) -> Path | None:
    """If a file ending in -<slug>.md exists in any of `dirs`, return its path.
    Used to skip signatures already moved to `promoted/` or `archive/` — the
    human has already decided about them, and re-creating the proposal would
    just churn the directory."""
    for d in dirs:
        if not d.exists():
            continue
        for p in d.glob(f"*-{slug}.md"):
            return p
    return None


# Legacy alias kept for back-compat with the v1.0 call site below.
is_already_promoted = is_already_resolved


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
    p.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    records = load_ledger(args.ledger)
    if not records:
        print("No records in ledger; nothing to propose.")
        return 0

    by_sig: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_check_in_episode: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        sig = r.get("signature", "")
        if sig:
            by_sig[sig].append(r)
        check = r.get("check_id", "")
        book = r.get("book", "")
        ep = r.get("episode", "")
        if check and book:
            by_check_in_episode[(check, book, ep)].append(r)

    args.proposals_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    written: list[Path] = []
    skipped_resolved: list[str] = []
    skipped_below_threshold: list[str] = []

    skipped_all_autofixed: list[str] = []

    # ── Pass 1: cross-book / cross-episode signature recurrence ─────────────
    for sig, recs in sorted(by_sig.items()):
        # Skip when EVERY record for this signature carries resolution=auto-fixed.
        # The rule has already absorbed the pattern; further proposals are noise.
        if recs and all(r.get("resolution") == "auto-fixed" for r in recs):
            skipped_all_autofixed.append(sig)
            continue

        books = {r.get("book", "") for r in recs if r.get("book")}
        episodes = {r.get("episode", "") for r in recs if r.get("episode")}
        if not (len(books) >= THRESHOLD_BOOKS or len(episodes) >= THRESHOLD_EPISODES):
            skipped_below_threshold.append(sig)
            continue

        slug = signature_to_slug(sig)
        already = is_already_resolved(slug, args.promoted_dir, args.archive_dir)
        if already:
            skipped_resolved.append(sig)
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

    # ── Pass 2: in-book density (≥ THRESHOLD_DENSITY records of same check_id
    #    in same (book, episode)). Emits one *consolidated* proposal per
    #    (check_id, book, episode) tuple. Signal: "this check fires repeatedly
    #    against one artifact — the check itself probably needs sharper auto-fix
    #    or a tighter precondition." ──────────────────────────────────────
    density_written: list[Path] = []
    for (check_id, book, ep), recs in sorted(by_check_in_episode.items()):
        # Count only still-flagged firings against the density threshold.
        # Auto-fixed firings prove the rule absorbed the pattern; they should
        # not keep re-firing the proposal once the fix lands.
        flagged_recs = [r for r in recs if r.get("resolution") != "auto-fixed"]
        if len(flagged_recs) < THRESHOLD_DENSITY:
            if recs and not flagged_recs:
                skipped_all_autofixed.append(f"{check_id}:density:{book}:{ep}")
            continue
        consolidated_sig = f"{check_id}:density:{book}:{ep}"
        slug = signature_to_slug(consolidated_sig)
        already = is_already_resolved(slug, args.promoted_dir, args.archive_dir)
        if already:
            skipped_resolved.append(consolidated_sig)
            continue
        severity = recs[0].get("severity", "")
        body = render_proposal(consolidated_sig, recs, check_id, severity)
        # Tag the body as a density proposal so the human reviewer knows the
        # trigger was in-book density, not cross-book recurrence.
        body = body.replace(
            "**Trigger.**",
            f"**Trigger (density).** {len(recs)}× firings of `{check_id}` within `{book}/{ep}` — in-book density ≥ {THRESHOLD_DENSITY}.\n\n**Trigger.**",
            1,
        )
        out_path = args.proposals_dir / f"{today}-{slug}.md"
        if args.dry_run:
            print(f"[dry-run] would write (density): {out_path.relative_to(REPO_ROOT) if REPO_ROOT in out_path.parents else out_path}")
            continue
        if out_path.exists() and out_path.read_text(encoding="utf-8") == body:
            continue
        out_path.write_text(body, encoding="utf-8")
        density_written.append(out_path)

    print(f"Proposer summary:")
    print(f"  records read:               {len(records)}")
    print(f"  signatures grouped:         {len(by_sig)}")
    print(f"  proposals written (recur):  {len(written)}")
    print(f"  proposals written (density):{len(density_written)}")
    print(f"  skipped (already resolved): {len(skipped_resolved)}")
    print(f"  skipped (all auto-fixed):   {len(skipped_all_autofixed)}")
    print(f"  skipped (below threshold):  {len(skipped_below_threshold)}")
    for p in written + density_written:
        print(f"  → {p.relative_to(REPO_ROOT) if REPO_ROOT in p.parents else p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
