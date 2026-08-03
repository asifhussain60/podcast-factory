#!/usr/bin/env python3
"""Move a Composer-authored front-matter section into chapter 1, once.

WHY THIS EXISTS
---------------
From 2026-08-03 a book's opening is folded into its first numbered chapter at
assembly time (``_translation_edition``), so no edition begins with a preface.
That fold is refused for one shape, and refused deliberately: a book whose
front-matter section carries a **Composer edit**.

The reason is ordering. The assembly folds; the Composer replay then rewrites
every edited chapter from ``_system/composer-edits.json`` a step later. If
chapter 1 is itself edited, the replay restores the author's chapter and the
folded opening goes with it — and nothing reports the loss, because
``apply_composer_edits`` only reports an edit whose HEADING is gone, not prose
that vanished from a chapter it found.

So the sidecar is migrated instead: the human's front-matter body is merged into
the human's chapter-1 body, in the sidecar, and the front-matter edit is deleted.
After that there is exactly one place holding each piece of prose, and the book
takes ``preface.include: false`` because its opening now lives inside chapter 1.

WHAT IT DOES, EXACTLY
---------------------
1. Reads ``_system/composer-edits.json``.
2. Strips the retired machine preface (the ``edition-intro`` fence) from the
   front-matter body — that text is the pipeline's, not the author's, and it is
   what this whole change is removing.
3. Prepends what remains to the chapter body, separated by a blank line.
4. Deletes the front-matter edit and rewrites the sidecar atomically.
5. Sets ``preface.include: false`` in ``book/book-toc.json`` unless
   ``--keep-toc-preface``, so the assembly does not re-emit the opening a second
   time beside the copy now inside chapter 1.

Refuses rather than guesses: an absent front-matter edit, an absent chapter edit,
or an already-merged body each stop the run with a message. ``--dry-run`` prints
the plan and writes nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_edits import anchor_key, load_edits, sidecar_path  # noqa: E402
from _book_frontmatter import strip_introduction  # noqa: E402


def plan_fold(book_dir: Path, preface_title: str, chapter_title: str) -> dict:
    """Everything the migration would do, computed without writing anything."""
    book_dir = Path(book_dir).resolve()
    pf_key, ch_key = anchor_key(preface_title), anchor_key(chapter_title)
    data = load_edits(book_dir, strict=True)
    edits = {str(e.get("chapter_key")): e for e in data["edits"] if e.get("chapter_key")}

    if pf_key not in edits:
        raise SystemExit(f"no Composer edit keyed {pf_key!r} in {sidecar_path(book_dir)} — nothing to migrate")
    if ch_key not in edits:
        raise SystemExit(
            f"no Composer edit keyed {ch_key!r}. The fold only needs migrating when BOTH sections are "
            "authored; if chapter 1 is not, drop this book's preface entry and let the assembly fold it."
        )

    pf_body = strip_introduction(str(edits[pf_key].get("body_md") or "")).strip()
    ch_body = str(edits[ch_key].get("body_md") or "").strip()
    if not pf_body:
        raise SystemExit(f"{pf_key!r} holds nothing but a machine preface — delete the edit rather than folding it")
    if pf_body[:400] in ch_body:
        raise SystemExit(f"{ch_key!r} already opens on this text — the migration has already run")

    return {
        "book_dir": str(book_dir),
        "preface_key": pf_key,
        "chapter_key": ch_key,
        "preface_words": len(pf_body.split()),
        "chapter_words": len(ch_body.split()),
        "merged_words": len((pf_body + " " + ch_body).split()),
        "merged_body": pf_body + "\n\n" + ch_body,
        "data": data,
    }


def apply_fold(plan: dict, *, keep_toc_preface: bool = False, log=print) -> None:
    """Write the merged sidecar and, unless told otherwise, drop the toc entry."""
    from _book_edits import _write_json_atomic

    book_dir = Path(plan["book_dir"])
    data = plan["data"]
    kept = []
    for e in data["edits"]:
        key = str(e.get("chapter_key") or "")
        if key == plan["preface_key"]:
            continue
        if key == plan["chapter_key"]:
            e = {**e, "body_md": plan["merged_body"]}
        kept.append(e)
    data["edits"] = kept
    _write_json_atomic(sidecar_path(book_dir), data)
    log(
        f"    sidecar: {plan['preface_key']!r} ({plan['preface_words']} words) merged into "
        f"{plan['chapter_key']!r} — now {plan['merged_words']} words; front-matter edit deleted"
    )

    if keep_toc_preface:
        return
    toc_path = book_dir / "book" / "book-toc.json"
    toc = json.loads(toc_path.read_text(encoding="utf-8"))
    preface = toc.get("preface")
    if isinstance(preface, dict) and preface.get("include"):
        preface["include"] = False
        toc_path.write_text(json.dumps(toc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        log("    book-toc.json: preface.include -> false (its text now lives inside chapter 1)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book_dir", type=Path)
    ap.add_argument("--preface-title", required=True, help="heading of the front-matter section, as it appears")
    ap.add_argument("--chapter-title", required=True, help="heading of chapter 1, without its number")
    ap.add_argument("--keep-toc-preface", action="store_true", help="leave book-toc.json alone")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    plan = plan_fold(args.book_dir, args.preface_title, args.chapter_title)
    print(
        f"{plan['preface_key']!r} ({plan['preface_words']} words) -> {plan['chapter_key']!r} "
        f"({plan['chapter_words']} words) = {plan['merged_words']} words"
    )
    if args.dry_run:
        print("--- merged body, first 600 chars ---")
        print(plan["merged_body"][:600])
        print("--- dry run: nothing written ---")
        return 0
    apply_fold(plan, keep_toc_preface=args.keep_toc_preface)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
