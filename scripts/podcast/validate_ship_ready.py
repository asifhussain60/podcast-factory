#!/usr/bin/env python3
"""validate_ship_ready.py — run G1-G7 quality gates WITHOUT publishing.

PURPOSE

The orchestrator's `finalize` phase (added 2026-05-24) needs to verify
"is this book production-ready?" without performing the actual file-copy
to `content/published/books/<slug>/`. This script imports the gate
functions from `publish_to_library.py` and runs them read-only.

If all gates pass, the orchestrator halts at finalize so Asif can review
the clean version in the podcast-reader app + optionally run A/B
transcription analysis. The actual publish (the file copy) is a
separate human-authorized action.

If any gate fails, this script exits non-zero with the failing gate's
reason — the orchestrator halts-and-surfaces for remediation.

USAGE

    python3 scripts/podcast/validate_ship_ready.py <slug>
    python3 scripts/podcast/validate_ship_ready.py <slug> --allow-mode-2
    python3 scripts/podcast/validate_ship_ready.py <slug> --strict --json

EXIT CODES

    0  — all G1-G7 gates passed; book is ship-ready
    1  — one or more gates failed; book is NOT ship-ready
    2  — couldn't run (book dir missing, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("slug", help="book slug under content/drafts/")
    ap.add_argument("--strict", action="store_true",
                    help="treat P1 advisories as gate-fails")
    ap.add_argument("--allow-mode-2", action="store_true",
                    help="permit non_orchestrated_mode_2 / pre_orchestrator_authored books")
    ap.add_argument("--no-wipe", action="store_true",
                    help="permit coexisting with prior content at target (G6 carve-out)")
    ap.add_argument("--force", action="store_true",
                    help="skip G5 state checkpoint")
    ap.add_argument("--json", action="store_true",
                    help="emit JSON verdict (for orchestrator consumption)")
    args = ap.parse_args()

    import publish_to_library as P

    workspace = P.WORKSPACE / args.slug
    if not workspace.is_dir():
        msg = f"workspace not found: {workspace}"
        if args.json:
            print(json.dumps({"verdict": "BLOCKED", "reason": msg, "gates": []}))
        else:
            print(f"validate_ship_ready: {msg}", file=sys.stderr)
        return 2
    target = P.LIBRARY / "books" / args.slug

    gate_results: list[dict] = []

    if not args.json:
        print(f"==> validate_ship_ready: {args.slug}")
        print(f"    workspace: {workspace.relative_to(P.REPO_ROOT)}")
        print(f"    target:    {target} (read-only check)")
        print()
        print("=== Gates ===")

    ok1, chapters, episodes = P.gate_g1_structure(workspace)
    gate_results.append({"gate": "G1", "name": "structure", "passed": bool(ok1)})
    if not ok1:
        return _emit(args, gate_results, "BLOCKED", "G1 structure check failed")

    ok2 = P.gate_g2_pairs(chapters, episodes)
    gate_results.append({"gate": "G2", "name": "chapter-episode-pairs", "passed": bool(ok2)})
    if not ok2:
        return _emit(args, gate_results, "BLOCKED", "G2 chapter/episode pair mismatch")

    ok3 = P.gate_g3_sequential(chapters, episodes)
    gate_results.append({"gate": "G3", "name": "sequential-numbering", "passed": bool(ok3)})
    if not ok3:
        return _emit(args, gate_results, "BLOCKED", "G3 sequential-numbering failed")

    ok4 = P.gate_g4_build_clean(workspace, args.slug, episodes, args.strict)
    gate_results.append({"gate": "G4", "name": "build-clean", "passed": bool(ok4)})
    if not ok4:
        return _emit(args, gate_results, "BLOCKED", "G4 build-clean failed")

    ok5 = P.gate_g5_state(workspace, args.force)
    gate_results.append({"gate": "G5", "name": "state-shippable", "passed": bool(ok5)})
    if not ok5:
        return _emit(args, gate_results, "BLOCKED", "G5 state-shippable failed")

    ok6 = P.gate_g6_target(target, args.no_wipe)
    gate_results.append({"gate": "G6", "name": "target-wipe-safe", "passed": bool(ok6)})
    if not ok6:
        return _emit(args, gate_results, "BLOCKED", "G6 target-wipe-safe failed")

    ok7 = P.gate_g7_challenger_convergence(workspace, args.allow_mode_2)
    gate_results.append({"gate": "G7", "name": "challenger-verdict", "passed": bool(ok7)})
    if not ok7:
        return _emit(args, gate_results, "BLOCKED", "G7 challenger-verdict failed")

    return _emit(args, gate_results, "SHIP-READY",
                 f"all 7 gates passed for {args.slug}; ready for publish")


def _emit(args, gate_results: list[dict], verdict: str, summary: str) -> int:
    if args.json:
        print(json.dumps({
            "slug": args.slug,
            "verdict": verdict,
            "summary": summary,
            "gates": gate_results,
            "passed_count": sum(1 for g in gate_results if g["passed"]),
            "total_count": len(gate_results),
        }, indent=2))
    else:
        print()
        if verdict == "SHIP-READY":
            print(f"✓ SHIP-READY — {summary}")
            print()
            print(f"  Next: human review in podcast-reader, then authorize")
            print(f"        `python3 scripts/podcast/publish_to_library.py {args.slug}`")
        else:
            print(f"✗ {verdict} — {summary}")
            print(f"  Remediation: see the failing gate's reason above.")
    return 0 if verdict == "SHIP-READY" else 1


if __name__ == "__main__":
    sys.exit(main())
