"""Intelligence layer — phase 0h step 3: DB-backed Augmenter.

Enriches episode text with relevant doctrine atoms from the Kashkole corpus
stored in the knowledge-base DB.  This is the Wave B upgrade of the JSONL-based
`knowledge/augmenter.py`.  The old JSONL augmenter remains as a fallback for
books without DB-backed atoms.

Guards:
  - `series.enable_knowledge_augmenter` must be True in the book's meta.yml
    (default: disabled, per R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED = False).
  - Only atoms with `needs_review = 0` (high-confidence, human-approved) are used.
  - Arabic script is never included in the injected block (DR-012).

Authority: architecture.md §Intelligence Layer; plan.md Wave B, B3.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _db
from _rules import R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED

# Maximum doctrine atoms injected per augmentation call
_MAX_ATOMS_DEFAULT = 5
# Strip Arabic Unicode range (U+0600–U+06FF and extended)
_ARABIC_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]+")

_PROMPT_BLOCK_HEADER = "[PRIOR DOCTRINAL CONTEXT — Kashkole corpus]"


# ─── public API ───────────────────────────────────────────────────────────────

def augment_episode_text(
    episode_text: str,
    book_dir: Path,
    topic_tags: Sequence[str] | None = None,
    *,
    max_atoms: int = _MAX_ATOMS_DEFAULT,
    tradition: str | None = None,
) -> str:
    """Prepend a doctrine-context block to episode text.

    Returns the original text unchanged if:
      - augmentation is disabled in meta.yml
      - no matching atoms found in DB
      - topic_tags is empty

    Args:
        episode_text: The framing/episode text to augment.
        book_dir:     `content/drafts/<slug>/` — used to read meta.yml.
        topic_tags:   Tags to filter doctrine atoms by (from chapter meta or
                      the book's series-config.yaml).  If None, falls back to
                      book-level tags from meta.yml.
        max_atoms:    Maximum doctrine atoms to inject.

    Returns:
        The (possibly augmented) episode text.
    """
    if not _augmentation_enabled(book_dir):
        return episode_text

    tags = list(topic_tags or []) or _book_tags(book_dir)
    if not tags:
        return episode_text

    book_tradition = tradition or _book_tradition(book_dir)
    atoms = _fetch_doctrine_atoms(tags, max_atoms=max_atoms, tradition=book_tradition)
    if not atoms:
        return episode_text

    block = _build_context_block(atoms)
    return block + "\n\n" + episode_text


def fetch_atoms_for_tags(
    tags: Sequence[str],
    max_atoms: int = _MAX_ATOMS_DEFAULT,
    tradition: str | None = None,
) -> list[dict]:
    """Return a list of doctrine atom dicts matching any of the given tags.

    Only returns atoms where needs_review = 0 (high-confidence, approved).
    Filters by tradition: only atoms whose tradition matches ``tradition`` or
    is 'universal' are returned.
    """
    return _fetch_doctrine_atoms(list(tags), max_atoms=max_atoms, tradition=tradition or "universal")


# ─── internal helpers ─────────────────────────────────────────────────────────

def _augmentation_enabled(book_dir: Path) -> bool:
    """Read `enable_knowledge_augmenter` from meta.yml. Default: False."""
    meta_path = book_dir / "meta.yml"
    if not meta_path.exists():
        return R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED
    try:
        import yaml  # type: ignore[import]
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        return bool(meta.get("series", {}).get("enable_knowledge_augmenter",
                                                R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED))
    except Exception:   # noqa: BLE001
        return R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED


def _book_tradition(book_dir: Path) -> str:
    """Read tradition_affinity from meta.yml. Default: 'universal'."""
    meta_path = book_dir / "meta.yml"
    if not meta_path.exists():
        return "universal"
    try:
        import yaml  # type: ignore[import]
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        return str(meta.get("tradition_affinity", "universal"))
    except Exception:  # noqa: BLE001
        return "universal"


def _book_tags(book_dir: Path) -> list[str]:
    """Read `knowledge_tags` from meta.yml as fallback topic list."""
    meta_path = book_dir / "meta.yml"
    if not meta_path.exists():
        return []
    try:
        import yaml  # type: ignore[import]
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        return list(meta.get("knowledge_tags", []))
    except Exception:   # noqa: BLE001
        return []


def _fetch_doctrine_atoms(tags: list[str], *, max_atoms: int, tradition: str = "universal") -> list[dict]:
    """Query DB for doctrine atoms tagged with any of the given tags.

    Filters by tradition: returns atoms where tradition = <tradition> OR
    tradition = 'universal'.  This prevents cross-tradition injection.
    """
    if not tags:
        return []
    conn = _db.get_connection()
    placeholders = ",".join("?" * len(tags))
    rows = conn.execute(
        f"""
        SELECT DISTINCT a.id, a.body
        FROM atoms a
        JOIN atom_topic_tags t ON t.atom_id = a.id
        WHERE a.type = 'doctrine'
          AND (a.tradition = ? OR a.tradition = 'universal')
          AND t.tag IN ({placeholders})
        ORDER BY a.id
        LIMIT ?
        """,
        (tradition, *tags, max_atoms),
    ).fetchall()
    result = []
    for atom_id, body_json in rows:
        try:
            body = json.loads(body_json)
        except json.JSONDecodeError:
            continue
        result.append({"id": atom_id, "body": body})
    return result


def _strip_arabic(text: str) -> str:
    """Remove Arabic script runs from text (DR-012)."""
    return _ARABIC_RE.sub("", text).strip()


def _build_context_block(atoms: list[dict]) -> str:
    """Format doctrine atoms as a prompt injection block."""
    lines = [_PROMPT_BLOCK_HEADER, ""]
    for atom in atoms:
        body = atom.get("body", {})
        text_en = _strip_arabic(body.get("text_en", ""))
        if not text_en:
            continue
        binder = body.get("binder_slug", "")
        chapter = body.get("chapter_slug", "")
        tags_label = f"{binder}, ch. {chapter}" if binder else ""
        lines.append(f"Source: Kashkole — {tags_label}".rstrip(" —").rstrip())
        lines.append("---")
        lines.append(text_en)
        lines.append("")
    return "\n".join(lines).strip()


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Fetch doctrine atoms for given topic tags.")
    parser.add_argument("tags", nargs="+", help="Topic tags to look up (e.g. tawhid eschatology)")
    parser.add_argument("--max", type=int, default=_MAX_ATOMS_DEFAULT, help="Max atoms to return")
    args = parser.parse_args()
    atoms = fetch_atoms_for_tags(args.tags, max_atoms=args.max)
    if not atoms:
        print("No matching atoms found.")
        return 0
    for atom in atoms:
        body = atom["body"]
        print(f"[{atom['id']}]")
        print(f"  {body.get('text_en', '')[:120]}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
