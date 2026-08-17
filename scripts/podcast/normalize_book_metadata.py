#!/usr/bin/env python3
"""normalize_book_metadata.py — one home for what a book IS.

WHY THIS EXISTS
---------------
A book's identity — who wrote it, what it is called in its own script, what it is
called in English — is currently recorded in two unrelated places, and only one of
the two surfaces a reader looks at can see each of them.

  * Each book's own files: `meta.yml`, `_system/meta.yml`, a work's `work.yml`.
    This is what the pipeline reads, so it is what the Podcast Factory Library
    publishes.
  * `plan-dashboard/src/lib/book-card-meta.ts`, a hand-typed TypeScript
    dictionary keyed by slug. This is a browser-side display map. No Python
    reads it, so nothing in it ever reaches the Library.

The result is not a tidiness problem. The two sites show DIFFERENT NAMES for the
same book — the Library calls it "Kitab al-Riyad" and the Studio shelf calls it
"The Book of Gardens" — and seven books display an author on the Studio shelf
that exists nowhere on disk, so the Library shows none.

WHAT THIS DOES
--------------
Moves the identity into the book's own files, deterministically:

  1. Reads every source, in one fixed precedence, and records WHERE each value
     came from. The precedence never changes between runs and never depends on
     the order the filesystem happens to return.
  2. Writes a canonical key into the book's own `meta.yml` ONLY where that file
     is silent. A book that already states something is never overwritten and
     never re-ordered — this is the pipeline's own data and a human wrote most
     of it.
  3. Reports, by name, every field no source states. It does NOT invent one.
     An author this script cannot find is an author only a person can supply,
     and a plausible guess about who wrote a religious text is the single worst
     thing this file could do.

It is IDEMPOTENT by construction: after a run, the values it wrote are in the
book's own file, so the next run reads them from there and changes nothing.

WHAT IT DELIBERATELY LEAVES ALONE
---------------------------------
  * `icon` and `blurb` stay in the TypeScript dictionary. A FontAwesome name is a
    property of a card, not of a book, and moving it into content would put a
    display detail in the pipeline's data.
  * The scattered author keys already on disk (`doctrinal_context.author`,
    `_system/meta.yml`'s `author`) are READ but never deleted. Pipeline phases
    read those paths today; removing them to make the shape tidy would be a
    refactor of live readers wearing a normalisation's clothes.
  * `meta.title`. It is what the Library publishes as the book's name, and
    whether a reader should see the transliteration or the English translation
    is an editorial decision, not a mechanical one. The English title is written
    to a NEW key, `title_english`, which leaves both recorded and lets that
    decision be made once, later, in the open.

USAGE
-----
    python3 scripts/podcast/normalize_book_metadata.py            # report only
    python3 scripts/podcast/normalize_book_metadata.py --apply    # write
    python3 scripts/podcast/normalize_book_metadata.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402
from _paths import BUCKETS, CONTENT_ROOT, REPO_ROOT  # noqa: E402

CARD_META_TS = "plan-dashboard/src/lib/book-card-meta.ts"

# The canonical key for each identity field, in the book's own meta.yml.
#
# `title_arabic` and `title_urdu` already exist and are already read by
# `_listener_book.py`, so they are adopted rather than replaced. `title_english`
# is new — see the module docstring for why the English title could not simply
# go into `title`.
KEY_AUTHOR = "author"
KEY_ENGLISH = "title_english"
KEY_ARABIC = "title_arabic"
KEY_URDU = "title_urdu"


@dataclass
class Resolution:
    """One field of one book: what it is, and which file said so."""

    value: str | None = None
    source: str = "none"


@dataclass
class BookIdentity:
    slug: str
    meta_path: Path
    author: Resolution = field(default_factory=Resolution)
    english: Resolution = field(default_factory=Resolution)
    native: Resolution = field(default_factory=Resolution)
    native_key: str = KEY_ARABIC
    track: Resolution = field(default_factory=Resolution)
    # A dictionary title dropped for being a respelling rather than a
    # translation — kept so the decision is reported rather than silent.
    respelling: str | None = None

    def writes(self) -> dict[str, str]:
        """The keys this book's own meta.yml is missing and this run can supply.

        A value already in `meta.yml` is never rewritten — `source == "meta"` is
        exactly the case where there is nothing to do.
        """
        out: dict[str, str] = {}
        if self.author.value and self.author.source != "meta":
            out[KEY_AUTHOR] = self.author.value
        if self.english.value and self.english.source != "meta":
            out[KEY_ENGLISH] = self.english.value
        if self.native.value and self.native.source != "meta":
            out[self.native_key] = self.native.value
        return out

    def unknown(self) -> list[str]:
        gaps = []
        if not self.author.value:
            gaps.append("author")
        if not self.native.value:
            gaps.append("native-script title")
        if not self.track.value:
            gaps.append("study track")
        return gaps


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _s(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _fold(value: str) -> str:
    """A title reduced to what survives a change of romanization.

    Case, punctuation and spacing go, and a run of the same letter collapses to
    one — which is the whole difference between "Asaar" and "Asar", and between
    "al-Nu'man" and "al Numan". Two titles that fold to the same string are one
    title spelled twice; two that do not are two titles.
    """
    stripped = re.sub(r"[^0-9a-z]+", "", value.lower())
    return re.sub(r"(.)\1+", r"\1", stripped)


def _is_respelling(candidate: str | None, existing: str | None) -> bool:
    return bool(candidate and existing and _fold(candidate) == _fold(existing))


def _nested(data: Any, *keys: str) -> str | None:
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return _s(data)


def read_card_meta() -> dict[str, dict[str, Any]]:
    """The hand-typed TypeScript dictionary, obtained by ASKING it.

    Executed through node rather than parsed with a regex. The map holds an
    apostrophe inside a quoted author and Arabic inside a string literal, and a
    regex that got either wrong would fail by producing a slightly-wrong name
    for a book, which is worse than failing loudly. The repo already bridges to
    node this way for the Scholar cards (`_scholar_bridge.py`).

    Returns `{}` when node is unavailable — the run then reports the fields it
    cannot see rather than pretending they do not exist.
    """
    dashboard = REPO_ROOT / "plan-dashboard"
    script = "import('./src/lib/book-card-meta.ts').then(m => console.log(JSON.stringify(m.BOOK_CARD_META)))"
    try:
        out = subprocess.run(
            ["node", "--import", "./scripts/lib/ts-resolve-hook.mjs", "-e", script],
            cwd=dashboard,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        ).stdout
        data = json.loads(out)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def card_meta_for(card_meta: dict[str, dict[str, Any]], slug: str) -> dict[str, Any]:
    """Mirrors `cardMetaFor` in book-card-meta.ts: an exact entry, else the
    parent's template for a `<work>-vol-NN` slug."""
    exact = card_meta.get(slug)
    if exact:
        return exact
    m = re.match(r"^(.+)-vol-0*\d+$", slug)
    if m:
        return card_meta.get(m.group(1)) or {}
    return {}


def declared_siblings() -> dict[str, list[str]]:
    """slug -> the other volumes of the same declared work.

    A volume of a multi-volume work has a fact available to it that a standalone
    book does not: its siblings are the same work by the same hand. Mukhtasar's
    second volume records its author and its first does not, and they are not two
    books that happen to be adjacent — a declaration says they are one work.
    Used ONLY when every sibling that speaks says the same name; two different
    names is a question, not a default.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from sync_listener_work_groups import find_groups
    except Exception:
        return {}
    out: dict[str, list[str]] = {}
    for group in find_groups():
        slugs = [v["slug"] for v in group.volumes]
        for slug in slugs:
            out[slug] = [s for s in slugs if s != slug]
    return out


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def _first(*candidates: tuple[str, str | None]) -> Resolution:
    for source, value in candidates:
        if value:
            return Resolution(value, source)
    return Resolution()


def resolve(
    slug: str,
    book_dir: Path,
    card_meta: dict[str, dict[str, Any]],
) -> BookIdentity:
    meta_path = book_dir / "meta.yml"
    meta = _load(meta_path)
    system = _load(book_dir / "_system" / "meta.yml")
    work = _load(book_dir.parent / "work.yml")
    card = card_meta_for(card_meta, slug)

    identity = BookIdentity(slug=slug, meta_path=meta_path)

    # The book's own meta.yml first, always. Every later source is a place the
    # value ended up because this one was silent.
    identity.author = _first(
        ("meta", _s(meta.get(KEY_AUTHOR))),
        ("meta:doctrinal_context", _nested(meta, "doctrinal_context", "author")),
        ("_system/meta.yml", _s(system.get("author"))),
        ("meta:publication", _nested(meta, "publication", "author")),
        ("work.yml", _s(work.get("author"))),
        ("book-card-meta.ts", _s(card.get("author"))),
    )

    # Urdu and Arabic are separate keys because `_listener_book.py` reads them
    # separately to label the script a title is set in — a Urdu title filed
    # under `title_arabic` would be typeset in the wrong face.
    urdu = _s(meta.get(KEY_URDU))
    language = _s(meta.get("original_title_language")) or _s(meta.get("source_language"))
    card_native = _s(card.get("nativeTitle"))
    card_is_urdu = card.get("nativeLang") == "ur"
    if urdu or language == "ur" or card_is_urdu:
        identity.native_key = KEY_URDU
        identity.native = _first(
            ("meta", urdu),
            ("book-card-meta.ts", card_native if card_is_urdu else None),
        )
    else:
        identity.native = _first(
            ("meta", _s(meta.get(KEY_ARABIC))),
            ("work.yml", _s(work.get(KEY_ARABIC))),
            ("book-card-meta.ts", card_native),
        )

    # Two sources ONLY, and the omissions are the point.
    #
    # `publication.english_title` is deliberately NOT one of them. It is the
    # TITLE-PAGE form and it carries the subtitle: "Degrees of Excellence: A
    # Fatimid Treatise on Leadership in Islam" is 64 characters and wraps to four
    # lines in a card meant to look like its neighbours. Promoting it here would
    # make it the card's heading, which is the opposite of what the card code
    # already decided about it.
    #
    # And a dictionary entry that is only a RESPELLING of the title the book
    # already records is not a translation. "Mukhtasar ul Asar 2" beside a
    # `title` of "Mukhtasar-ul-Asaar 2" records nothing except a second opinion
    # about how to spell it — worse than silence, because a later reader would
    # take the new key for a considered English name.
    english = _first(
        ("meta", _s(meta.get(KEY_ENGLISH))),
        ("book-card-meta.ts", _s(card.get("displayTitle"))),
    )
    if english.source != "meta" and _is_respelling(english.value, _s(meta.get("title"))):
        identity.respelling = english.value
        english = Resolution()
    identity.english = english

    identity.track = _first(
        ("meta", _s(meta.get("study_track"))),
        ("work.yml", _s(work.get("study_track"))),
    )
    return identity


def fill_from_siblings(books: dict[str, BookIdentity], siblings: dict[str, list[str]]) -> None:
    """An author a volume does not state, taken from the volumes that do.

    Only when every sibling that speaks says the SAME name. Two different names
    across one work is a genuine question about the work and this run leaves it
    for a person.
    """
    for slug, others in siblings.items():
        book = books.get(slug)
        if book is None or book.author.value:
            continue
        names = {books[o].author.value for o in others if o in books and books[o].author.value}
        if len(names) == 1:
            book.author = Resolution(names.pop(), "sibling volume")


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

# The identity block is inserted after the last of these keys that is present,
# so a book's file keeps reading top-down as slug -> what it is -> how it is
# built. Appending at the end instead would bury the author under a provenance
# note nobody reads.
ANCHOR_KEYS = ("title_urdu", "title_arabic", "title", "slug")


def apply_writes(book: BookIdentity, writes: dict[str, str]) -> str:
    """Insert the missing keys into meta.yml, TEXTUALLY.

    Not a YAML round-trip. `yaml.safe_dump` would rewrite the whole file — losing
    every comment in it, and these files carry comments that explain real
    decisions ("this flag is why five phases were stamped skipped"). A targeted
    insertion touches the lines it adds and nothing else.
    """
    text = book.meta_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    anchor = -1
    for key in ANCHOR_KEYS:
        for i, line in enumerate(lines):
            if re.match(rf"^{re.escape(key)}\s*:", line):
                anchor = max(anchor, i)
        if anchor >= 0:
            break

    # Dumped as a one-key MAPPING, not as a bare scalar: `safe_dump("Someone")`
    # is a whole YAML document and comes back as "Someone\n...\n", so the
    # document-end marker lands in the middle of the file and everything below
    # it stops being read. Dumping the mapping also gets the quoting right for a
    # value containing a colon or a leading quote, which a hand-built f-string
    # would not.
    block = [
        yaml.safe_dump({k: v}, allow_unicode=True, default_flow_style=False, sort_keys=False).strip()
        for k, v in writes.items()
    ]
    at = anchor + 1 if anchor >= 0 else 0
    lines[at:at] = block
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def collect(card_meta: dict[str, dict[str, Any]]) -> dict[str, BookIdentity]:
    books: dict[str, BookIdentity] = {}
    for bucket in BUCKETS:
        bucket_dir = CONTENT_ROOT / bucket
        if not bucket_dir.is_dir():
            continue
        for child in sorted(bucket_dir.iterdir()):
            if not child.is_dir() or child.name.startswith(("_", ".")):
                continue
            if (child / "meta.yml").is_file():
                books[child.name] = resolve(child.name, child, card_meta)
            for volume in sorted(child.glob("vol-*")):
                if (volume / "meta.yml").is_file():
                    slug = f"{child.name}-{volume.name}"
                    books[slug] = resolve(slug, volume, card_meta)
    return books


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the changes (default: report only)")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    args = ap.parse_args()

    card_meta = read_card_meta()
    books = collect(card_meta)
    fill_from_siblings(books, declared_siblings())

    planned = {slug: b.writes() for slug, b in books.items()}
    planned = {slug: w for slug, w in planned.items() if w}
    gaps = {slug: b.unknown() for slug, b in books.items() if b.unknown()}

    if args.json:
        print(
            json.dumps(
                {
                    "books": len(books),
                    "writes": planned,
                    "unknown": gaps,
                    "card_meta_readable": bool(card_meta),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if not card_meta:
        print("WARNING: could not read book-card-meta.ts through node — its values are invisible to this run.\n")

    if planned:
        print(f"Identity to move into each book's own meta.yml ({len(planned)} book(s)):\n")
        for slug in sorted(planned):
            book = books[slug]
            print(f"  {slug}")
            for key, value in planned[slug].items():
                source = {
                    KEY_AUTHOR: book.author.source,
                    KEY_ENGLISH: book.english.source,
                    book.native_key: book.native.source,
                }[key]
                print(f"      {key}: {value}   [from {source}]")
            print()
    else:
        print("Every book already records its own identity — nothing to move.\n")

    respellings = {slug: b.respelling for slug, b in books.items() if b.respelling}
    if respellings:
        print(f"Dropped as a respelling, not a translation ({len(respellings)}):\n")
        for slug in sorted(respellings):
            print(f"  {slug:<32} {respellings[slug]!r} folds to the title already recorded")
        print()

    if gaps:
        print(f"NOT written, because no source states them ({len(gaps)} book(s)):\n")
        for slug in sorted(gaps):
            print(f"  {slug:<32} missing: {', '.join(gaps[slug])}")
        print("\nThese need a person. This script will not guess a book's author.")

    if args.apply:
        for slug in sorted(planned):
            book = books[slug]
            book.meta_path.write_text(apply_writes(book, planned[slug]), encoding="utf-8")
        print(f"\nwrote {len(planned)} meta.yml file(s)")
    elif planned:
        print("\nReport only. Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
