"""migrate_meta_yml.py — idempotent unified-schema migration for all book meta.yml files.

Applies the unified archetype schema to every book's meta.yml under
content/drafts/<slug>/meta.yml. Idempotent: re-running is safe; already-migrated
books are skipped. No schema_version field ever written (DR-009).

USAGE
    python3 scripts/podcast/migrate_meta_yml.py [--dry-run] [--slug <slug>]

EXIT CODES
    0 — all meta.yml files are schema-current
    1 — error
    2 — migrations applied
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[2]
DRAFTS_DIR = REPO_ROOT / "content" / "drafts"

# Canonical archetype mapping per architecture.md §Content Archetypes.
# Keys are book slugs; values are the unified schema fields to apply.
ARCHETYPE_MAP: dict[str, dict[str, Any]] = {
    "kitab-al-riyad": {
        "archetype": "scholarly-deep-dive",
        "density": "deep",
        "capstone_mode": "single_plus_distillation",
    },
    "asaas-al-taveel": {
        "archetype": "scholarly-deep-dive",
        "density": "deep",
        "capstone_mode": "single_plus_distillation",
    },
    "ayyuhal-walad": {
        "archetype": "aphorism-collection",
        "density": "shallow",
        "capstone_mode": "none",
    },
    "islr-mas-i": {
        "archetype": "scholarly-deep-dive",
        "density": "medium",
        "capstone_mode": "single",
    },
    "the-master-and-the-disciple": {
        "archetype": "play-novel",
        "density": "shallow",
        "capstone_mode": "none",
        "requires_preface": True,
    },
    "kunooz-al-hikmah": {
        "archetype": "lecture-series",
        "density": "medium",
        "capstone_mode": "single",
    },
    "rasail-ikhwan-al-safa": {
        "archetype": "encyclopedic-epistolary",
        "density": "deep",
        "capstone_mode": "full_brethren",
    },
}


def _find_meta_ymls(slugs: list[str] | None) -> list[Path]:
    """Return meta.yml paths under content/drafts/, optionally filtered by slug."""
    results: list[Path] = []
    if not DRAFTS_DIR.exists():
        return results
    for candidate in sorted(DRAFTS_DIR.rglob("meta.yml")):
        if slugs:
            slug = candidate.parent.name
            if slug not in slugs:
                continue
        results.append(candidate)
    return results


def _migrate_one(path: Path, dry_run: bool) -> bool:
    """Apply unified schema fields to one meta.yml. Return True if changed."""
    if yaml is None:
        print(f"  [skip] PyYAML not installed — cannot parse {path}", file=sys.stderr)
        return False

    slug = path.parent.name
    mapping = ARCHETYPE_MAP.get(slug)
    if mapping is None:
        return False  # no known mapping for this slug

    text = path.read_text()
    data = yaml.safe_load(text) or {}

    changed = False
    for key, val in mapping.items():
        if data.get(key) != val:
            data[key] = val
            changed = True

    if not changed:
        return False

    if not dry_run:
        # Write back — preserve existing YAML structure by round-tripping.
        # sort_keys=False preserves insertion order where PyYAML supports it.
        path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))
        print(f"  migrated: {slug} → archetype={data.get('archetype')}")
    else:
        print(f"  [dry-run] would migrate: {slug} → archetype={mapping.get('archetype')}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="migrate_meta_yml.py",
        description="Idempotent unified-schema migration for all book meta.yml files.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing.")
    parser.add_argument("--slug", action="append", dest="slugs", metavar="SLUG",
                        help="Restrict migration to one slug (repeatable).")
    args = parser.parse_args(argv)

    paths = _find_meta_ymls(args.slugs)
    if not paths:
        print("migrate_meta_yml: no meta.yml files found; nothing to migrate.")
        return 0

    total_changed = 0
    for path in paths:
        if _migrate_one(path, dry_run=args.dry_run):
            total_changed += 1

    if total_changed == 0:
        print(f"migrate_meta_yml: {len(paths)} file(s) checked — all schema-current.")
        return 0

    action = "would update" if args.dry_run else "updated"
    print(f"migrate_meta_yml: {action} {total_changed}/{len(paths)} meta.yml file(s).")
    return 2


if __name__ == "__main__":
    sys.exit(main())
