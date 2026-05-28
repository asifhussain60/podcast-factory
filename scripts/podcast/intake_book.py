#!/usr/bin/env python3
"""intake_book.py — automate the manual setup that precedes per-chapter authoring
for a new book in the podcast pipeline (Phase 7.5 of the intelligence-enhancements plan).

Two modes:

1. PDF intake (original):
     scripts/podcast/intake_book.py <pdf-path> <book-slug>
   Copies the PDF, builds the workspace skeleton, initializes
   orchestrator-state at phase=preflight (Phase 0a will run from scratch).

2. Bundle intake (new — for source_extractor output):
     scripts/podcast/intake_book.py --from-bundle <bundle-path> [--slug X] [--category C]
   Reads bundle.yml, copies the bundle's _system/source/ into
   content/drafts/<slug>/_system/source/, initializes orchestrator-state with
   Phase 0a marked complete (the bundle already contains raw-extract.md).
   Next phase:
     - source_language == "en"  → 0b refine
     - source_language != "en"  → 0a-translate (pending — Phase E)

What it does NOT do:
  - Author chapters or framings (that's the orchestrator + Step D pattern).
  - Mutate develop or any other branch.
  - Push the new branch (operator decides when).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from _paths import REPO_ROOT

WORKSPACE_BOOKS = REPO_ROOT / "content" / "drafts"
RAW_DIR = REPO_ROOT.parent.parent / "raw"  # podcast-factory/raw/, outside the worktree

SKELETON_DIRS = ["_source", "_system", "chapters", "episodes", "episode-drafts"]
SLUG_RE_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


def _die(msg: str) -> None:
    print(f"intake_book: {msg}", file=sys.stderr)
    sys.exit(2)


def _info(msg: str) -> None:
    print(msg)


def _validate_slug(slug: str) -> None:
    if not re.match(SLUG_RE_PATTERN, slug):
        _die(f"slug '{slug}' must be lowercase-kebab-case (a-z, 0-9, hyphens)")


def _create_skeleton(book_dir: Path, force: bool) -> None:
    """Create the standard workspace skeleton under book_dir."""
    if book_dir.exists() and not force:
        _die(
            f"book workspace already exists: {book_dir}\n  "
            f"Use --force to overwrite or pick a different slug."
        )
    if force and book_dir.exists():
        _info(f"==> Removing existing workspace at {book_dir} (--force)")
        shutil.rmtree(book_dir)
    for d in SKELETON_DIRS:
        (book_dir / d).mkdir(parents=True, exist_ok=True)


def _create_branch(category: str, slug: str) -> str | None:
    """Create the typed content branch off develop. Returns the branch name
    on success, None on warning (we still return for the next-action hint)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _branching import branch_name  # noqa: E402

    branch = branch_name(category, slug)
    result = subprocess.run(
        ["git", "rev-parse", "--verify", branch],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if result.returncode == 0:
        _info(f"==> Branch already exists: {branch} (skipping)")
        return branch
    _info(f"==> Creating branch {branch} from develop")
    r = subprocess.run(
        ["git", "branch", branch, "develop"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if r.returncode != 0:
        _info(f"    WARN: could not create branch — {r.stderr.strip()}")
        return None
    _info(f"    Created. Switch with: git checkout {branch}")
    return branch


# ---- PDF intake (original) --------------------------------------------------

def _intake_from_pdf(
    pdf_path: str, slug: str, force: bool, no_branch: bool,
    category: str = "books",
) -> int:
    _validate_slug(slug)

    src = Path(pdf_path).expanduser()
    if not src.is_absolute():
        for candidate in [RAW_DIR / src, Path.cwd() / src, REPO_ROOT / src]:
            if candidate.exists():
                src = candidate
                break
    if not src.exists():
        _die(
            f"source not found: {pdf_path} "
            f"(looked under {RAW_DIR}, cwd, and repo root)"
        )

    book_dir = WORKSPACE_BOOKS / slug
    _info(f"==> Creating workspace at {book_dir.relative_to(REPO_ROOT)}")
    _create_skeleton(book_dir, force)
    _info(f"    Skeleton dirs: {', '.join(SKELETON_DIRS)}")

    dst_pdf = book_dir / "_source" / src.name
    shutil.copy2(src, dst_pdf)
    _info(f"    Copied source: raw/{src.name} → {dst_pdf.relative_to(REPO_ROOT)}")

    state = {
        "schema_version": 1,
        "book_slug": slug,
        "source_path": str(dst_pdf.relative_to(REPO_ROOT)),
        "source_kind": "pdf",
        "phase": "preflight",
        "phase_status": "pending",
        "last_completed_phase": None,
        "last_error": None,
        "category": category,
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phases": {},
        "intake_via": "scripts/podcast/intake_book.py",
    }
    state_path = book_dir / "_system" / "orchestrator-state.json"
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    _info(f"    state.json: phase=preflight, phase_status=pending")

    if not no_branch:
        _create_branch(category, slug)

    _info("")
    _info(f"==> DONE. Next steps:")
    _info(f"    1. python3 scripts/podcast/orchestrate_book.py "
          f"--start {dst_pdf.relative_to(REPO_ROOT)} --slug {slug}")
    _info(f"    2. Watch Phase 0a (OCR) run; advance through 0b/0c/0d as gates clear.")
    return 0


# ---- Bundle intake (new) ----------------------------------------------------

_BUNDLE_FIELD_RE = re.compile(r"^([a-z_]+):\s*(.*)$")


def _read_bundle_yml(bundle_yml: Path) -> dict:
    """Minimal reader for our self-generated bundle.yml shape.

    Returns a flat dict of the fields we care about for intake. Format is
    fully controlled by tools.source_extractor.bundle.write_bundle_yml — keep
    in sync if that emitter changes."""
    out: dict = {}
    current_block: str | None = None
    for raw_line in bundle_yml.read_text(encoding="utf-8").splitlines():
        # strip trailing comments outside quoted strings (our YAML has no quotes
        # except via json.dumps, which never contains '#')
        line = raw_line.split("#", 1)[0].rstrip() if "#" in raw_line else raw_line.rstrip()
        if not line or line.startswith("#"):
            continue
        # Top-level scalar (no leading spaces, no nested-list bullet)
        if not line.startswith(" ") and not line.startswith("\t"):
            m = _BUNDLE_FIELD_RE.match(line)
            if m:
                key, val = m.group(1), m.group(2).strip()
                if val == "":
                    current_block = key
                    out[key] = {}
                else:
                    current_block = None
                    out[key] = val
        elif line.startswith("  ") and not line.startswith("    "):
            # Single-level nested field (e.g. inside shelf:, book:, pipeline_hints:)
            inner = line[2:]
            m = _BUNDLE_FIELD_RE.match(inner)
            if m and current_block is not None:
                key, val = m.group(1), m.group(2).strip()
                if isinstance(out.get(current_block), dict):
                    out[current_block][key] = val
    return out


def _intake_from_bundle(
    bundle_path: str, slug_override: str | None, category_override: str | None,
    force: bool, no_branch: bool,
) -> int:
    bundle_dir = Path(bundle_path).expanduser().resolve()
    if not bundle_dir.is_dir():
        _die(f"bundle path is not a directory: {bundle_dir}")

    bundle_yml = bundle_dir / "bundle.yml"
    if not bundle_yml.exists():
        _die(f"bundle missing required bundle.yml at {bundle_yml}")

    src_root = bundle_dir / "_system" / "source"
    if not src_root.is_dir():
        _die(f"bundle missing _system/source/ at {src_root}")

    raw_extract = src_root / "text" / "raw-extract.md"
    if not raw_extract.exists():
        _die(
            f"bundle missing finalized raw-extract.md at {raw_extract}\n  "
            f"(was finalize stage run? a .draft suggests prepare ran but vision/finalize did not)"
        )

    fields = _read_bundle_yml(bundle_yml)
    bundle_stage = fields.get("stage", "").strip().strip("'\"")
    if bundle_stage != "finalized":
        _die(
            f"bundle stage is '{bundle_stage}', not 'finalized'. "
            f"Run finalize on the bundle before intake."
        )

    source_language = fields.get("source_language", "").strip().strip("'\"")
    if not source_language:
        _die("bundle.yml missing required source_language")

    hints = fields.get("pipeline_hints", {}) if isinstance(fields.get("pipeline_hints"), dict) else {}
    suggested_slug = (hints.get("suggested_slug") or "").strip().strip("'\"")
    suggested_category = (hints.get("suggested_category") or "").strip().strip("'\"")

    slug = slug_override or suggested_slug
    if not slug:
        _die(
            "no slug — bundle has no pipeline_hints.suggested_slug and no --slug given"
        )
    _validate_slug(slug)

    category = category_override or suggested_category or "lectures"

    book_dir = WORKSPACE_BOOKS / slug
    _info(f"==> Bundle intake")
    _info(f"    bundle: {bundle_dir}")
    _info(f"    slug:   {slug}")
    _info(f"    source_language: {source_language}")
    _info(f"    category: {category}")

    _info(f"==> Creating workspace at {book_dir.relative_to(REPO_ROOT)}")
    _create_skeleton(book_dir, force)
    _info(f"    Skeleton dirs: {', '.join(SKELETON_DIRS)}")

    # Copy bundle's _system/source/ into content/drafts/<slug>/_system/source/
    dst_source = book_dir / "_system" / "source"
    shutil.copytree(src_root, dst_source, dirs_exist_ok=True)
    _info(f"    Copied _system/source/ from bundle")

    # Preserve the bundle manifest at a fixed location for traceability
    shutil.copy2(bundle_yml, book_dir / "_system" / "source-bundle-manifest.yml")
    _info(f"    Bundle manifest copied to _system/source-bundle-manifest.yml")

    # Determine next phase based on source_language
    if source_language == "en":
        next_phase = "0b"
        phase_status = "pending"
        last_error = None
    else:
        next_phase = "0a-translate"
        phase_status = "pending"
        last_error = (
            f"Phase 0a-translate not yet implemented (Phase E pending). "
            f"Source language is '{source_language}'; refine cannot run until "
            f"the orchestrator gains a translate step."
        )

    # Pull the finalize timestamp from _provenance.json (bundle.yml doesn't carry it)
    finalized_at = None
    prov_path = src_root / "text" / "_provenance.json"
    if prov_path.exists():
        try:
            prov = json.loads(prov_path.read_text(encoding="utf-8"))
            finalized_at = prov.get("finalize", {}).get("finalized_at")
        except Exception:
            pass

    state = {
        "schema_version": 1,
        "book_slug": slug,
        "source_path": str((dst_source / "text" / "raw-extract.md").relative_to(REPO_ROOT)),
        "source_kind": "bundle",
        "source_language": source_language,
        "source_bundle_origin": str(bundle_dir),
        "phase": next_phase,
        "phase_status": phase_status,
        "last_completed_phase": "0a",
        "last_error": last_error,
        "category": category,
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phases": {
            "0a": {
                "completed_via": "tools.source_extractor",
                "completed_at": finalized_at,
            }
        },
        "intake_via": "scripts/podcast/intake_book.py --from-bundle",
    }
    state_path = book_dir / "_system" / "orchestrator-state.json"
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    _info(
        f"    state.json: phase={next_phase}, phase_status={phase_status}, "
        f"last_completed_phase=0a"
    )

    if not no_branch:
        _create_branch(category, slug)

    _info("")
    _info(f"==> DONE. Next steps:")
    if source_language == "en":
        _info(f"    1. python3 scripts/podcast/orchestrate_book.py --resume {slug}")
        _info(f"    2. Pipeline picks up at Phase 0b (refine).")
    else:
        _info(
            f"    Phase 0a-translate is not yet implemented "
            f"(Phase E of the source-extractor work)."
        )
        _info(f"    State is recorded; orchestrator will halt on translate until ready.")
    return 0


# ---- Entry point ------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "pdf_path", nargs="?",
        help="Source PDF path (required unless --from-bundle is used).",
    )
    parser.add_argument(
        "slug", nargs="?",
        help="Book slug (required for PDF intake; "
             "may override bundle's suggested_slug for --from-bundle).",
    )
    parser.add_argument(
        "--from-bundle", dest="from_bundle", metavar="PATH",
        help="Intake a source-extractor bundle directory instead of a PDF.",
    )
    parser.add_argument(
        "--slug", dest="slug_flag",
        help="Override slug (with --from-bundle).",
    )
    parser.add_argument(
        "--category", dest="category_flag",
        help="Override category (default: 'books' for PDF, "
             "bundle.suggested_category for --from-bundle).",
    )
    parser.add_argument(
        "--no-branch", action="store_true",
        help="Skip git branch creation (workspace setup only).",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite an existing workspace skeleton.",
    )
    args = parser.parse_args()

    if args.from_bundle:
        if args.pdf_path is not None and args.slug is None:
            # The user passed a single positional with --from-bundle — treat
            # it as a slug override (the more common intent).
            args.slug_flag = args.slug_flag or args.pdf_path
        return _intake_from_bundle(
            bundle_path=args.from_bundle,
            slug_override=args.slug_flag,
            category_override=args.category_flag,
            force=args.force,
            no_branch=args.no_branch,
        )

    # PDF intake — require both positionals
    if not args.pdf_path or not args.slug:
        _die(
            "PDF intake needs both <pdf-path> and <slug>. "
            "For bundle intake, use --from-bundle <path>."
        )
    return _intake_from_pdf(
        pdf_path=args.pdf_path,
        slug=args.slug,
        force=args.force,
        no_branch=args.no_branch,
        category=args.category_flag or "books",
    )


if __name__ == "__main__":
    sys.exit(main())
