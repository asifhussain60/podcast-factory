"""CLI entry point.

Usage:
  python -m tools.source_extractor prepare kashkole --binder 1 --chapter 125
  python -m tools.source_extractor finalize kashkole --binder 1 --chapter 125

  (KSESSIONS adapter not yet implemented — raises NotImplementedError.)

After `prepare`, the Stage B in-conversation vision pass happens — Claude reads
each NNN.png in the book's -images/ directory and writes a sibling NNN.json
sidecar with classification + OCR + suggested citation. Then `finalize`
substitutes placeholders, runs adapter-specific citation cleanup, and emits
the final .md.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

from .adapters import get_adapter
from .adapters.base import BookIds
from .stages.prepare import prepare_book
from .stages.finalize import finalize_book


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXTRACT_ROOT = REPO_ROOT / "CONTENT" / "_shared" / "source-library" / "extracted"


def _add_ids_args(parser: argparse.ArgumentParser, adapter_name: str) -> None:
    """Add --shelf-id / --book-id (canonical) plus adapter-specific aliases."""
    parser.add_argument(
        "--shelf-id", type=int,
        help="Generic shelf id (adapter-specific aliases also accepted).",
    )
    parser.add_argument(
        "--book-id", type=int,
        help="Generic book id (adapter-specific aliases also accepted).",
    )
    if adapter_name in ("kashkole", "kahskole"):
        parser.add_argument("--binder", type=int, dest="shelf_id_alias",
                            help="Alias for --shelf-id (KAHSKOLE.BinderID).")
        parser.add_argument("--chapter", type=int, dest="book_id_alias",
                            help="Alias for --book-id (KAHSKOLE.ChapterID).")
    elif adapter_name == "ksessions":
        parser.add_argument("--group", type=int, dest="shelf_id_alias",
                            help="Alias for --shelf-id (KSESSIONS.GroupID).")
        parser.add_argument("--category", type=int, dest="book_id_alias",
                            help="Alias for --book-id (KSESSIONS.CategoryID).")


def _resolve_ids(args: argparse.Namespace) -> BookIds:
    shelf_id = args.shelf_id if args.shelf_id is not None else getattr(args, "shelf_id_alias", None)
    book_id = args.book_id if args.book_id is not None else getattr(args, "book_id_alias", None)
    if shelf_id is None or book_id is None:
        raise SystemExit(
            "Missing required ids. Pass --shelf-id/--book-id "
            "or the adapter-specific aliases (--binder/--chapter, --group/--category)."
        )
    return BookIds(shelf_id=shelf_id, book_id=book_id)


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="python -m tools.source_extractor",
        description="SQL source database → podcast-pipeline source bundle.",
    )
    ap.add_argument(
        "--extract-root", type=Path, default=DEFAULT_EXTRACT_ROOT,
        help=f"Filesystem root for extracted output. Default: {DEFAULT_EXTRACT_ROOT}",
    )

    cmd = ap.add_subparsers(dest="cmd", required=True)

    # prepare <adapter>
    p_prepare = cmd.add_parser("prepare", help="Stage A: DB → draft MD + images + vision-tasks.")
    p_prepare_sub = p_prepare.add_subparsers(dest="adapter", required=True)
    for name in ("kashkole", "ksessions"):
        sp = p_prepare_sub.add_parser(name, help=f"{name.upper()} adapter")
        _add_ids_args(sp, name)

    # finalize <adapter>
    p_finalize = cmd.add_parser("finalize", help="Stage C: substitute + cleanup + emit final .md.")
    p_finalize_sub = p_finalize.add_subparsers(dest="adapter", required=True)
    for name in ("kashkole", "ksessions"):
        sp = p_finalize_sub.add_parser(name, help=f"{name.upper()} adapter")
        _add_ids_args(sp, name)

    args = ap.parse_args()
    adapter = get_adapter(args.adapter)
    ids = _resolve_ids(args)
    extract_root = args.extract_root

    if args.cmd == "prepare":
        bundle_root = prepare_book(adapter, ids, extract_root)
        print(f"PREPARED: {bundle_root}/")
        print(f"  bundle.yml:                {bundle_root}/bundle.yml")
        print(f"  raw-extract (draft):       "
              f"{bundle_root}/_system/source/text/raw-extract.md.draft")
        print(f"  images:                    "
              f"{bundle_root}/_system/source/images/")
        tasks_path = bundle_root / "_system" / "source" / "images" / "vision-tasks.json"
        if tasks_path.exists():
            with tasks_path.open() as f:
                tasks = json.load(f)
            print(
                f"  vision tasks: {len(tasks['images'])} "
                f"images awaiting processing"
            )
    elif args.cmd == "finalize":
        final = finalize_book(adapter, ids, extract_root)
        print(f"FINALIZED: {final}")


if __name__ == "__main__":
    main()
