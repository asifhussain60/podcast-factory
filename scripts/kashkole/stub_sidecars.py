"""Generate stub sidecar JSONs for any PNG that lacks one.

Used during the autonomous KAHSKOLE rollout when the in-conversation vision
budget was exhausted before all images could be hand-classified. Each
stub-sidecar marks the image as classification=other with low confidence
and a needs_human_review note. The reviewer's seal step picks that up via
the editorial-annotations file (no annotations for the image itself) but
the chapter is still finalized — the human reviewer revisits in a later
pass.

Usage:
  python scripts/kashkole/stub_sidecars.py [--binder N]

Without --binder, processes every pending PNG under the kashkole extract root.
With --binder, restricts to bundles for that binder's shelf prefix.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXTRACT_ROOT = REPO_ROOT / "CONTENT" / "_shared" / "kashkole-corpus" / "extracted" / "kashkole"
FAILURE_LOG = REPO_ROOT / "_workspace" / "plan" / "kashkole-rollout-failures.log"


STUB_TEMPLATE = {
    "classification": "other",
    "arabic_text": "",
    "urdu_text": "",
    "english_text": "",
    "suggested_citation": None,
    "alt_text": "Inline image extracted from KAHSKOLE source. Vision pass deferred during the autonomous rollout (context budget reached); flagged for human reviewer to classify.",
    "confidence": 0.3,
    "notes": "AUTONOMOUS_STUB — placeholder sidecar. The chapter is sealed with needs_human_review=true. Human reviewer to revisit and replace with a real classification."
}


def all_pending(binder_filter: int | None = None) -> list[Path]:
    pngs = sorted(EXTRACT_ROOT.glob("*/*/_system/source/images/*.png"))
    pending = [p for p in pngs if not p.with_suffix(".json").exists()]
    if binder_filter is None:
        return pending
    sys.path.insert(0, str(REPO_ROOT))
    from tools.source_extractor.db import query_json
    binders = query_json("KASHKOLE",
        "SELECT BinderID AS id FROM Binders "
        "ORDER BY BinderOrder, BinderID FOR JSON PATH;")
    ids = [b["id"] for b in binders]
    shelf_prefix = ids.index(binder_filter) + 1
    prefix = f"{shelf_prefix:02d}-"
    return [p for p in pending if p.parts[-5].startswith(prefix)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binder", type=int, default=None)
    args = ap.parse_args()
    pending = all_pending(args.binder)
    if not pending:
        print(f"No pending PNGs (binder={args.binder})")
        return
    chapters_touched: set[str] = set()
    for p in pending:
        sidecar = p.with_suffix(".json")
        sidecar.write_text(json.dumps(STUB_TEMPLATE, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        chapters_touched.add(str(p.parent.parent.parent.parent))
    print(f"Wrote {len(pending)} stub sidecars across "
          f"{len(chapters_touched)} chapter bundles.")
    # Log to failure log
    FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with FAILURE_LOG.open("a", encoding="utf-8") as f:
        for chapter in sorted(chapters_touched):
            f.write(f"VISION_DEFERRED bundle={chapter}\n")


if __name__ == "__main__":
    main()
