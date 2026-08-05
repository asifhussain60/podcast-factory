#!/usr/bin/env python3
"""Partition the synthesized al-anwaar-al-lateefah 0c book into a 6-volume work.

Book-specific scaffolder for Islamic/al-anwaar-al-lateefah ONLY. Mirrors the
asaas-al-taveel split precedent (split_transcript_asaas.py) but targets the
CURRENT nested work model (work.yml + vol-NN/, per _paths/_work_manifest) rather
than the legacy top-level "<slug>-vol-N" dirs. Do NOT merge to develop as a
general tool — the section->volume boundaries are specific to this title
(COLLECTION-PLAN.md section 5, split design APPROVED 2026-06-17).

What it does (no re-synthesis):
  * Reads the already-synthesized _system/unified-book.md — 28 H2 sections, the
    0b-refined artifact — and partitions it into vol-NN/_system/source/text/
    refined-english.md (the Phase-0c prerequisite), each volume holding EXACTLY
    its approved sections.
  * The root _system/ (unified book + unified ledger + arabic fingerprints) stays
    in place as the work's SHARED source of truth; work.yml records it.
  * Each volume gets the standard book skeleton, a 0c/pending orchestrator-state
    (0a/0b pre-marked "sliced from synthesis"), and shares the one work branch.

Self-verifying: every H2 section lands in exactly one volume; per-volume word and
Arabic-script-character sums reconcile to the source. Teaching-level assignment
(_volume-split.json, no-loss/no-repeat) is a per-volume 0d concern, NOT done here.

Dry-run by default. Pass --execute to write.

Usage:
    .venv/bin/python scripts/podcast/split_synthesis_al_anwaar.py            # dry-run
    .venv/bin/python scripts/podcast/split_synthesis_al_anwaar.py --execute
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import ensure_book_skeleton

WORK_SLUG = "al-anwaar-al-lateefah"
WORK_DIR = REPO_ROOT / "content" / "Islamic" / WORK_SLUG
UNIFIED_BOOK = WORK_DIR / "_system" / "unified-book.md"
WORK_BRANCH = f"Islamic/{WORK_SLUG}"
WORK_TITLE = "Al-Anwaar al-Lateefah"

# Volume -> (title, inclusive 1-based H2 section range). Partition of all 28.
VOLUMES: dict[int, dict] = {
    1: {"title": "The Oneness (Tawheed)", "sections": (1, 2)},
    2: {"title": "The Origin (Mabda')", "sections": (3, 9)},
    3: {"title": "The Hidden Hierarchy", "sections": (10, 14)},
    4: {"title": "The Sacred Line", "sections": (15, 18)},
    5: {"title": "The Two Paths and the Resurrection", "sections": (19, 23)},
    6: {"title": "Retribution and the Dawn", "sections": (24, 28)},
}

_ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")


def _parse_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Split unified-book.md into (preamble, [(header, body), ...]) by H2.

    Preamble = everything before the first '## '. Each section's body is the
    verbatim text from its '## ' header up to (excluding) the next '## '.
    """
    lines = text.split("\n")
    head_idx = [i for i, l in enumerate(lines) if l.startswith("## ")]
    if not head_idx:
        raise SystemExit("no H2 sections found in unified-book.md")
    preamble = "\n".join(lines[: head_idx[0]]).rstrip() + "\n"
    bounds = head_idx + [len(lines)]
    sections: list[tuple[str, str]] = []
    for k in range(len(head_idx)):
        block = lines[bounds[k] : bounds[k + 1]]
        header = block[0][3:].strip()
        body = "\n".join(block).rstrip() + "\n"
        sections.append((header, body))
    return preamble, sections


def _volume_refined_text(vol: int, sections: list[tuple[str, str]]) -> str:
    """Assemble a standalone volume's refined-english.md from its sections."""
    lo, hi = VOLUMES[vol]["sections"]
    title = VOLUMES[vol]["title"]
    note = (
        "*Volume {n} of the Al-Anwaar Collection — an enhanced reading edition "
        "prepared from the recorded lessons of the master. Arabic and Qur'anic "
        "quotations are reproduced as transmitted; ordinary terms are given in "
        "plain transliteration for reading.*"
    ).format(n=vol)
    parts = [f"# Al-Anwaar al-Lateefah, Volume {vol} — {title}", "", note, "", "---", ""]
    parts += [sections[i - 1][1] for i in range(lo, hi + 1)]
    return "\n".join(parts).rstrip() + "\n"


def _volume_state(vol: int) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pre = lambda note: {"status": "completed", "note": note}
    return {
        "schema_version": 1,
        "book_slug": f"{WORK_SLUG}-vol-{vol:02d}",
        "work_slug": WORK_SLUG,
        "volume": vol,
        "category": "books",
        "content_profile": "islamic_scholarly",
        "branch": WORK_BRANCH,
        "phase": "0c",
        "phase_status": "pending",
        "last_completed_phase": "0b",
        "next_phase": "0c",
        "last_error": None,
        "phases": {
            "pre-flight": pre("pre-marked: volume scaffold"),
            "branch": pre(f"pre-marked: shares {WORK_BRANCH} branch"),
            "scaffold": pre("pre-marked: carved from synthesized unified-book.md"),
            "0a": pre("pre-marked: multi-source synthesis on work root; sliced"),
            "0b": pre("pre-marked: refinement on synthesized book; sliced"),
            "0c": {"status": "pending"},
            "0d": {"status": "pending"},
            "0e": {"status": "pending"},
            "0f": {"status": "pending"},
            "0g": {"status": "pending"},
            "per-chapter": {"status": "pending"},
            "trainer": {"status": "pending"},
            "merge": {"status": "pending"},
            "done": {"status": "pending"},
        },
        "cost": {"azure_usd": 0.0, "anthropic_usd": 0.0},
        "wall_clock_sec": 0,
        "config": {"length_tier": "extended", "unit_mode": "auto"},
        "pipeline_mode": "orchestrated",
        "status": "draft",
        "ts_started": now,
        "ts_updated": now,
    }


def _manifest(sections: list[tuple[str, str]]) -> dict:
    vols = []
    for v in sorted(VOLUMES):
        lo, hi = VOLUMES[v]["sections"]
        vols.append(
            {
                "order": v,
                "slug": f"{WORK_SLUG}-vol-{v:02d}",
                "dir": f"vol-{v:02d}",
                "title": VOLUMES[v]["title"],
                "h2_sections": list(range(lo, hi + 1)),
                "refined_source": f"vol-{v:02d}/_system/source/text/refined-english.md",
                "status": "draft",
            }
        )
    return {
        "work_slug": WORK_SLUG,
        "title": WORK_TITLE,
        "content_profile": "islamic_scholarly",
        "bucket": "Islamic",
        "collection": "Al-Anwaar Collection",
        "shared": {
            "synthesis": "_system/unified-book.md",
            "ledger": "_system/source/text/_teaching-ledger.json",
            "arabic_fingerprints": "_system/arabic-fingerprints.json",
            "knowledge": "_system",
        },
        "note": (
            "Partitioned from the synthesized 0c book by "
            "scripts/podcast/split_synthesis_al_anwaar.py (no re-synthesis). "
            "Volumes start at 0c; teaching-level _volume-split.json is a per-volume "
            "0d artifact. Boundaries: COLLECTION-PLAN.md section 5 (APPROVED 2026-06-17)."
        ),
        "volumes": vols,
    }


def _emit_yaml(manifest: dict) -> str:
    """Minimal manifest YAML (avoids a PyYAML dump dependency; matches asaas shape)."""
    import yaml  # available in .venv

    return yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=100)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true", help="write files (default: dry-run)")
    args = ap.parse_args()

    if not UNIFIED_BOOK.exists():
        raise SystemExit(f"missing synthesized book: {UNIFIED_BOOK}")
    text = UNIFIED_BOOK.read_text()
    preamble, sections = _parse_sections(text)
    if len(sections) != 28:
        raise SystemExit(f"expected 28 H2 sections, found {len(sections)}")

    # Partition integrity: every section assigned exactly once.
    assigned: list[int] = []
    for v in sorted(VOLUMES):
        lo, hi = VOLUMES[v]["sections"]
        assigned += list(range(lo, hi + 1))
    if sorted(assigned) != list(range(1, 29)) or len(assigned) != len(set(assigned)):
        raise SystemExit(f"section->volume map is not a clean partition of 1..28: {assigned}")

    src_words = sum(len(b.split()) for _, b in sections)
    src_arabic = sum(len(_ARABIC_RE.findall(b)) for _, b in sections)

    print(f"{'mode':<10}{'EXECUTE' if args.execute else 'DRY-RUN'}")
    print(
        f"source: {UNIFIED_BOOK.relative_to(REPO_ROOT)}  ({len(sections)} sections, "
        f"{src_words} words, {src_arabic} Arabic chars)\n"
    )
    print(f"{'Vol':<4}{'dir':<9}{'sections':<12}{'words':>8}{'arabic':>9}  title")
    tot_w = tot_a = 0
    vol_texts: dict[int, str] = {}
    for v in sorted(VOLUMES):
        lo, hi = VOLUMES[v]["sections"]
        vtext = _volume_refined_text(v, sections)
        vol_texts[v] = vtext
        # measure ONLY the section bodies (exclude the per-volume front matter we add)
        body_w = sum(len(sections[i - 1][1].split()) for i in range(lo, hi + 1))
        body_a = sum(len(_ARABIC_RE.findall(sections[i - 1][1])) for i in range(lo, hi + 1))
        tot_w += body_w
        tot_a += body_a
        print(f"{v:<4}vol-{v:02d}   {f'{lo}-{hi}':<12}{body_w:>8}{body_a:>9}  {VOLUMES[v]['title']}")
    print(f"{'':<25}{tot_w:>8}{tot_a:>9}  TOTAL")

    ok_w = tot_w == src_words
    ok_a = tot_a == src_arabic
    print(f"\nno-loss words : {'OK' if ok_w else 'MISMATCH'} ({tot_w} vs {src_words})")
    print(f"no-loss arabic: {'OK' if ok_a else 'MISMATCH'} ({tot_a} vs {src_arabic})")
    if not (ok_w and ok_a):
        raise SystemExit("partition is lossy — refusing to proceed")

    manifest = _manifest(sections)
    if not args.execute:
        print("\n--- work.yml (preview) ---")
        print(_emit_yaml(manifest))
        print("(dry-run — no files written. Re-run with --execute on the work branch.)")
        return 0

    # WRITE
    (WORK_DIR / "work.yml").write_text(_emit_yaml(manifest))
    print(f"\nwrote {WORK_DIR.relative_to(REPO_ROOT)}/work.yml")
    for v in sorted(VOLUMES):
        vdir = WORK_DIR / f"vol-{v:02d}"
        ensure_book_skeleton(vdir)
        (vdir / "_system" / "source" / "text" / "refined-english.md").write_text(vol_texts[v])
        (vdir / "_system" / "orchestrator-state.json").write_text(json.dumps(_volume_state(v), indent=2) + "\n")
        print(f"  vol-{v:02d}: skeleton + refined-english.md + state(0c/pending)")
    print("\nDONE. Next: launch per-volume 0c via orchestrate_work.py (Tier 2 — ask first).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
