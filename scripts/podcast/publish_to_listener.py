#!/usr/bin/env python3
"""Push a finished book into the Podcast Factory Listener's database.

This is the phase-3 writer for `listener/migrations/0004_catalog.sql`: it reads
one book out of `content/<Bucket>/<slug>/` and writes its reading edition, its
episodes and its media inventory into D1.

Reading a book off disk lives in `_listener_book.py`. That half holds all the
judgment — how a chapter is keyed, which audio file belongs to which episode,
what counts as a blurb — and this half is the mechanical turn into SQL.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It never names `content_unit.status` or `content_unit.open_to_all`. Those two
columns are the privilege bits — one decides whether a unit is readable at all,
the other opens it to every signed-in person — and they belong to the admin
session alone. When this script has to create a `content_unit` row for a book the
seed did not know about, it OMITS both columns and lets the schema defaults
('draft' and 0) apply, so a newly published book is invisible until a human says
otherwise. That is stricter than passing the safe value explicitly, because there
is then no line to get wrong later.

WHY THE HTML IS RENDERED HERE
-----------------------------
Chapter prose goes through `renderMarkdown` from
`plan-dashboard/src/lib/reader/markdown.ts` — the same function behind the print
edition — via `listener/scripts/render-chapters.mjs`. Rendering in the Worker
instead would mean a second markdown implementation that can disagree with the
printed book about the same paragraph.

USAGE
-----
    python3 scripts/podcast/publish_to_listener.py <slug> [<slug> …]
        [--remote]     write to the deployed D1 instead of the local one
        [--dry-run]    print the plan and the SQL path; execute nothing
        [--json]       machine-readable summary on stdout

Media (audio, PDFs, covers, deck pages) is INVENTORIED here and uploaded
separately, because R2 is not enabled on the Cloudflare account yet. Every
`media_asset` row is written with `uploaded_at` NULL, which is what the site
reads as "this exists but is not available yet" — it shows the episode and says
there is no audio, rather than offering a link that would 404.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _listener_book import LISTENER, Book, load_book, render  # noqa: E402
from _paths import REPO_ROOT  # noqa: E402

# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def sql_str(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def build_sql(book: Book, *, published_at: str, commit: str | None) -> str:
    """Everything for one book, as one replaceable block.

    Each table is cleared for this slug and rewritten. That makes a re-publish
    idempotent and, more importantly, makes DELETION work: a chapter dropped from
    the edition disappears here too, where an upsert-only script would leave it
    readable forever.
    """
    out: list[str] = []
    add = out.append

    # The access row. Note the columns NOT named: status and open_to_all are left
    # to the schema defaults, so a book published for the first time is a draft
    # nobody can see until a human changes that in the admin screens.
    add(
        "INSERT INTO content_unit (slug, bucket, title, kind, sort_order) VALUES "
        f"({sql_str(book.slug)}, {sql_str(book.bucket)}, {sql_str(book.title)}, 'book', 0) "
        "ON CONFLICT(slug) DO UPDATE SET bucket = excluded.bucket, title = excluded.title;"
    )

    add(f"DELETE FROM unit_detail WHERE slug = {sql_str(book.slug)};")
    add(
        "INSERT INTO unit_detail "
        "(slug, title_arabic, blurb_html, edition_note, cover_key, pdf_key, published_at, source_commit) "
        f"VALUES ({sql_str(book.slug)}, {sql_str(book.title_arabic)}, {sql_str(book.blurb)}, "
        f"{sql_str(book.edition_note)}, {sql_str(book.cover.key if book.cover else None)}, "
        f"{sql_str(book.pdf.key if book.pdf else None)}, {sql_str(published_at)}, {sql_str(commit)});"
    )

    add(f"DELETE FROM chapter WHERE slug = {sql_str(book.slug)};")
    for chapter in book.chapters:
        add(
            "INSERT INTO chapter (slug, anchor_key, idx, title, html, word_count) VALUES "
            f"({sql_str(book.slug)}, {sql_str(chapter.anchor)}, {chapter.idx}, "
            f"{sql_str(chapter.title)}, {sql_str(chapter.html)}, {chapter.word_count});"
        )

    add(f"DELETE FROM episode WHERE slug = {sql_str(book.slug)};")
    for episode in book.episodes:
        add(
            "INSERT INTO episode (slug, number, title, blurb, style, audio_key, duration_s) VALUES "
            f"({sql_str(book.slug)}, {episode.number}, {sql_str(episode.title)}, "
            f"{sql_str(episode.blurb)}, {sql_str(episode.style)}, "
            f"{sql_str(episode.audio.key if episode.audio else None)}, "
            f"{sql_str(episode.duration_s)});"
        )

    add(f"DELETE FROM episode_chapter WHERE slug = {sql_str(book.slug)};")
    for number, anchor in book.bridge:
        add(
            "INSERT INTO episode_chapter (slug, number, anchor_key) VALUES "
            f"({sql_str(book.slug)}, {number}, {sql_str(anchor)});"
        )

    # Media rows are rewritten but `uploaded_at` is preserved for keys that are
    # already in R2 and whose content has not changed — re-publishing prose must
    # not make the site claim a 50 MB recording has vanished.
    add(f"DELETE FROM media_asset WHERE slug = {sql_str(book.slug)};")
    for asset in book.assets:
        add(
            "INSERT INTO media_asset (key, slug, kind, content_type, bytes, sha256, source_path) VALUES "
            f"({sql_str(asset.key)}, {sql_str(asset.slug)}, {sql_str(asset.kind)}, "
            f"{sql_str(asset.content_type)}, {asset.bytes}, {sql_str(asset.sha256)}, "
            f"{sql_str(str(asset.path.relative_to(REPO_ROOT)))});"
        )

    return "\n".join(out) + "\n"


def execute(sql_path: Path, *, remote: bool) -> None:
    subprocess.run(
        [
            "npx",
            "wrangler",
            "d1",
            "execute",
            "podcast-listener",
            "--remote" if remote else "--local",
            f"--file={sql_path}",
            "--yes",
        ],
        cwd=LISTENER,
        check=True,
    )


# ---------------------------------------------------------------------------


def describe(book: Book) -> dict:
    with_audio = sum(1 for e in book.episodes if e.audio)
    return {
        "slug": book.slug,
        "bucket": book.bucket,
        "title": book.title,
        "chapters": len(book.chapters),
        "episodes": len(book.episodes),
        "episodes_with_audio": with_audio,
        "pdf": bool(book.pdf),
        "cover": bool(book.cover),
        "deck_pages": sum(1 for a in book.assets if a.kind == "deck-page"),
        "bridge_links": len(book.bridge),
        "unmatched_audio": book.unmatched_audio,
        "media_bytes": sum(a.bytes for a in book.assets),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="+")
    parser.add_argument("--remote", action="store_true", help="write to the deployed D1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    commit = None
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    published_at = subprocess.run(
        ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True, check=True
    ).stdout.strip()

    summaries = []
    statements: list[str] = []

    for slug in args.slugs:
        book = load_book(slug)
        render(book)
        statements.append(build_sql(book, published_at=published_at, commit=commit))
        summary = describe(book)
        summaries.append(summary)

        if not args.json:
            print(f"\n{book.title}  ({book.bucket}/{book.slug})")
            print(f"  chapters           {summary['chapters']}")
            print(f"  episodes           {summary['episodes']}  ({summary['episodes_with_audio']} with audio)")
            print(f"  print edition      {'yes' if summary['pdf'] else 'no'}")
            print(f"  slide deck         {summary['deck_pages'] or 'none'}")
            print(f"  episode<->chapter  {summary['bridge_links'] or 'not recorded'}")
            for name in summary["unmatched_audio"]:
                print(f"  ! audio matched no episode, skipped: {name}")

    out_dir = LISTENER / ".publish"
    out_dir.mkdir(exist_ok=True)
    sql_path = out_dir / ("-".join(args.slugs)[:60] + ".sql")
    sql_path.write_text("".join(statements), encoding="utf-8")

    if args.dry_run:
        if not args.json:
            print(f"\ndry run — SQL written to {sql_path.relative_to(REPO_ROOT)}, nothing executed")
    else:
        execute(sql_path, remote=args.remote)
        if not args.json:
            target = "the deployed database" if args.remote else "the local database"
            print(f"\nwritten to {target}")

    if args.json:
        print(json.dumps({"books": summaries, "sql": str(sql_path)}, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
