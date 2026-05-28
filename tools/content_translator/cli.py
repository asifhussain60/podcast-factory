"""CLI entry point.

Usage:
  python -m tools.content_translator translate wisdom --binder N --chapter M
  python -m tools.content_translator adapt     wisdom --binder N --chapter M
  python -m tools.content_translator seal      wisdom --binder N --chapter M --stage adapted
  python -m tools.content_translator status
  python -m tools.content_translator status    --binder N --chapter M --format stage
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.source_extractor.adapters import get_adapter as get_source_adapter
from tools.source_extractor.adapters.base import BookIds
from tools.source_extractor.bundle import bundle_paths

from .stages.translate import translate_bundle
from .stages.adapt import surface_adapt_brief
from .stages.seal import seal_stage

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXTRACT_ROOT = REPO_ROOT / "CONTENT" / "_shared" / "source-library" / "extracted"
COST_LEDGER = REPO_ROOT / "_workspace" / "plan" / "wisdom-translation-cost-ledger.jsonl"


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
    shelf_id = args.shelf_id if getattr(args, "shelf_id", None) is not None else getattr(args, "shelf_id_alias", None)
    book_id = args.book_id if getattr(args, "book_id", None) is not None else getattr(args, "book_id_alias", None)
    if shelf_id is None or book_id is None:
        raise SystemExit(
            "Missing IDs. Pass --binder/--chapter (wisdom) or --shelf-id/--book-id."
        )
    return BookIds(shelf_id=shelf_id, book_id=book_id)


def _resolve_bundle_root(adapter_name: str, ids: BookIds, extract_root: Path) -> Path:
    src_adapter = get_source_adapter(adapter_name)
    meta = src_adapter.resolve_book(ids)
    paths = bundle_paths(extract_root, meta)
    return paths.root


def _status_summary(args: argparse.Namespace) -> None:
    """Print ledger summary or per-chapter stage."""
    has_chapter = (
        getattr(args, "binder", None) is not None
        or getattr(args, "shelf_id", None) is not None
    )
    fmt = getattr(args, "format", None) or "summary"

    if has_chapter and fmt in ("stage", "nhr"):
        ids = _resolve_ids(args)
        bundle_root = _resolve_bundle_root("wisdom", ids, args.extract_root)
        bundle_yml = bundle_root / "bundle.yml"
        if not bundle_yml.exists():
            print("unknown")
            return
        text = bundle_yml.read_text(encoding="utf-8")
        if fmt == "stage":
            for line in text.splitlines():
                if line.startswith("stage:"):
                    print(line.split(":", 1)[1].strip())
                    return
            print("unknown")
        elif fmt == "nhr":
            for line in text.splitlines():
                if line.startswith("needs_human_review:"):
                    print(line.split(":", 1)[1].strip())
                    return
            print("false")
        return

    # Ledger summary
    if fmt == "session-cost":
        total = 0.0
        if COST_LEDGER.exists():
            with COST_LEDGER.open() as f:
                for line in f:
                    line = line.strip()
                    if line:
                        total += json.loads(line).get("cost_usd", 0.0)
        print(f"{total:.4f}")
        return

    # Full summary table
    if not COST_LEDGER.exists():
        print("No cost ledger yet. Run translate on a chapter first.")
        return

    entries: list[dict] = []
    with COST_LEDGER.open() as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    total_cost = sum(e.get("cost_usd", 0) for e in entries)
    print(f"\nKASHKOLE Translation Cost Ledger — {len(entries)} entries, total ${total_cost:.4f}\n")
    print(f"  {'binder':>6}  {'chapter':>7}  {'phase':>12}  {'cost_usd':>10}  completed_at")
    print(f"  {'-'*6}  {'-'*7}  {'-'*12}  {'-'*10}  {'-'*24}")
    for e in entries:
        print(
            f"  {str(e.get('binder_id','')):>6}  "
            f"{str(e.get('chapter_id','')):>7}  "
            f"{e.get('phase',''):>12}  "
            f"${e.get('cost_usd', 0):>9.4f}  "
            f"{e.get('completed_at', '')}"
        )
    print(f"\n  Total: ${total_cost:.4f}\n")


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="python -m tools.content_translator",
        description="Urdu→English translation + adaptation pipeline for wisdom bundles.",
    )
    ap.add_argument("--extract-root", type=Path, default=DEFAULT_EXTRACT_ROOT)

    cmd = ap.add_subparsers(dest="cmd", required=True)

    # translate
    for cmd_name in ("translate", "adapt", "adapt-auto"):
        c = cmd.add_parser(cmd_name)
        c.add_argument("--dry-run", action="store_true", default=False)
        c_sub = c.add_subparsers(dest="adapter", required=True)
        for name in ("wisdom", "ksessions"):
            sp = c_sub.add_parser(name)
            _add_ids_args(sp, name)

    # challenge
    for cmd_name in ("challenge",):
        c = cmd.add_parser(cmd_name)
        c.add_argument("--dry-run", action="store_true", default=False)
        c_sub = c.add_subparsers(dest="adapter", required=True)
        for name in ("wisdom", "ksessions"):
            sp = c_sub.add_parser(name)
            _add_ids_args(sp, name)

    # seal
    seal_cmd = cmd.add_parser("seal")
    seal_cmd.add_argument(
        "--stage",
        required=True,
        choices=["translated", "adapted", "challenged"],
        help="Target stage to seal to.",
    )
    seal_sub = seal_cmd.add_subparsers(dest="adapter", required=True)
    for name in ("wisdom", "ksessions"):
        sp = seal_sub.add_parser(name)
        _add_ids_args(sp, name)

    # status
    status_cmd = cmd.add_parser("status")
    status_cmd.add_argument("--binder", type=int, dest="shelf_id_alias")
    status_cmd.add_argument("--chapter", type=int, dest="book_id_alias")
    status_cmd.add_argument("--shelf-id", type=int)
    status_cmd.add_argument("--book-id", type=int)
    status_cmd.add_argument(
        "--format",
        choices=["summary", "stage", "nhr", "session-cost"],
        default="summary",
    )

    args = ap.parse_args()

    if args.cmd == "status":
        _status_summary(args)
        return

    ids = _resolve_ids(args)
    bundle_root = _resolve_bundle_root(args.adapter, ids, args.extract_root)

    if args.cmd == "translate":
        result = translate_bundle(
            bundle_root,
            binder_id=ids.shelf_id,
            chapter_id=ids.book_id,
            dry_run=args.dry_run,
        )
        if result.get("skipped"):
            print(f"SKIPPED (already {result['stage']}): {bundle_root}")
        elif result.get("passthrough"):
            print(f"PASSTHROUGH (English source): {bundle_root}")
            print(f"  cost:     $0.0000")
            print(f"  output:   {result['output_path']}")
        else:
            print(f"TRANSLATED: {bundle_root}")
            print(f"  sections: {result['sections_translated']}")
            print(f"  chars:    {result['char_count']:,}")
            print(f"  cost:     ${result['cost_usd']:.4f}")
            print(f"  output:   {result['output_path']}")

    elif args.cmd == "adapt":
        surface_adapt_brief(bundle_root, binder_id=ids.shelf_id, chapter_id=ids.book_id)

    elif args.cmd == "adapt-auto":
        from .stages.adapt_auto import adapt_bundle_auto
        result = adapt_bundle_auto(
            bundle_root,
            binder_id=ids.shelf_id,
            chapter_id=ids.book_id,
            dry_run=args.dry_run,
        )
        if result.get("skipped"):
            print(f"SKIPPED (already {result['stage']}): {bundle_root}")
        elif result.get("dry_run"):
            print(f"DRY-RUN ({result.get('mode','?')}): {bundle_root}")
            print(f"  raw_bytes: {result['raw_bytes']:,}")
            print(f"  chunks:   {result['chunks']}")
        else:
            mode = result.get("mode", "llm")
            print(f"ADAPTED [{mode}]: {bundle_root}")
            print(f"  chunks:     {result['chunks']}")
            print(f"  citations:  {result['citations']}")
            if mode != "deterministic":
                print(f"  tokens in:  {result['input_tokens']:,}")
                print(f"  tokens out: {result['output_tokens']:,}")
            print(f"  cost:       ${result['cost_usd']:.4f}")
            print(f"  output:     {result['output_path']}")

    elif args.cmd == "challenge":
        from tools.content_challenger.wisdom.challenge_auto import challenge_bundle
        result = challenge_bundle(
            bundle_root,
            binder_id=ids.shelf_id,
            chapter_id=ids.book_id,
            dry_run=args.dry_run,
        )
        if result.get("skipped"):
            print(f"SKIPPED (already {result['stage']}): {bundle_root}")
        elif result.get("dry_run"):
            print(f"DRY-RUN challenge: {bundle_root}")
            for line in result.get("validator", []):
                print(f"  {line}")
        else:
            print(f"CHALLENGED [{result['verdict']}]: {bundle_root}")
            print(f"  validator: {result['validator_p0']} P0, {result['validator_p1']} P1")
            print(f"  cost:      ${result['cost_usd']:.4f}")
            print(f"  report:    {result['report_path']}")

    elif args.cmd == "seal":
        result = seal_stage(bundle_root, target_stage=args.stage)
        if result.get("skipped"):
            print(f"SKIPPED (already {args.stage}): {bundle_root}")


if __name__ == "__main__":
    main()
