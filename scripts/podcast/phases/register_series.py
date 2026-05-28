"""phases/register_series.py — Phase 0g: register series in cross-book registry.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT


def _info(msg: str) -> None:
    print(msg)


def phase_0g_register(book_dir: Path) -> None:
    """Append episode rows to PODCAST_ROOT/.skill/registry.md (idempotent).

    This is a deterministic deferred step — Phase 0d already wrote per-chapter
    contracts; 0g surfaces the series in the cross-book registry so subsequent
    validate_registry.py runs see it.
    """
    registry = REPO_ROOT / "content" / "podcast" / ".skill" / "registry.md"
    if not registry.exists():
        return
    book_slug = book_dir.name
    contracts_dir = book_dir / "chapter-contracts"
    if not contracts_dir.is_dir():
        return

    import yaml as _yaml
    existing = registry.read_text(encoding="utf-8")
    new_lines: list[str] = []
    for yml in sorted(contracts_dir.glob("*.yml")):
        with yml.open("r", encoding="utf-8") as f:
            data = _yaml.safe_load(f) or {}
        ep = data.get("episode_number", "?")
        slug = data.get("slug", yml.stem)
        title = data.get("title", slug)
        source_type = data.get("source_type", "book-chapter")
        if f"`{slug}`" in existing:
            continue
        new_lines.append(
            f"| EP{ep:02d} | {title} | `{slug}` | {source_type} | drafted | "
            f"{book_slug} | — |"
            if isinstance(ep, int) else
            f"| EP{ep} | {title} | `{slug}` | {source_type} | drafted | {book_slug} | — |"
        )
    if new_lines:
        with registry.open("a", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")
