"""_book_meta.py — every book gets a meta.yml, built only from what is actually known.

Until 2026-09-19 nothing in intake or scaffold wrote one, although `scaffold_book.py`'s own docstring
says it registers the book "via the per-book meta.yml". The Podcast Factory Library loader then crashed
on the missing file and a person hand-wrote it (isaf-al-talib).

Sources, in order: explicit arguments (what the scaffold was told), then the book's own
`_system/series-config.yaml`. A field nobody supplied stays ABSENT — never guessed. An author or an
Arabic title invented for a religious text is worse than a missing one, and `normalize_book_metadata.py`
already fills silent keys later from every other source. Existing files are never touched.

    python3 scripts/podcast/_book_meta.py <slug>      # create meta.yml from the book's series-config
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml
from _translation_contract import TRANSLATION_EDITION_MODE, read_series_config


def _text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _enable_book_branch(cfg: dict[str, Any]) -> bool:
    if cfg.get("deliverable_mode") == TRANSLATION_EDITION_MODE:
        return True
    series = cfg.get("series")
    series = series if isinstance(series, dict) else {}
    return bool(cfg.get("enable_book_branch") or series.get("enable_book_branch"))


def build_meta(
    slug: str,
    *,
    title: str | None = None,
    author: str | None = None,
    series_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The meta.yml content as an ordered dict. Only keys with a known value are present."""
    cfg = series_config or {}
    meta: dict[str, Any] = {"slug": slug}
    meta["title"] = _text(title) or _text(cfg.get("title")) or slug.replace("-", " ").title()
    for key, value in (
        ("title_arabic", cfg.get("title_arabic")),
        ("title_english", cfg.get("title_english")),
        ("original_title_language", cfg.get("original_title_language") or cfg.get("source_language")),
        ("author", author or cfg.get("author")),
        ("study_track", cfg.get("study_track")),
    ):
        if _text(value):
            meta[key] = _text(value)
    if _enable_book_branch(cfg):
        meta["series"] = {"enable_book_branch": True}
    meta["publication"] = {"status": "draft"}
    return meta


def ensure_meta(
    book_dir: Path,
    slug: str,
    *,
    title: str | None = None,
    author: str | None = None,
    series_config: dict[str, Any] | None = None,
) -> Path | None:
    """Create book_dir/meta.yml if absent; return its path, or None when one already exists."""
    path = Path(book_dir) / "meta.yml"
    if path.exists():
        return None
    cfg = series_config if series_config is not None else read_series_config(book_dir)
    meta = build_meta(slug, title=title, author=author, series_config=cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: _book_meta.py <slug>", file=sys.stderr)
        return 2
    from _paths import find_content

    found = find_content(args[0])
    if found is None:
        print(f"no content found for slug '{args[0]}'", file=sys.stderr)
        return 1
    created = ensure_meta(found[2], args[0])
    print(f"created {created}" if created else f"{args[0]}: meta.yml already exists — left untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
