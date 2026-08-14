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

Media (audio, PDFs, covers, deck pages) is INVENTORIED here and uploaded by
`upload_listener_media.py`, which is the slow, retryable half. A row written here
starts with `uploaded_at` NULL — "this exists on disk but is not available yet" —
and the site reports it that way rather than offering a link that would 404.

This step DOES delete objects, in one narrow case: when a re-publish drops a
`media_asset` row because the file is gone from disk, the object behind it goes
too. Nothing can list an R2 bucket from here, so the moment the row disappears
is the only moment that key is knowable — and a recording pulled from a book must
not stay downloadable by anyone who noted the URL.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _listener_book import LISTENER, Book, load_book, render  # noqa: E402
from _listener_search import IndexReport, Passage, passages_for  # noqa: E402
from _paths import REPO_ROOT  # noqa: E402
from _production_publish import account_ok, cloudflare_env  # noqa: E402

# The bucket belongs to the uploader; the publish step borrows two of its
# functions rather than growing a second way to talk to R2.
from upload_listener_media import d1, delete_object  # noqa: E402

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


_SEARCH_CACHE: dict[str, tuple[list[Passage], IndexReport]] = {}


def search_index(book: Book) -> tuple[list[Passage], IndexReport]:
    """The book's search rows, computed once.

    Cached because `build_sql` and `describe` both want them and naming a verse
    means matching its skeleton against all 6,236 ayat — cheap once per book,
    wasteful twice.
    """
    if book.slug not in _SEARCH_CACHE:
        _SEARCH_CACHE[book.slug] = passages_for(book)
    return _SEARCH_CACHE[book.slug]


def search_passages(book: Book) -> list[Passage]:
    return search_index(book)[0]


def build_statements(book: Book, *, published_at: str, commit: str | None) -> list[str]:
    """Everything for one book, as one replaceable block of statements.

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
        "(slug, title_arabic, title_language, study_track, blurb_html, edition_note, cover_key, pdf_key, published_at, source_commit) "
        f"VALUES ({sql_str(book.slug)}, {sql_str(book.title_arabic)}, {sql_str(book.title_language)}, {sql_str(book.study_track)}, "
        f"{sql_str(book.blurb)}, "
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

    add(f"DELETE FROM chapter_narration WHERE slug = {sql_str(book.slug)};")
    for chapter in book.chapters:
        if chapter.narration is None:
            continue
        add(
            "INSERT INTO chapter_narration "
            "(slug, anchor_key, audio_key, duration_s, source_hash, voice, cues_json) VALUES "
            f"({sql_str(book.slug)}, {sql_str(chapter.anchor)}, "
            f"{sql_str(chapter.narration.audio.key)}, {sql_str(chapter.narration.duration_s)}, "
            f"{sql_str(chapter.narration.source_hash)}, {sql_str(chapter.narration.voice)}, "
            f"{sql_str(json.dumps(listener_narration_cues(chapter.narration.cues), ensure_ascii=False))});"
        )

    # Sessions first, since an episode points at one.
    add(f"DELETE FROM book_session WHERE slug = {sql_str(book.slug)};")
    for session in book.sessions:
        add(
            "INSERT INTO book_session (slug, number, title) VALUES "
            f"({sql_str(book.slug)}, {session.number}, {sql_str(session.title)});"
        )

    add(f"DELETE FROM episode WHERE slug = {sql_str(book.slug)};")
    for episode in book.episodes:
        add(
            "INSERT INTO episode "
            "(slug, number, title, blurb, style, audio_key, transcript_key, duration_s, session_number) VALUES "
            f"({sql_str(book.slug)}, {episode.number}, {sql_str(episode.title)}, "
            f"{sql_str(episode.blurb)}, {sql_str(episode.style)}, "
            f"{sql_str(episode.audio.key if episode.audio else None)}, "
            f"{sql_str(episode.transcript.key if episode.transcript else None)}, "
            f"{sql_str(episode.duration_s)}, {sql_str(episode.session)});"
        )

    add(f"DELETE FROM episode_chapter WHERE slug = {sql_str(book.slug)};")
    for number, anchor in book.bridge:
        add(
            "INSERT INTO episode_chapter (slug, number, anchor_key) VALUES "
            f"({sql_str(book.slug)}, {number}, {sql_str(anchor)});"
        )

    # The Scholar Companion cards. Cleared and rewritten like the chapters, so a
    # note deleted in the Composer disappears here rather than staying readable
    # forever — and so does one whose chapter was renamed out from under it.
    add(f"DELETE FROM companion_note WHERE slug = {sql_str(book.slug)};")
    for card in book.companion:
        add(
            "INSERT INTO companion_note "
            "(slug, anchor_key, note_id, idx, title, quote, body_html, etymology) VALUES "
            f"({sql_str(book.slug)}, {sql_str(card.anchor)}, {sql_str(card.note_id)}, "
            f"{card.idx}, {sql_str(card.title)}, {sql_str(card.quote)}, "
            f"{sql_str(card.body_html)}, "
            f"{sql_str(json.dumps(card.etymology, ensure_ascii=False) if card.etymology else None)});"
        )

    # The search index. Cleared and rewritten with the chapters it describes,
    # which is what stops it describing a passage the edition no longer has.
    #
    # NOTHING TOUCHES `search_fts` HERE, deliberately. It is an external-content
    # FTS5 table kept in step by three triggers declared in 0012_search.sql, so
    # these two statements maintain it for free. A second write here would be the
    # copy that drifts the first time somebody changed one and not the other.
    add(f"DELETE FROM search_passage WHERE slug = {sql_str(book.slug)};")
    for passage in search_passages(book):
        add(
            "INSERT INTO search_passage "
            "(slug, kind, anchor_key, heading, ordinal, episode_number, quote, prefix, "
            "arabic, label, surah, ayah, heading_fold, body_fold, arabic_fold) VALUES "
            f"({sql_str(passage.slug)}, {sql_str(passage.kind)}, {sql_str(passage.anchor_key)}, "
            f"{sql_str(passage.heading)}, {passage.ordinal}, "
            f"{passage.episode_number if passage.episode_number is not None else 'NULL'}, "
            f"{sql_str(passage.quote)}, {sql_str(passage.prefix)}, {sql_str(passage.arabic)}, "
            f"{sql_str(passage.label)}, "
            f"{passage.surah if passage.surah is not None else 'NULL'}, "
            f"{passage.ayah if passage.ayah is not None else 'NULL'}, "
            f"{sql_str(passage.heading_fold)}, {sql_str(passage.body_fold)}, "
            f"{sql_str(passage.arabic_fold)});"
        )

    # Media is the ONE table not cleared and rewritten, because `uploaded_at` is
    # knowledge this run does not have: it says the object is in R2, and only the
    # uploader can know that. A delete-and-reinsert would reset it on every
    # re-publish, so correcting a typo in one chapter would make the site report
    # that fifty megabytes of recordings had vanished — and the uploader would
    # then push all of them again.
    #
    # So: drop only the keys that no longer exist on disk, and upsert the rest.
    # `uploaded_at` survives when the CONTENT is unchanged and is cleared when it
    # is not, which is exactly right — a re-cut recording under the same key is a
    # different object and has to be uploaded again. The CASE reads the OLD row;
    # SQLite evaluates every right-hand side against the existing values.
    keys = ", ".join(sql_str(a.key) for a in book.assets)
    add(f"DELETE FROM media_asset WHERE slug = {sql_str(book.slug)}" + (f" AND key NOT IN ({keys});" if keys else ";"))
    for asset in book.assets:
        add(
            "INSERT INTO media_asset "
            "(key, slug, kind, content_type, bytes, sha256, source_path, deck_id, deck_title) VALUES "
            f"({sql_str(asset.key)}, {sql_str(asset.slug)}, {sql_str(asset.kind)}, "
            f"{sql_str(asset.content_type)}, {asset.bytes}, {sql_str(asset.sha256)}, "
            f"{sql_str(str(asset.path.relative_to(REPO_ROOT)))}, "
            f"{sql_str(asset.deck_id)}, {sql_str(asset.deck_title)}) "
            "ON CONFLICT(key) DO UPDATE SET "
            "slug = excluded.slug, kind = excluded.kind, content_type = excluded.content_type, "
            "bytes = excluded.bytes, source_path = excluded.source_path, "
            "deck_id = excluded.deck_id, deck_title = excluded.deck_title, "
            "uploaded_at = CASE WHEN media_asset.sha256 = excluded.sha256 "
            "THEN media_asset.uploaded_at ELSE NULL END, "
            "sha256 = excluded.sha256;"
        )

    return out


def build_sql(book: Book, *, published_at: str, commit: str | None) -> str:
    """The SQL file shape, kept for dry runs, inspection, and local imports."""
    return "\n".join(build_statements(book, published_at=published_at, commit=commit)) + "\n"


def listener_narration_cues(cues: list[dict]) -> list[dict]:
    """Only the browser sync data; the paragraph text is already in chapter HTML."""
    slim: list[dict] = []
    for cue in cues:
        slim.append(
            {
                "idx": cue.get("idx"),
                "blockIndex": cue.get("blockIndex"),
                "startS": cue.get("startS"),
                "endS": cue.get("endS"),
            }
        )
    return slim


def keys_in_bucket(slug: str, *, remote: bool) -> set[str]:
    """The media keys this book currently claims to have uploaded."""
    rows = d1(
        f"SELECT key FROM media_asset WHERE uploaded_at IS NOT NULL AND slug = {sql_str(slug)}",
        remote=remote,
    )
    return {r["key"] for r in rows}


REMOTE_BATCH_BYTES = 80_000


def remote_batches(statements: list[str], *, max_bytes: int = REMOTE_BATCH_BYTES) -> list[str]:
    """Group statements for D1's query endpoint without using the import path."""
    batches: list[str] = []
    current: list[str] = []
    size = 0
    for statement in statements:
        statement_size = len(statement.encode("utf-8")) + 1
        if current and size + statement_size > max_bytes:
            batches.append("\n".join(current))
            current = []
            size = 0
        current.append(statement)
        size += statement_size
    if current:
        batches.append("\n".join(current))
    return batches


def execute(sql_path: Path, *, remote: bool, statements: list[str] | None = None) -> None:
    if statements is not None:
        batches = remote_batches(statements)
        location = "remote" if remote else "local"
        for i, command in enumerate(batches, 1):
            print(f"  {location} SQL batch {i}/{len(batches)}")
            subprocess.run(
                [
                    "npx",
                    "wrangler",
                    "d1",
                    "execute",
                    "podcast-listener",
                    "--remote" if remote else "--local",
                    "--command",
                    command,
                    "--yes",
                ],
                cwd=LISTENER,
                capture_output=True,
                text=True,
                check=True,
            )
        return

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


def session_concerns(book: Book) -> list[str]:
    """Where this book's two answers about sessions disagree. Reported, never fatal.

    There are two, and until now they never spoke. The pipeline DERIVES sessions
    from the book's table-of-contents plan (`_sessions.derive_sessions`); the
    Listener READS them from the folder names the author typed under
    `m4a/Episodes/`. The folder names are what reach the database, and they are
    the untested side — so a disagreement shipped silently and looked like a fact.

    That is exactly how Degrees of Excellence went live under a lone "Session 4":
    the folder was numbered from the book's source-chapter index instead of its
    position in the series, and nothing anywhere was in a position to notice.

    Folders stay authoritative — arranging recordings into them is the author's
    act of declaring a podcast finished, and inferring the grouping instead would
    start publishing groupings for half-recorded books. This only says when the
    two disagree, the way `unmatched_audio` says when a recording did not land.
    """
    concerns: list[str] = []
    numbers = sorted(s.number for s in book.sessions)

    # Numbered from 1, contiguously. A reader shown "Session 4" with no Sessions
    # 1-3 above it has been told the book is missing three parts.
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        concerns.append(
            f"sessions are numbered {numbers} — not 1..{len(numbers)}. "
            "A session number is its position in the series, not its index in the source."
        )

    try:
        from _sessions import load_sessions_for_book

        derived = load_sessions_for_book(book.directory) or []
    except Exception:  # a book with no plan on disk simply has nothing to compare
        return concerns

    if derived and not book.sessions:
        titles = ", ".join(str(s["session_title"]) for s in derived[:3])
        concerns.append(
            f"the plan derives {len(derived)} session(s) ({titles}...) but no "
            "`m4a/Episodes/Session N — ...` folders exist, so this book publishes flat "
            "and that grouping is lost."
        )
    elif derived and len(derived) != len(book.sessions):
        concerns.append(f"the plan derives {len(derived)} session(s); the folders declare {len(book.sessions)}.")

    return concerns


def describe(book: Book) -> dict:
    with_audio = sum(1 for e in book.episodes if e.audio)
    _rows, index = search_index(book)
    return {
        # What the advanced search will be able to find. `verses_named` is the
        # honest number: the Arabic runs the canonical mushaf could put a
        # reference on, out of every run that IS a quotation. The gap is not a
        # failure — most quotation in this library is hadith, poetry or a book
        # title, none of which is scripture and none of which gets a citation.
        "search_passages": index.passages,
        "search_by_kind": index.per_kind,
        "arabic_quotations": index.verses,
        "verses_named": index.named_verses,
        "mushaf_available": index.mushaf,
        "slug": book.slug,
        "bucket": book.bucket,
        "title": book.title,
        "chapters": len(book.chapters),
        "episodes": len(book.episodes),
        "episodes_with_audio": with_audio,
        "sessions": len(book.sessions),
        "pdf": bool(book.pdf),
        "cover": bool(book.cover),
        "deck_pages": sum(1 for a in book.assets if a.kind == "deck-page"),
        "bridge_links": len(book.bridge),
        "companion_cards": len(book.companion),
        "unmatched_audio": book.unmatched_audio,
        "session_concerns": session_concerns(book),
        "media_bytes": sum(a.bytes for a in book.assets),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="+")
    parser.add_argument("--remote", action="store_true", help="write to the deployed D1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.remote:
        try:
            os.environ.update(cloudflare_env())
        except RuntimeError as error:
            print(f"  ! {error}")
            return 2
        ok, who = account_ok(dict(os.environ), LISTENER)
        if not ok:
            print(f"  ! {who}")
            return 2

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

    out_dir = LISTENER / ".publish"
    out_dir.mkdir(exist_ok=True)

    summaries = []
    failed: list[str] = []

    # ONE FILE PER BOOK, executed as we go. Concatenating three books came to
    # 566 KB and D1 refused it with `statement too long` even though its largest
    # single statement was 86 KB — the limit that bit is on what the executor
    # will swallow at once, not on any one statement. Per-book files stay well
    # under it and cost nothing; they also mean a book that fails does not
    # strand the ones after it.
    for slug in args.slugs:
        book = load_book(slug)
        render(book)
        summary = describe(book)
        summaries.append(summary)

        sql_path = out_dir / f"{slug}.sql"
        statements = build_statements(book, published_at=published_at, commit=commit)
        sql_path.write_text("\n".join(statements) + "\n", encoding="utf-8")

        if not args.json:
            print(f"\n{book.title}  ({book.bucket}/{book.slug})")
            print(f"  chapters           {summary['chapters']}")
            print(f"  episodes           {summary['episodes']}  ({summary['episodes_with_audio']} with audio)")
            if summary["sessions"]:
                print(f"  sessions           {summary['sessions']}")
            print(f"  print edition      {'yes' if summary['pdf'] else 'no'}")
            print(f"  slide deck         {summary['deck_pages'] or 'none'}")
            print(f"  episode<->chapter  {summary['bridge_links'] or 'not recorded'}")
            print(f"  scholar cards      {summary['companion_cards'] or 'none'}")
            for name in summary["unmatched_audio"]:
                print(f"  ! audio not shipped, left where it is: {name}")
            for note in summary["session_concerns"]:
                print(f"  ! sessions: {note}")

        if args.dry_run:
            continue

        # What this book has in the bucket right now, read BEFORE the write. The
        # write drops rows for files that no longer exist on disk, and the object
        # behind each one has to go with it — a recording pulled from a book must
        # not stay downloadable by anyone who noted the URL. Nothing can list an
        # R2 bucket from here, so the only moment these keys are knowable is this
        # one, while the row still exists.
        before = set() if args.dry_run else keys_in_bucket(slug, remote=args.remote)

        try:
            execute(sql_path, remote=args.remote, statements=statements)
        except subprocess.CalledProcessError as error:
            failed.append(slug)
            for stream in (error.stdout, error.stderr):
                text = str(stream or "").strip()
                if text:
                    print(text)
            print(f"  ! FAILED to write {slug} — the books before it are already in")
            continue
        except subprocess.SubprocessError as error:
            failed.append(slug)
            print(f"  ! FAILED to write {slug}: {error}")
            continue

        orphans = before - {a.key for a in book.assets}
        for key in sorted(orphans):
            gone = delete_object(key, remote=args.remote)
            print(f"  {'removed from the bucket' if gone else '! could not remove'}: {key}")

    if not args.json:
        if args.dry_run:
            print(f"\ndry run — SQL written to {out_dir.relative_to(REPO_ROOT)}/, nothing executed")
        else:
            target = "the deployed database" if args.remote else "the local database"
            done = len(args.slugs) - len(failed)
            print(f"\n{done} of {len(args.slugs)} written to {target}")

    if args.json:
        print(json.dumps({"books": summaries, "failed": failed}, indent=2))

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
