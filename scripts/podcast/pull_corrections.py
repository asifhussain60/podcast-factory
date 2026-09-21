#!/usr/bin/env python3
"""pull_corrections.py -- the round trip: accepted corrections back into the book.

    python3 scripts/podcast/pull_corrections.py <slug> [--apply]

DRY-RUN BY DEFAULT. Without `--apply` it changes nothing and prints, per chapter,
the unified diff of exactly what would change: the republish preview (design
B11). With `--apply` it writes through `_book_edits.write_chapter_body` -- the
Book Composer's own edit path, and the only sanctioned way a chapter's prose
changes -- so each change is also recorded in `_system/composer-edits.json` and
survives a re-compose. The Library only CAPTURES corrections; it never applies
them (design section 1).

For each `accepted` correction it demands, and reports rather than guesses:

  * the chapter exists and the quote occurs EXACTLY ONCE in it -- otherwise
    `orphaned` (missing, ambiguous, or spanning formatting the script cannot
    splice through);
  * no other accepted correction touches the same passage -- otherwise both are
    `overlapping` and NEITHER is applied, because each was accepted against text
    the other would change;
  * a Qur'anic letter change is refused outright (a person decides those);
  * an Arabic change is marks-only (`_vowelling.rejection_reason`);
  * the narrative-frame gates (`revoice_gates`) pass on the changed paragraph;
  * a spoken-lane book (Sessions / Audiobook) keeps >= 90% of a chapter's words,
    because its prose is timed against a recording.

Then, after `--apply`, each applied correction is stamped `applied` in the LOCAL
Library database, a `correction_applied` row is written so readers' highlights
can follow the changed wording, and an `access_event` records it.

Also reported (never edited): a SYSTEMIC DETECTOR -- three or more corrections of
the same shape are one pipeline defect, not three fixes, and go to the findings
ledger (on `--apply`) -- and GLOSSARY CANDIDATES for repeated term fixes.

The database is local unless `--remote` AND `--i-understand-remote` are given.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _book_edits  # noqa: E402
from _correction_db import (  # noqa: E402
    D1,
    REMOTE_CONFIRM_FLAG,
    default_d1,
    event_insert,
    fetch_corrections,
    now_iso,
    refuse_remote_unless_confirmed,
    sql_str,
)
from _correction_packets import (  # noqa: E402
    BookContext,
    Gate,
    arabic_gate,
    frame_gate,
    load_context,
    quran_gate,
    retention_gate,
)
from _correction_text import (  # noqa: E402
    BookChapter,
    block_span,
    duplicate_keys,
    find_chapter,
    locate_reader,
    locate_source,
    normalize_text,
    spans_overlap,
    substitute,
)
from _paths import REPO_ROOT, resolve_content  # noqa: E402

ACTOR = "pipeline"
CLUSTER_MIN = 3
GLOSSARY_MIN_OCCURRENCES = 2
CHECK_ID = "CR-SYSTEMIC"
SOURCE = "pull_corrections"
SOURCE_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


@dataclass
class Item:
    correction: dict
    chapter: BookChapter | None = None
    span: tuple[int, int] | None = None
    state: str = "ready"  # ready | orphaned | overlapping | refused
    reasons: list[str] = field(default_factory=list)
    gates: list[Gate] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.correction["id"]

    def block(self, why: str, state: str) -> None:
        self.state = state
        self.reasons.append(why)


def _resolve(ctx: BookContext, c: dict, dup: set[str]) -> Item:
    item = Item(correction=c)
    quote, proposed = str(c["quote"]), str(c["proposed_text"])
    chapter = find_chapter(ctx.chapters, str(c["anchor_key"]))
    if chapter is None:
        item.block("the chapter is no longer in the book", "orphaned")
        return item
    if chapter.key in dup:
        item.block("two chapters share this heading, so the target is ambiguous", "orphaned")
        return item
    item.chapter = chapter
    if normalize_text(quote) == normalize_text(proposed):
        item.block("the proposed text equals the quote; nothing to apply", "refused")
        return item
    src, reader = locate_source(chapter.body, quote), locate_reader(chapter.body, quote)
    if len(src) == 1 and len(reader) == 1:
        item.span = src[0]
    elif not src and reader:
        item.block(
            "the quote spans formatting (bold, italics or a link) in the source text, so it cannot be spliced safely; make this edit in the Book Composer",
            "orphaned",
        )
    elif not src and not reader:
        item.block(
            "the quote is not in the chapter (it may already be changed, or the chapter was re-composed)", "orphaned"
        )
    else:
        item.block(f"the quote matches {max(len(src), len(reader))} places -- ambiguous, so not guessed", "orphaned")
    return item


def plan(ctx: BookContext, accepted: list[dict]) -> tuple[list[Item], dict[str, dict]]:
    """Classify every accepted correction; return (items, per-chapter change set).

    The change set holds only chapters where at least one correction is `ready`
    after every refusal has been applied, with the rebuilt body and the diff.
    """
    dup = duplicate_keys(ctx.chapters)
    items = [_resolve(ctx, c, dup) for c in accepted]

    # Overlap: any two live spans in one chapter that touch. Both are withheld.
    by_chapter: dict[str, list[Item]] = defaultdict(list)
    for it in items:
        if it.state == "ready" and it.chapter and it.span:
            by_chapter[it.chapter.key].append(it)
    for group in by_chapter.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if spans_overlap(a.span, b.span):  # type: ignore[arg-type]
                    for x, y in ((a, b), (b, a)):
                        x.block(f"overlaps accepted correction {y.id}; neither is applied", "overlapping")

    frame = ctx.rules.get("narrative_frame")
    subject = ctx.rules.get("narrator_subject", "")

    # Per-item script gates, then one frame gate per changed paragraph (combined result).
    for it in items:
        if it.state != "ready":
            continue
        quote, proposed, kind = (
            str(it.correction["quote"]),
            str(it.correction["proposed_text"]),
            str(it.correction["kind"]),
        )
        for g in (quran_gate(quote, proposed), arabic_gate(quote, proposed, kind)):
            if g:
                it.gates.append(g)
                if g.result == "no":
                    it.block(f"{g.id}: {g.note}", "refused")

    paragraphs: dict[tuple[str, int], list[Item]] = defaultdict(list)
    for it in items:
        if it.state == "ready":
            paragraphs[(it.chapter.key, block_span(it.chapter.body, *it.span)[0])].append(it)  # type: ignore[union-attr]
    for group in paragraphs.values():
        ch = group[0].chapter
        lo, hi = block_span(ch.body, *group[0].span)  # type: ignore[union-attr,arg-type]
        old_para = ch.body[lo:hi]
        edits = [(it.span[0] - lo, it.span[1] - lo, str(it.correction["proposed_text"])) for it in group]  # type: ignore[index]
        g = frame_gate(old_para, substitute(old_para, edits), frame=frame, narrator_subject=subject)
        for it in group:
            it.gates.append(g)
            if g.result == "no":
                it.block(f"{g.id}: {g.note}", "refused")

    changes: dict[str, dict] = {}
    for key, group in by_chapter.items():
        ready = [it for it in group if it.state == "ready"]
        if not ready:
            continue
        ch = ready[0].chapter
        new_body = substitute(ch.body, [(it.span[0], it.span[1], str(it.correction["proposed_text"])) for it in ready])  # type: ignore[index,union-attr]
        if ctx.spoken:
            g = retention_gate(ch.body, new_body)
            for it in ready:
                it.gates.append(g)
                if g.result == "no":
                    it.block(f"{g.id}: {g.note}", "refused")
            ready = [it for it in ready if it.state == "ready"]
            if not ready:
                continue
            new_body = substitute(
                ch.body, [(it.span[0], it.span[1], str(it.correction["proposed_text"])) for it in ready]
            )  # type: ignore[index]
        changes[key] = {"chapter": ch, "new_body": new_body, "items": ready}
    return items, changes


def chapter_diff(chapter: BookChapter, new_body: str) -> str:
    return "".join(
        difflib.unified_diff(
            (chapter.body + "\n").splitlines(keepends=True),
            (new_body + "\n").splitlines(keepends=True),
            fromfile=f"book.md [{chapter.heading}] (current)",
            tofile=f"book.md [{chapter.heading}] (corrected)",
            n=1,
        )
    )


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


def applied_sql(c: dict, slug: str, *, at: str) -> str:
    """Stamp one correction applied, audit it, and record the substitution.

    Statement order matters: the event uses `WHERE changes() > 0`, which reports
    the UPDATE immediately before it, so nothing may sit between them. The
    `correction_applied` row is written regardless of whether the UPDATE matched
    (the correction may have been dismissed a moment ago): the prose has changed
    on disk either way, and readers' marks have to be able to follow it.
    """
    return ";\n".join(
        [
            f"UPDATE correction SET status = 'applied', applied_at = {sql_str(at)}, updated_at = {sql_str(at)} "
            f"WHERE id = {sql_str(c['id'])} AND slug = {sql_str(slug)} AND status = 'accepted' AND deleted_at IS NULL",
            event_insert(
                at=at, actor=ACTOR, action="apply-correction", subject=slug, scope_id=c["id"], only_if_changed=True
            ),
            "INSERT OR REPLACE INTO correction_applied (slug, anchor_key, old_text, new_text, applied_at) VALUES ("
            + ", ".join(sql_str(v) for v in (slug, c["anchor_key"], c["quote"], c["proposed_text"], at))
            + ")",
        ]
    )


# ---------------------------------------------------------------------------
# Systemic detector and glossary candidates (report-only)
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[\w'’\-]+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def word_changes(quote: str, proposed: str) -> list[tuple[str, str]]:
    """The (old, new) word-level replacements that turn `quote` into `proposed`."""
    a, b = _tokens(quote), _tokens(proposed)
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            out.append((" ".join(a[i1:i2]), " ".join(b[j1:j2])))
    return out


def shape_of(c: dict) -> tuple[str, str] | None:
    """A correction's normalized (kind, "old -> new") shape, or None if it has no word-level change."""
    ch = word_changes(str(c["quote"]), str(c["proposed_text"]))
    if not ch:
        return None
    return str(c["kind"]), " | ".join(f"{o or '(nothing)'} -> {n or '(nothing)'}" for o, n in ch)


def systemic_clusters(corrections: list[dict], minimum: int = CLUSTER_MIN) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for c in corrections:
        s = shape_of(c)
        if s:
            groups[s].append(c)
    return [
        {"kind": k, "shape": sh, "count": len(cs), "ids": [c["id"] for c in cs]}
        for (k, sh), cs in sorted(groups.items(), key=lambda kv: -len(kv[1]))
        if len(cs) >= minimum
    ]


#: Words that carry no term-hood however often they recur. A citation or meaning
#: fix that swaps one of these ("of" -> "for") is a rewrite of a sentence, not a
#: term with a settled rendering.
_STOPWORDS = frozenset(
    "a an the of and or but in on at to for from by with as is are was were be been it its this that these those he she they "
    "we you i his her their our your not no if then than so who whom which what when where whoever whatever unless until "
    "sit say said says do does did has have had will would shall should may might can could".split()
)
#: A term is short. Longer quotes are sentences, and diffing a sentence rewrite
#: word by word produces pairs that mean nothing on their own.
GLOSSARY_MAX_QUOTE_WORDS = 8
GLOSSARY_MIN_TERM_CHARS = 4


def glossary_candidates(corrections: list[dict], book_md: str) -> list[dict]:
    """Term -> correct-rendering pairs from citation/meaning fixes whose replaced
    token still recurs in the book. Reported for a person; `glossary.yml` is never edited.

    Only SMALL, single-change corrections qualify, and never a stop-word: measured
    on a real book, the unfiltered version ranked "of -> for each" (4,378 hits)
    above every real term.
    """
    lower = book_md.lower()
    out: dict[tuple[str, str], dict] = {}
    for c in corrections:
        if c["kind"] not in ("citation", "meaning"):
            continue
        if len(_tokens(str(c["quote"]))) > GLOSSARY_MAX_QUOTE_WORDS:
            continue
        changes = word_changes(str(c["quote"]), str(c["proposed_text"]))
        if len(changes) != 1:
            continue
        old, new = changes[0]
        words = old.split()
        if (
            not old
            or not new
            or len(words) > 3
            or len(old) < GLOSSARY_MIN_TERM_CHARS
            or all(w in _STOPWORDS for w in words)
        ):
            continue
        n = len(re.findall(rf"(?<!\w){re.escape(old)}(?!\w)", lower))
        if n >= GLOSSARY_MIN_OCCURRENCES:
            e = out.setdefault(
                (old, new), {"term": old, "rendering": new, "kind": c["kind"], "occurrences_in_book": n, "ids": []}
            )
            e["ids"].append(c["id"])
    return sorted(out.values(), key=lambda e: -e["occurrences_in_book"])


def ledger_has(repo_root: Path, book: str, signature: str) -> bool:
    ledger = repo_root / "_learning" / "findings.jsonl"
    if not ledger.exists():
        return False
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except ValueError as exc:
            # A damaged ledger line is skipped, but said aloud: staying silent would let a corrupted
            # ledger quietly re-report a cluster that was already recorded.
            print(f"  ! findings ledger: skipped an unreadable line ({exc})", file=sys.stderr)
            continue
        if rec.get("source") == SOURCE and rec.get("book") == book and rec.get("signature") == signature:
            return True
    return False


def record_clusters(clusters: list[dict], book: str, *, repo_root: Path = REPO_ROOT) -> list[str]:
    """Append ONE finding per cluster to the ledger; returns the signatures newly written."""
    from _rules import emit_finding

    written: list[str] = []
    for cl in clusters:
        signature = f"{CHECK_ID}:{cl['kind']}:{cl['shape']}"
        if ledger_has(repo_root, book, signature):
            continue
        emit_finding(
            repo_root=repo_root,
            source=SOURCE,
            source_version=SOURCE_VERSION,
            book=book,
            check_id=CHECK_ID,
            severity="P1",
            signature=signature,
            context_excerpt=f"{cl['count']} corrections make the same {cl['kind']} change ({cl['shape']}); ids {', '.join(cl['ids'][:4])}",
        )
        written.append(signature)
    return written


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def follow_ups(slug: str, ctx: BookContext, applied: list[Item]) -> dict[str, Any]:
    spoken_or_narrated = ctx.spoken or (ctx.book_dir / "book" / "narration").is_dir()
    lane = []
    for it in applied:
        hit = [
            name
            for name, text in ctx.lane_text.items()
            if normalize_text(str(it.correction["quote"])).lower() in text.lower()
        ]
        if hit:
            lane.append({"id": it.id, "files": hit})
    return {
        "publish": f"python3 scripts/podcast/publish_to_listener.py {slug}",
        "read_along": (
            f"python3 scripts/podcast/generate_reader_narration.py {slug}   "
            "(re-records only the changed paragraphs; Azure speech spend -- run it on purpose)"
            if spoken_or_narrated and applied
            else None
        ),
        "read_along_chapters": [
            ch.heading for ch in ctx.chapters if any(it.chapter and it.chapter.heading == ch.heading for it in applied)
        ]
        if spoken_or_narrated
        else [],
        "podcast_lane_still_old": lane,
    }


def run(
    book_dir: Path,
    slug: str,
    *,
    d1: D1,
    apply: bool = False,
    remote: bool = False,
    repo_root: Path = REPO_ROOT,
    out=print,
) -> dict:
    accepted = fetch_corrections(d1, slug, ("accepted",), remote=remote)
    everything = fetch_corrections(d1, slug, ("suggested", "open", "accepted", "applied"), remote=remote)
    ctx = load_context(book_dir, slug)
    items, changes = plan(ctx, accepted)
    ready = [it for ch in changes.values() for it in ch["items"]]

    report: dict[str, Any] = {
        "accepted": len(accepted),
        "ready": [it.id for it in ready],
        "orphaned": [(it.id, it.reasons) for it in items if it.state == "orphaned"],
        "overlapping": [(it.id, it.reasons) for it in items if it.state == "overlapping"],
        "refused": [(it.id, it.reasons) for it in items if it.state == "refused"],
        "applied": [],
        "apply": apply,
    }

    out(
        f"{len(accepted)} accepted correction(s): {len(ready)} ready, {len(report['orphaned'])} orphaned, "
        f"{len(report['overlapping'])} overlapping, {len(report['refused'])} refused"
    )
    for label in ("orphaned", "overlapping", "refused"):
        for cid, why in report[label]:
            out(f"  {label.upper():<12} {cid}: {'; '.join(why)}")

    for change in changes.values():
        ch: BookChapter = change["chapter"]
        out(f"\n=== {ch.heading}  ({len(change['items'])} correction(s)) ===")
        out(chapter_diff(ch, change["new_body"]).rstrip() or "(no textual change)")

    failed_sql: list[str] = []
    if apply:
        at = now_iso()
        for change in changes.values():
            ch = change["chapter"]
            _book_edits.write_chapter_body(book_dir, ch.heading, change["new_body"])
            for it in change["items"]:
                sql = applied_sql(it.correction, slug, at=at)
                try:
                    d1(sql, remote=remote)
                    report["applied"].append(it.id)
                except Exception as exc:  # the book is already changed; say exactly how to finish
                    failed_sql.append(sql)
                    out(f"  DATABASE WRITE FAILED for {it.id}: {exc}")
        if failed_sql:
            out("\nThe book was changed but these statements did not run. Run them against the same database:")
            out(";\n".join(failed_sql))
        applied_items = [it for it in ready if it.id in report["applied"] or failed_sql]
        report["follow_ups"] = follow_ups(slug, ctx, applied_items)
        out("\nNext steps:")
        out("  Compose is NOT needed -- the change is recorded as a Composer edit and survives a re-compose.")
        out(f"  Send the corrected prose to the Library:  {report['follow_ups']['publish']}")
        if report["follow_ups"]["read_along"]:
            out(f"  Read-along timing needs re-sync for: {', '.join(report['follow_ups']['read_along_chapters'])}")
            out(f"    {report['follow_ups']['read_along']}")
        for entry in report["follow_ups"]["podcast_lane_still_old"]:
            out(f"  The podcast/audio text still carries the OLD wording ({entry['id']}): {', '.join(entry['files'])}")
    else:
        out("\nDRY RUN -- nothing was written. Re-run with --apply to make these changes.")
        preview = follow_ups(slug, ctx, ready)
        for entry in preview["podcast_lane_still_old"]:
            out(
                f"  Note: the podcast/audio text also carries the old wording ({entry['id']}): {', '.join(entry['files'])}"
            )
        if preview["read_along_chapters"] and ready:
            out(f"  Note: read-along timing would need re-sync for: {', '.join(preview['read_along_chapters'])}")

    clusters = systemic_clusters([c for c in everything])
    report["systemic"] = clusters
    for cl in clusters:
        out(f"\nSYSTEMIC ({cl['count']}x, {cl['kind']}): {cl['shape']}  -- ids: {', '.join(cl['ids'][:6])}")
        out("  Three or more of the same fix is a pipeline defect, not three fixes.")
    if clusters:
        if apply:
            written = record_clusters(clusters, slug, repo_root=repo_root)
            report["ledger_written"] = written
            out(f"  {len(written)} finding(s) appended to the findings ledger ({CHECK_ID}).")
        else:
            out(f"  (dry run: {len(clusters)} finding(s) would be appended to the ledger on --apply)")

    book_md = (
        (book_dir / "book" / "book.md").read_text(encoding="utf-8") if (book_dir / "book" / "book.md").exists() else ""
    )
    cands = glossary_candidates(everything, book_md)
    report["glossary_candidates"] = cands
    if cands:
        out("\nGLOSSARY CANDIDATES (not applied -- glossary.yml is never edited here):")
        for e in cands:
            out(f"  {e['term']} -> {e['rendering']}   ({e['kind']}, {e['occurrences_in_book']}x still in the book)")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--apply", action="store_true", help="write the changes (default is a dry-run diff)")
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
    report = run(book_dir, args.slug, d1=default_d1(), apply=args.apply, remote=args.remote)
    return 0 if not (args.apply and report["accepted"] and not report["applied"] and report["ready"]) else 1


if __name__ == "__main__":
    sys.exit(main())
