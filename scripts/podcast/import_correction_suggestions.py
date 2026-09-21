#!/usr/bin/env python3
"""import_correction_suggestions.py -- the pipeline's own audit findings, as pre-filled corrections.

    python3 scripts/podcast/import_correction_suggestions.py <slug> [--dry-run]

Finding an error is the slow part of correcting a book; confirming one is fast.
The Arabic-verification audit already records, for `isaf-al-talib` alone, 126
findings, each with a chapter, an exact quote, a suggested wording, a certainty
and a page -- almost exactly a correction. This turns every still-`open` finding
into a `suggested` correction (origin `sweep`, raised by `pipeline`) so a
moderator confirms or dismisses it instead of hunting for it (design B1).

What is imported, and what deliberately is not:

  * Only `status == "open"` findings. The `applied` ones are already in the book;
    the dry-run report verifies that instead of trusting it.
  * A finding is SKIPPED, and listed with its reason, when its quote is not found
    EXACTLY ONCE in its chapter (never guessed), when the suggestion equals the
    quote, or when the "suggestion" is not replacement wording at all. The audit
    wrote some of its `suggested` fields as instructions to a person -- "Add
    translation.", "Delete the second block", "(uncertain) ...", "Probably: ..."
    -- and importing one as `proposed_text` would, on acceptance, REPLACE the
    quoted passage with that sentence. That is the one failure that matters here,
    so anything that reads as an instruction or carries an editorial note in
    brackets stays with the audit and is reported.
  * Idempotent: the id is `sweep-` plus a hash of slug + quote + suggestion, so a
    re-run inserts nothing already there.

CHAPTER MAPPING. A flag's `chapter` is the reading edition's printed chapter
number, which is also the `bk_index` in `book/book-toc.json`. The importer
resolves it through the toc title (identity) and falls back to the printed number,
and reports how many chapters the two agreed on so the mapping is proven per book
rather than assumed.

The database is local unless `--remote` AND `--i-understand-remote` are given.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_edits import anchor_key  # noqa: E402
from _correction_db import (  # noqa: E402
    D1,
    REMOTE_CONFIRM_FLAG,
    default_d1,
    event_insert,
    now_iso,
    refuse_remote_unless_confirmed,
    sql_str,
)
from _correction_packets import arabic_gate, has_arabic  # noqa: E402
from _correction_text import (  # noqa: E402
    BookChapter,
    block_texts,
    locate_reader,
    normalize_text,
    prefix_before,
    read_chapters,
)
from _paths import resolve_content  # noqa: E402

ACTOR = "pipeline"
ID_PREFIX = "sweep-"
CHUNK = 20

#: A `suggested` that opens with one of these is telling a person what to do, not
#: giving the wording. Case-insensitive, checked at the start after trimming.
_INSTRUCTION_RE = re.compile(
    r"^\s*(add|insert|delete|omit|drop|note|none\b|no change|either|probably|consider|confirm|verify|check|"
    r"remove|keep|replace|translate|\(|\.\.\.|…)",
    re.I,
)
#: A trailing bracketed note ("... (ambiguous)", "... (as ch.4 renders it)") is the
#: auditor talking to the reader, and would be printed into the book if accepted.
_TRAILING_NOTE_RE = re.compile(r"\s\([^)]*\)\s*$")


def kind_for(category: str | None, quote: str) -> str:
    """Correction kind for an audit category.

    The audit's own category wins where it names one the app knows (meaning,
    citation); anything Arabic-related -- the `bare-arabic` category, or a quote
    carrying Arabic script under no category -- is `arabic`; the rest is `other`.
    """
    c = (category or "").strip().lower()
    if c in ("meaning", "citation"):
        return c
    if "arabic" in c or has_arabic(quote):
        return "arabic"
    return "other"


def clean_suggestion(quote: str, suggested: str) -> str:
    """The suggestion with a wrapping pair of quote marks removed, when it added them.

    The audit often writes the wording inside straight quotes ('Observe mourning
    ...'); the quotes are its punctuation, not the book's. Stripped only when the
    quoted passage does not itself start with a quote mark.
    """
    s = suggested.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"" and quote.strip()[:1] != s[0]:
        s = s[1:-1].strip()
    # The audit writes its wording in running text, so it lowercases a suggestion that replaces the
    # START of a sentence or a list item ("Truthfulness in one's home" -> "truthfulness in every
    # situation"). Printed into the book that is a typo of its own. Carry the capital over when the
    # quote had one and the suggestion begins with a plain lowercase Latin letter.
    q = quote.strip()
    if q and s and q[0].isupper() and q[0].isascii() and s[0].islower() and s[0].isascii():
        s = s[0].upper() + s[1:]
    return s


def not_replacement_wording(suggested: str, quote: str) -> str | None:
    """Why a suggestion cannot be used as replacement text, or None if it can."""
    if _INSTRUCTION_RE.search(suggested):
        return "the suggestion is an instruction to a person, not replacement wording"
    if _TRAILING_NOTE_RE.search(suggested) and not _TRAILING_NOTE_RE.search(quote):
        return "the suggestion ends with an editorial note in brackets that would be printed into the book"
    return None


def correction_id(slug: str, quote: str, suggested: str) -> str:
    digest = hashlib.sha1(f"{slug}\0{quote}\0{suggested}".encode("utf-8")).hexdigest()
    return ID_PREFIX + digest[:16]


def load_flags(book_dir: Path) -> list[dict]:
    try:
        data = json.loads((book_dir / "_system" / "arabic-verify-flags.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def chapter_map(book_dir: Path, chapters: list[BookChapter]) -> tuple[dict[int, BookChapter], dict[str, Any]]:
    """Flag chapter number -> BookChapter, proven against `book-toc.json`.

    Returns the map plus a proof: how many toc entries resolved by title, how many
    of those agree with the printed number, and any that do not.
    """
    by_number = {c.number: c for c in chapters if c.number is not None}
    by_key = {c.key: c for c in chapters}
    mapping: dict[int, BookChapter] = dict(by_number)
    proof: dict[str, Any] = {"toc_entries": 0, "matched_by_title": 0, "agree_with_printed_number": 0, "disagree": []}
    try:
        toc = json.loads((book_dir / "book" / "book-toc.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        toc = {}
    for entry in toc.get("chapters", []) if isinstance(toc, dict) else []:
        idx = entry.get("bk_index")
        if not isinstance(idx, int):
            continue
        proof["toc_entries"] += 1
        ch = by_key.get(anchor_key(str(entry.get("title", ""))))
        if ch is None:
            continue
        proof["matched_by_title"] += 1
        if ch.number == idx:
            proof["agree_with_printed_number"] += 1
        else:
            proof["disagree"].append({"bk_index": idx, "printed": ch.number, "title": ch.heading})
        mapping[idx] = ch  # identity by title wins over the printed number
    return mapping, proof


def classify(
    flags: list[dict], slug: str, chapters_by_index: dict[int, BookChapter], all_chapters: list[BookChapter]
) -> dict[str, Any]:
    """Split flags into importable suggestions and skipped/informational lists."""
    importable: list[dict] = []
    skipped: list[dict] = []
    applied_check = {"claimed": 0, "absent_from_book": 0, "instruction_type": 0, "still_present": []}
    open_total = 0

    for f in flags:
        quote_raw = str(f.get("quote") or "")
        chapter = chapters_by_index.get(f.get("chapter"))
        status = f.get("status")

        if status == "applied":
            applied_check["claimed"] += 1
            present = any(locate_reader(c.body, quote_raw) for c in all_chapters)
            if not present:
                applied_check["absent_from_book"] += 1
            elif _INSTRUCTION_RE.search(str(f.get("suggested") or "")):
                # An "Add translation" fix leaves the quoted block in place by design.
                applied_check["instruction_type"] += 1
            else:
                applied_check["still_present"].append({"chapter": f.get("chapter"), "quote": quote_raw[:60]})
            continue
        if status != "open":
            continue
        open_total += 1

        def skip(reason: str) -> None:
            skipped.append(
                {"chapter": f.get("chapter"), "sev": f.get("sev"), "quote": quote_raw[:70], "reason": reason}
            )

        if chapter is None:
            skip(f"chapter {f.get('chapter')} is not in the book")
            continue
        quote = normalize_text(quote_raw)
        suggested = clean_suggestion(quote, str(f.get("suggested") or ""))
        if not suggested:
            skip("no suggested wording")
            continue
        if normalize_text(suggested) == quote:
            skip("the suggestion equals the quote")
            continue
        bad = not_replacement_wording(suggested, quote)
        if bad:
            skip(bad)
            continue
        # A suggestion the pipeline's own gate would refuse at review time is not worth
        # a moderator's attention: it would arrive as `suggested` and be rejected on sight.
        gate = arabic_gate(quote, suggested, kind_for(f.get("category"), quote))
        if gate and gate.result == "no":
            skip(f"the suggestion would be refused by the Arabic gate ({gate.note})")
            continue
        hits = locate_reader(chapter.body, quote)
        if not hits:
            skip("the quote is not in the chapter (the book has changed since the audit)")
            continue
        if len(hits) > 1:
            skip(f"the quote matches {len(hits)} places in the chapter -- ambiguous, not guessed")
            continue
        h = hits[0]
        text = block_texts(chapter.body)[h.block_index]
        page, sev = f.get("page"), f.get("sev")
        bits = ([f"page {page}"] if page else []) + ([f"severity {sev}"] if sev else [])
        importable.append(
            {
                "id": correction_id(slug, quote, suggested),
                "slug": slug,
                "anchor_key": chapter.key,
                "block_index": h.block_index,
                "start_offset": h.start,
                "end_offset": h.end,
                "quote": quote,
                "prefix": prefix_before(text, h.start),
                "proposed_text": suggested,
                "rationale": "Found by the Arabic verification audit" + (f" ({', '.join(bits)})." if bits else "."),
                "kind": kind_for(f.get("category"), quote),
                "certainty": f.get("certainty") if isinstance(f.get("certainty"), int) else None,
            }
        )
    return {"importable": importable, "skipped": skipped, "open_total": open_total, "applied_check": applied_check}


def insert_sql(s: dict, *, at: str) -> str:
    cols = (
        "id, slug, anchor_key, block_index, start_offset, end_offset, quote, prefix, proposed_text, rationale_html, "
        "kind, status, origin, certainty, batch_id, raised_by, raised_at, updated_at"
    )
    vals = (
        s["id"], s["slug"], s["anchor_key"], s["block_index"], s["start_offset"], s["end_offset"], s["quote"],
        s["prefix"], s["proposed_text"], s["rationale"], s["kind"], "suggested", "sweep", s["certainty"], None,
        ACTOR, at, at,
    )  # fmt: skip
    return f"INSERT OR IGNORE INTO correction ({cols}) VALUES ({', '.join(sql_str(v) for v in vals)})"


def existing_ids(d1: D1, ids: list[str], *, remote: bool) -> set[str]:
    if not ids:
        return set()
    out: set[str] = set()
    for i in range(0, len(ids), 200):
        listed = ", ".join(sql_str(x) for x in ids[i : i + 200])
        out |= {r["id"] for r in d1(f"SELECT id FROM correction WHERE id IN ({listed})", remote=remote)}
    return out


def run(book_dir: Path, slug: str, *, d1: D1 | None, dry_run: bool, remote: bool = False, out=print) -> dict:
    chapters = read_chapters(book_dir)
    mapping, proof = chapter_map(book_dir, chapters)
    result = classify(load_flags(book_dir), slug, mapping, chapters)
    importable = result["importable"]

    already: set[str] = set()
    if d1 is not None:
        already = existing_ids(d1, [s["id"] for s in importable], remote=remote)
    fresh = [s for s in importable if s["id"] not in already]
    result.update(mapping_proof=proof, already_present=len(already), to_insert=len(fresh), dry_run=dry_run)

    if not dry_run and d1 is not None and fresh:
        at = now_iso()
        stmts = [insert_sql(s, at=at) for s in fresh]
        for i in range(0, len(stmts), CHUNK):
            d1(";\n".join(stmts[i : i + CHUNK]), remote=remote)
        d1(
            event_insert(
                at=at,
                actor=ACTOR,
                action="import-suggestions",
                subject=slug,
                scope_id=slug,
                detail=f"imported {len(fresh)}",
            ),
            remote=remote,
        )

    ac = result["applied_check"]
    out(
        f"chapter mapping: {proof['matched_by_title']}/{proof['toc_entries']} toc entries matched a heading by title; "
        f"{proof['agree_with_printed_number']} agree with the printed number, {len(proof['disagree'])} disagree"
    )
    out(
        f"open findings: {result['open_total']}  ->  importable {len(importable)}, skipped {len(result['skipped'])}"
        f"  ({result['already_present']} already imported, {len(fresh)} {'would be inserted' if dry_run else 'inserted'})"
    )
    out(
        f"'applied' findings: {ac['claimed']} claimed applied; {ac['absent_from_book']} quote absent from the book, "
        f"{ac['instruction_type']} are add-a-translation fixes that keep the quoted block, {len(ac['still_present'])} still present"
    )
    reasons: dict[str, int] = {}
    for s in result["skipped"]:
        reasons[s["reason"]] = reasons.get(s["reason"], 0) + 1
    for reason, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        out(f"  skipped {n:>3}: {reason}")
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--dry-run", action="store_true", help="report only; touches no database (reads none either)")
    ap.add_argument("--remote", action="store_true", help="the DEPLOYED database (needs " + REMOTE_CONFIRM_FLAG + ")")
    ap.add_argument(REMOTE_CONFIRM_FLAG, dest="confirmed", action="store_true")
    args = ap.parse_args(argv)

    refusal = refuse_remote_unless_confirmed(args.remote, args.confirmed)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    book_dir = resolve_content(args.slug)
    if not (book_dir / "book" / "book.md").exists():
        print(f"no reading edition for: {args.slug}", file=sys.stderr)
        return 2
    run(book_dir, args.slug, d1=None if args.dry_run else default_d1(), dry_run=args.dry_run, remote=args.remote)
    return 0


if __name__ == "__main__":
    sys.exit(main())
