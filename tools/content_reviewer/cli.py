"""CLI entry point.

Usage:
  python -m tools.content_reviewer review wisdom --binder N --chapter M
  python -m tools.content_reviewer review ksessions --binder N --chapter M
  python -m tools.content_reviewer seal wisdom --binder N --chapter M

Resolves the bundle directory by reusing tools.source_extractor's adapter
(adapter.resolve_book gives us the slugs and prefixes needed to compute the
BOOK_DIR). The reviewer does not touch the DB beyond optionally instantiating
the adapter's Quran corpus for sentence-completion / quran-uncited lookups.
"""
from __future__ import annotations
import argparse
from pathlib import Path

from tools.source_extractor.adapters import get_adapter as get_source_adapter
from tools.source_extractor.adapters.base import BookIds
from tools.source_extractor.bundle import bundle_paths

from .adapters import get_review_adapter
from .stages.review import review_book
from .stages.seal import seal_book


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXTRACT_ROOT = REPO_ROOT / "CONTENT" / "_shared" / "source-library" / "extracted"


def _add_ids_args(parser: argparse.ArgumentParser, adapter_name: str) -> None:
    parser.add_argument("--shelf-id", type=int)
    parser.add_argument("--book-id", type=int)
    if adapter_name in ("wisdom", "kashkole", "kahskole"):
        parser.add_argument("--binder", type=int, dest="shelf_id_alias")
        parser.add_argument("--chapter", type=int, dest="book_id_alias")
    elif adapter_name == "ksessions":
        parser.add_argument("--group", type=int, dest="shelf_id_alias")
        parser.add_argument("--category", type=int, dest="book_id_alias")


def _resolve_ids(args: argparse.Namespace) -> BookIds:
    shelf_id = args.shelf_id if args.shelf_id is not None else getattr(args, "shelf_id_alias", None)
    book_id = args.book_id if args.book_id is not None else getattr(args, "book_id_alias", None)
    if shelf_id is None or book_id is None:
        raise SystemExit(
            "Missing required ids. Pass --shelf-id/--book-id or "
            "--binder/--chapter (wisdom) or --group/--category (ksessions)."
        )
    return BookIds(shelf_id=shelf_id, book_id=book_id)


def _resolve_bundle_root(adapter_name: str, ids: BookIds, extract_root: Path) -> Path:
    src_adapter = get_source_adapter(adapter_name)
    meta = src_adapter.resolve_book(ids)
    paths = bundle_paths(extract_root, meta)
    return paths.root


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="python -m tools.content_reviewer",
        description="Annotation-layer reviewer for source-extractor bundles.",
    )
    ap.add_argument("--extract-root", type=Path, default=DEFAULT_EXTRACT_ROOT)

    cmd = ap.add_subparsers(dest="cmd", required=True)

    for cmd_name in ("review", "seal"):
        c = cmd.add_parser(cmd_name)
        c_sub = c.add_subparsers(dest="adapter", required=True)
        for name in ("wisdom", "ksessions"):
            sp = c_sub.add_parser(name)
            _add_ids_args(sp, name)

    args = ap.parse_args()
    ids = _resolve_ids(args)
    bundle_root = _resolve_bundle_root(args.adapter, ids, args.extract_root)

    if args.cmd == "review":
        review_adapter = get_review_adapter(args.adapter)
        # Quran corpus from source_extractor adapter (KAHSKOLE only currently).
        src_adapter = get_source_adapter(args.adapter)
        quran_corpus = src_adapter.get_quran_corpus()
        counts = review_book(review_adapter, bundle_root, quran_corpus=quran_corpus)
        if counts.get("skipped"):
            print(f"SKIPPED (already reviewed): {bundle_root}")
        else:
            print(f"REVIEWED: {bundle_root}")
            print(f"  total annotations: {counts['total']}")
            for k, v in sorted(counts["by_type"].items()):
                print(f"    {k}: {v}")
    elif args.cmd == "seal":
        result = seal_book(bundle_root)
        flag = " (needs_human_review!)" if result["needs_human_review"] else ""
        print(f"SEALED: {bundle_root}{flag}")
        print(f"  total annotations: {result['total_annotations']}")
        print(f"  needs_human_review_count: {result['needs_human_review_count']}")


if __name__ == "__main__":
    main()
