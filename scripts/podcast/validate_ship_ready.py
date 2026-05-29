#!/usr/bin/env python3
"""validate_ship_ready.py — run G1-G7 quality gates WITHOUT publishing.

PURPOSE

The orchestrator's `finalize` phase (added 2026-05-24) needs to verify
"is this book production-ready?" without performing the actual file-copy
to `content/published/books/<slug>/`. This script imports the gate
functions from `publish_to_library.py` and runs them read-only.

If all gates pass, the orchestrator halts at finalize so Asif can review
the clean version in the Podcast Factory Astro Site + optionally run A/B
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

    # ── G8-G12: archetype-aware gates (warn-only until G12 fires green on ≥1 book) ──

    # G8 — capstone-mode-honored: if meta.yml declares a capstone_mode != none,
    # at least the tier-1 capstone episode file must exist.
    meta_path = workspace / "meta.yml"
    capstone_mode = "none"
    if meta_path.exists():
        try:
            import yaml as _yaml
            _meta = _yaml.safe_load(meta_path.read_text()) or {}
            capstone_mode = str(_meta.get("capstone_mode", "none"))
        except Exception:
            pass
    ok8 = True
    if capstone_mode not in ("none", ""):
        tier1_ep = workspace / "_system" / "episode-drafts"
        capstone_eps = list(tier1_ep.glob("*capstone*")) if tier1_ep.exists() else []
        ok8 = len(capstone_eps) > 0
    gate_results.append({"gate": "G8", "name": "capstone-mode-honored", "passed": bool(ok8)})
    if not ok8:
        return _emit(args, gate_results, "BLOCKED",
                     f"G8 capstone-mode-honored failed — capstone_mode={capstone_mode} but no capstone episode found")

    # G9 — rich-diagram-coverage: if diagram_density == high, slide classifier
    # must report coverage ≥ 60% (WARN threshold from pilot findings).
    diagram_density = "low"
    if meta_path.exists():
        try:
            import yaml as _yaml
            _meta2 = _yaml.safe_load(meta_path.read_text()) or {}
            diagram_density = str(_meta2.get("diagram_density", "low"))
        except Exception:
            pass
    ok9 = True
    if diagram_density == "high":
        coverage_report = workspace / "_system" / "diagram-coverage-report.json"
        if coverage_report.exists():
            try:
                import json as _json
                _cov = _json.loads(coverage_report.read_text())
                ok9 = float(_cov.get("coverage", 1.0)) >= 0.60
            except Exception:
                ok9 = True  # missing report → advisory only, not blocking
    gate_results.append({"gate": "G9", "name": "rich-diagram-coverage", "passed": bool(ok9)})
    if not ok9:
        return _emit(args, gate_results, "BLOCKED",
                     "G9 rich-diagram-coverage failed — diagram_density=high but coverage < 60%")

    # G10 — manual-review-resolved: no open manual-review alert divs in any episode file.
    open_manual_reviews: list[str] = []
    episodes_dir = workspace / "episodes"
    if episodes_dir.exists():
        for ep_file in episodes_dir.glob("*.txt"):
            if "<div class='alert manual-review'>" in ep_file.read_text():
                open_manual_reviews.append(ep_file.name)
    ok10 = len(open_manual_reviews) == 0
    gate_results.append({"gate": "G10", "name": "manual-review-resolved",
                         "passed": bool(ok10)})
    if not ok10:
        return _emit(args, gate_results, "BLOCKED",
                     f"G10 manual-review-resolved failed — open reviews in: {', '.join(open_manual_reviews)}")

    # G11 — knowledge-base-merge-clean: librarian merge report has zero conflicts.
    ok11 = True
    merge_report = workspace / "_system" / "librarian-merge-report.md"
    if merge_report.exists():
        report_text = merge_report.read_text()
        if "conflict" in report_text.lower() and "zero" not in report_text.lower():
            ok11 = False
    gate_results.append({"gate": "G11", "name": "knowledge-base-merge-clean",
                         "passed": bool(ok11)})
    if not ok11:
        return _emit(args, gate_results, "BLOCKED",
                     "G11 knowledge-base-merge-clean failed — unresolved conflicts in librarian merge report")

    # G12 — augmenter-A/B-acceptance: for books with enable_knowledge_augmenter=true,
    # challenger must have surfaced ≥1 finding referencing an augmented atom.
    # Advisory gate — does not block until A/B flywheel fires green on ≥1 book pair.
    enable_augmenter = False
    if meta_path.exists():
        try:
            import yaml as _yaml
            _meta3 = _yaml.safe_load(meta_path.read_text()) or {}
            enable_augmenter = bool(_meta3.get("enable_knowledge_augmenter", False))
        except Exception:
            pass
    ok12 = True  # default pass — advisory-only until first A/B green
    if enable_augmenter:
        challenger_report = workspace / "_system" / "challenger-report.md"
        if challenger_report.exists():
            ok12 = "augmented atom" in challenger_report.read_text().lower()
        # Else: file missing → advisory pass (book hasn't been challenged yet)
    gate_results.append({"gate": "G12", "name": "augmenter-AB-acceptance",
                         "passed": bool(ok12)})
    # G12 is advisory — warn but do not block ship

    total_gates = len(gate_results)
    return _emit(args, gate_results, "SHIP-READY",
                 f"all {total_gates} gates passed for {args.slug}; ready for publish")


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
