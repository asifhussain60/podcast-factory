"""Fill the content tables the pipeline designed and never wrote to.

WHAT WAS WRONG. `book_metadata`, `chapters` and `episodes` have been in
`knowledge.db` since the early migrations. On 2026-08-31 all three held zero
rows, and nine of the ten content tables had no writer anywhere in the repo:
the only thing hydrating that database was the atoms side (Qur'an, hadith,
doctrine). So there was no way to ask a question across books — "which sessions
teach about ostentation", "where else is this hadith taught" — without grepping
the tree, and nothing downstream could either.

WHAT THIS DOES. Walks every book in every bucket through the same resolver the
rest of the pipeline uses (`_paths.listing`), and upserts:

    book_metadata   one row per book: title, shelf, profile, phase, meta.yml
    chapters        one row per chapter file, with its text and word count
    episodes        one row per episode framing, with its build status

then rebuilds `chapters_fts` so the text is searchable across everything at
once, Arabic included (the index folds tashkeel — see migration 032).

IT ONLY READS `content/`. Every write lands in `knowledge.db`. That is what
makes it safe to run while a pipeline run is in flight: it cannot touch the
files a phase is writing, and SQLite's WAL mode plus a busy timeout let it share
the database with a run that is appending atoms.

IDEMPOTENT, and incremental by default. A book whose files have not changed
since its last hydration is skipped — the fingerprint is content, never mtimes,
so a `git checkout` that rewrites timestamps does not force a full re-read.
`--force` re-reads everything.

LOGGING IS THE POINT, not a side effect. Asif, 2026-08-31: "Ensure every action
spits out a log entry somewhere that you can track." Every book, every table,
every skip and every failure is written to `content/knowledge-base/_index/
hydration-log.jsonl` — one JSON object per line, with counts and timings — and
the run's summary is recorded in `run_telemetry`. A book that fails is logged
and the walk continues: one unreadable book must not cost the other twenty
their index.

Usage:
    python3 scripts/podcast/hydrate_search_index.py                # all books
    python3 scripts/podcast/hydrate_search_index.py <slug> [<slug>...]
    python3 scripts/podcast/hydrate_search_index.py --force        # re-read all
    python3 scripts/podcast/hydrate_search_index.py --dry-run      # read, report
    python3 scripts/podcast/hydrate_search_index.py --search "ostentation"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _paths  # noqa: E402
from _arabic_coverage import ARABIC_BODY, normalize_arabic  # noqa: E402
from _db import get_connection, run_migrations  # noqa: E402

#: One Arabic run. Built from `_arabic_coverage.ARABIC_BODY` rather than a range
#: of its own: this repo keeps ONE definition of what "Arabic" means, and a
#: ratchet test fails any module that respells it — which this one did, and was
#: caught by, on 2026-08-31.
#:
#: Folded per-run rather than over the whole text because `normalize_arabic`
#: returns a bare skeleton with no spaces: right for comparing two spans, wrong
#: for a tokenized index, which needs the word boundaries and the surrounding
#: English left alone.
_ARABIC_RUN = re.compile(f"[{ARABIC_BODY}]+")


def searchable(text: str) -> str:
    """The text with its Arabic folded to consonantal skeletons.

    What makes an unvowelled query find vowelled prose. English is untouched, so
    one column serves both and a bilingual chapter is searchable in either.
    """
    if not text:
        return ""
    return _ARABIC_RUN.sub(lambda m: normalize_arabic(m.group()) or m.group(), text)


LOG_PATH = _paths.CONTENT_ROOT / "knowledge-base" / "_index" / "hydration-log.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(event: str, **fields: Any) -> dict:
    """One JSONL line per action. Never raises — a diagnostic that can break the
    thing it is diagnosing is worse than no diagnostic."""
    rec = {"at": _now(), "event": event, **fields}
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return rec


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def _yaml(p: Path) -> dict:
    if not p.is_file():
        return {}
    try:
        import yaml

        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _json(p: Path) -> dict:
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def fingerprint(book_dir: Path) -> str:
    """A hash of what this hydrator actually reads.

    CONTENT, never mtimes: a `git checkout` rewrites every timestamp in the
    tree, and an index that re-read twenty books because of that would be
    useless as an incremental step. Names are included as well as bytes, so a
    renamed chapter counts as a change even when its text is identical.
    """
    h = hashlib.sha256()
    for rel in ("meta.yml", "_system/series-config.yaml", "_system/orchestrator-state.json", "book/book.md"):
        h.update(rel.encode())
        h.update(_read(book_dir / rel).encode())
    for sub in ("chapters", "episodes"):
        d = book_dir / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.txt")):
            h.update(f.name.encode())
            h.update(_read(f).encode())
    return h.hexdigest()[:16]


def _book_md_rows(book_dir: Path, slug: str, phase: str) -> list[tuple]:
    """Chapters read from the composed reading edition, split on its `##` headings.

    THE SESSIONS LANE HAS NO `chapters/` DIRECTORY. Its books are composed
    straight into `book/book.md` — `sessions/ingest.py` says so outright ("the
    output is an ordinary book folder") and never writes the per-episode chapter
    files the podcast route produces. Indexing only `chapters/*.txt` therefore
    missed Love Of The Prophet and Surah Al-Fateha entirely: 146,000 words of the
    very sessions this index exists to make searchable, plus a translation
    edition that composes the same way.

    The `##` headings ARE the chapters — that is the structure
    `_book_frontmatter` and the Composer both write and read. The `#` title and
    anything before the first `##` (the introduction front matter) is deliberately
    not a chapter.
    """
    md = book_dir / "book" / "book.md"
    text = _read(md)
    if not text.strip():
        return []
    parts = re.split(r"^##\s+(.+?)\s*$", text, flags=re.M)
    rows = []
    # re.split with one group yields [preamble, title, body, title, body, ...].
    for i in range(1, len(parts) - 1, 2):
        title, body = parts[i].strip(), parts[i + 1].strip()
        if not body:
            continue
        n = len(rows) + 1
        rows.append(
            (f"{slug}/ch{n:02d}", slug, f"ch{n:02d}", title, None, body, len(body.split()), phase, searchable(body))
        )
    return rows


def _chapter_rows(book_dir: Path, slug: str, phase: str) -> list[tuple]:
    rows = []
    d = book_dir / "chapters"
    if not d.is_dir():
        return _book_md_rows(book_dir, slug, phase)
    for f in sorted(d.glob("*.txt")):
        stem = f.stem
        chapter_id = stem.split("-", 1)[0] if "-" in stem else stem
        # The title lives in the chapter's contract when there is one — that is
        # where the SOURCE's own chapter name is kept (`title:`), as opposed to
        # the file's slug, which for some books is a theme the pipeline chose.
        contract = _yaml(book_dir / "chapter-contracts" / f"{stem.split('-', 1)[-1]}.yml")
        text = _read(f)
        rows.append(
            (
                f"{slug}/{chapter_id}",
                slug,
                chapter_id,
                (contract.get("title") or stem.split("-", 1)[-1].replace("-", " ").title()),
                None,
                text,
                len(text.split()),
                phase,
                searchable(text),
            )
        )
    return rows or _book_md_rows(book_dir, slug, phase)


def _episode_rows(book_dir: Path, slug: str) -> list[tuple]:
    rows = []
    d = book_dir / "episodes"
    if not d.is_dir():
        return rows
    for f in sorted(d.glob("*.txt")):
        digits = "".join(c for c in f.stem if c.isdigit())
        if not digits:
            continue
        rows.append((f"{slug}/ep{digits}", slug, int(digits), None, f.stem, _read(f), str(f), "built"))
    return rows


def hydrate_book(conn, ref, *, force: bool = False, dry_run: bool = False) -> dict:
    """Upsert one book. Returns a report dict; never raises for one bad book."""
    started = time.time()
    slug, book_dir = ref.slug, Path(ref.dir)
    try:
        fp = fingerprint(book_dir)
        prev = conn.execute("SELECT meta_yml FROM book_metadata WHERE slug = ?", (slug,)).fetchone()
        prev_fp = None
        if prev and prev[0]:
            try:
                prev_fp = (json.loads(prev[0]) or {}).get("_fingerprint")
            except Exception:
                prev_fp = None
        if prev_fp == fp and not force:
            return _log("book.skipped", slug=slug, reason="unchanged", fingerprint=fp)

        meta = _yaml(book_dir / "meta.yml")
        cfg = _yaml(book_dir / "_system" / "series-config.yaml")
        state = _json(book_dir / "_system" / "orchestrator-state.json")
        phase = str(state.get("phase") or "")
        chapters = _chapter_rows(book_dir, slug, phase)
        episodes = _episode_rows(book_dir, slug)

        if dry_run:
            return _log(
                "book.dry-run",
                slug=slug,
                bucket=ref.bucket,
                chapters=len(chapters),
                episodes=len(episodes),
                words=sum(c[6] for c in chapters),
            )

        snapshot = dict(meta)
        snapshot["_fingerprint"] = fp
        conn.execute(
            "INSERT INTO book_metadata (slug, category, archetype, meta_yml, current_phase, phase_status,"
            " bucket, title, content_profile, last_updated) VALUES (?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(slug) DO UPDATE SET category=excluded.category, archetype=excluded.archetype,"
            " meta_yml=excluded.meta_yml, current_phase=excluded.current_phase,"
            " phase_status=excluded.phase_status, bucket=excluded.bucket, title=excluded.title,"
            " content_profile=excluded.content_profile, last_updated=excluded.last_updated",
            (
                slug,
                str(meta.get("category") or cfg.get("category") or "books"),
                meta.get("archetype"),
                json.dumps(snapshot, ensure_ascii=False, default=str),
                phase,
                str(state.get("phase_status") or ""),
                ref.bucket,
                str(meta.get("title") or cfg.get("title") or slug),
                str(cfg.get("content_profile") or ""),
                _now(),
            ),
        )
        # Replaced wholesale, not merged: a chapter REMOVED from the tree (a
        # re-segmentation drops seventeen and writes twenty-four) must leave the
        # index, and an upsert alone would leave the old rows searchable forever.
        conn.execute("DELETE FROM chapters WHERE book_slug = ?", (slug,))
        conn.executemany(
            "INSERT INTO chapters (id, book_slug, chapter_id, chapter_title, source_text,"
            " refined_text, word_count, phase_reached, search_text) VALUES (?,?,?,?,?,?,?,?,?)",
            chapters,
        )
        conn.execute("DELETE FROM episodes WHERE book_slug = ?", (slug,))
        conn.executemany(
            "INSERT INTO episodes (id, book_slug, episode_number, chapter_id, title,"
            " framing_text, source_bundle, build_status) VALUES (?,?,?,?,?,?,?,?)",
            episodes,
        )
        conn.commit()
        return _log(
            "book.hydrated",
            slug=slug,
            bucket=ref.bucket,
            profile=str(cfg.get("content_profile") or ""),
            phase=phase,
            chapters=len(chapters),
            episodes=len(episodes),
            words=sum(c[6] for c in chapters),
            fingerprint=fp,
            ms=int((time.time() - started) * 1000),
        )
    except Exception as e:
        # One unreadable book must not cost the other twenty their index.
        return _log("book.failed", slug=slug, error=f"{type(e).__name__}: {e}", ms=int((time.time() - started) * 1000))


def rebuild_fts(conn) -> dict:
    """Rebuild the search index from `chapters`.

    `INSERT INTO <fts>('rebuild')` is FTS5's own contentless-table rebuild: it
    re-derives the whole index from the content table in one statement, which is
    both faster and less error-prone than deleting and reinserting row by row.
    """
    started = time.time()
    try:
        conn.execute("INSERT INTO chapters_fts(chapters_fts) VALUES('rebuild')")
        conn.commit()
        n = conn.execute("SELECT count(*) FROM chapters_fts").fetchone()[0]
        return _log("fts.rebuilt", rows=n, ms=int((time.time() - started) * 1000))
    except Exception as e:
        return _log("fts.failed", error=f"{type(e).__name__}: {e}")


def search(conn, query: str, *, bucket: str | None = None, limit: int = 20) -> list[dict]:
    """Cross-content search. Returns the book, chapter and a highlighted snippet."""
    # The query is folded the SAME way the index was, so an unvowelled Arabic
    # query reaches the folded column. When folding changes nothing (English, or
    # Arabic already bare) the two halves are identical and FTS5 dedupes the
    # match — searching both costs nothing and misses neither.
    folded = searchable(query)
    match = query if folded == query else f"({query}) OR ({folded})"
    sql = (
        "SELECT b.title AS book, b.bucket, c.chapter_title, c.chapter_id, c.book_slug,"
        # Snippet from refined_text (column 1), never the folded copy: what a
        # reader is shown keeps its diacritics.
        " snippet(chapters_fts, 1, '[', ']', '…', 12) AS snippet, rank"
        " FROM chapters_fts f JOIN chapters c ON c.rowid = f.rowid"
        " LEFT JOIN book_metadata b ON b.slug = c.book_slug"
        " WHERE chapters_fts MATCH ?"
    )
    params: list[Any] = [match]
    if bucket:
        sql += " AND b.bucket = ?"
        params.append(bucket)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def hydrate(slugs=None, *, force: bool = False, dry_run: bool = False, log=print) -> dict:
    started = time.time()
    conn = get_connection()
    conn.execute("PRAGMA busy_timeout=30000")  # a live pipeline run may be writing atoms
    applied = run_migrations()
    if applied:
        _log("migrations.applied", files=applied)
        log(f"  migrations applied: {', '.join(applied)}")

    refs = _list_books()
    if slugs:
        wanted = set(slugs)
        refs = [r for r in refs if r.slug in wanted]
    _log("run.started", books=len(refs), force=force, dry_run=dry_run)

    reports = [hydrate_book(conn, r, force=force, dry_run=dry_run) for r in refs]
    for rep in reports:
        if rep["event"] == "book.hydrated":
            log(f"  {rep['slug']:<38} {rep['chapters']:>3} ch  {rep['episodes']:>3} ep  {rep['words']:>7,} words")
        elif rep["event"] == "book.failed":
            log(f"  {rep['slug']:<38} FAILED — {rep['error']}")
        elif rep["event"] == "book.dry-run":
            log(f"  {rep['slug']:<38} would index {rep['chapters']} ch / {rep['episodes']} ep")

    fts = {} if dry_run else rebuild_fts(conn)
    summary = {
        "books": len(refs),
        "hydrated": sum(1 for r in reports if r["event"] == "book.hydrated"),
        "skipped": sum(1 for r in reports if r["event"] == "book.skipped"),
        "failed": sum(1 for r in reports if r["event"] == "book.failed"),
        "chapters": sum(r.get("chapters", 0) for r in reports),
        "episodes": sum(r.get("episodes", 0) for r in reports),
        "words": sum(r.get("words", 0) for r in reports),
        "fts_rows": fts.get("rows"),
        "ms": int((time.time() - started) * 1000),
    }
    _log("run.finished", **summary)
    try:
        conn.execute(
            "INSERT INTO run_telemetry (run_id, book_slug, phase, status, payload) VALUES (?,?,?,?,?)",
            (f"hydrate-{_now()}", None, "search-index", "completed", json.dumps(summary)),
        )
        conn.commit()
    except Exception:
        pass  # telemetry is a record, never a gate
    return summary


def _list_books():
    """Every book on disk, through the pipeline's OWN resolver.

    `_paths.iter_content` is what the rest of the repo walks the tree with: it
    honours the type-first layout AND the legacy one, descends multi-volume work
    parents to their volumes, and derives the composite slug. Re-implementing
    the walk here would have missed the volumes of every multi-volume work —
    six of them for Asas al-Taweel alone.
    """
    from types import SimpleNamespace

    out = []
    for _status, bucket, d in _paths.iter_content():
        out.append(SimpleNamespace(slug=_paths.slug_of(d), dir=str(d), bucket=bucket))
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="hydrate the cross-content search index")
    p.add_argument("slugs", nargs="*", help="books to hydrate (default: all)")
    p.add_argument("--force", action="store_true", help="re-read even unchanged books")
    p.add_argument("--dry-run", action="store_true", help="read and report; write nothing")
    p.add_argument("--search", metavar="QUERY", help="search the index instead of hydrating")
    p.add_argument("--bucket", help="with --search: restrict to one shelf")
    args = p.parse_args(argv)

    if args.search:
        conn = get_connection()
        run_migrations()
        hits = search(conn, args.search, bucket=args.bucket)
        _log("search", query=args.search, bucket=args.bucket, hits=len(hits))
        if not hits:
            print(f"No match for {args.search!r}.")
            return 0
        for h in hits:
            print(f"{h['book']}  ·  {h['chapter_title']}  [{h['bucket']}]")
            print(f"    {h['snippet']}")
        return 0

    print("Hydrating the cross-content search index…")
    s = hydrate(args.slugs or None, force=args.force, dry_run=args.dry_run)
    print(
        f"\n{s['hydrated']} hydrated · {s['skipped']} unchanged · {s['failed']} failed · "
        f"{s['chapters']:,} chapters · {s['words']:,} words · index {s['fts_rows']} rows · {s['ms']} ms"
    )
    print(f"Log: {LOG_PATH}")
    return 1 if s["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
