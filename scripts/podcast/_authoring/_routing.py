"""Content routing helpers for podcast authoring phases."""

from __future__ import annotations

import json
from pathlib import Path

ARABIC_SCHOLARLY_CATEGORIES: frozenset[str] = frozenset(
    {
        "books",
        "letters",
        "lectures",
        "articles",
        "asbaaq",
        "documents",
        "interviews",
    }
)

SKIP_PHONETICS_CATEGORIES: frozenset[str] = frozenset(
    {
        "sites",
        "explainers",
    }
)

SKIP_ENRICHMENT_CATEGORIES: frozenset[str] = frozenset(
    {
        "sites",
    }
)

SKIP_OCR_CATEGORIES: frozenset[str] = frozenset(
    {
        "sites",
        "explainers",
    }
)

FICTION_CONTENT_PROFILES: frozenset[str] = frozenset({"fiction"})


def _read_category(book_dir: Path) -> str:
    """Read a book's content category, defaulting to the scholarly path."""
    state_path = book_dir / "_system" / "orchestrator-state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            cat = state.get("category", "").strip()
            if cat:
                return cat.lower()
        except Exception:
            pass

    meta_path = book_dir / "_system" / "meta.yml"
    if meta_path.exists():
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("category:"):
                cat = line.split(":", 1)[1].strip().strip('"').strip("'")
                if cat:
                    return cat.lower()

    return "books"


def _read_content_profile(book_dir: Path) -> str:
    """Read a book's content profile, distinct from category."""
    state_path = book_dir / "_system" / "orchestrator-state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            prof = state.get("content_profile", "").strip()
            if prof:
                return prof.lower()
        except Exception:
            pass

    cfg_path = book_dir / "_system" / "series-config.yaml"
    if cfg_path.exists():
        for line in cfg_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("content_profile:"):
                prof = line.split(":", 1)[1].strip().strip('"').strip("'")
                if prof:
                    return prof.lower()

    return ""
