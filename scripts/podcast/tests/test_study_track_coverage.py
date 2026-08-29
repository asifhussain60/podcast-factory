#!/usr/bin/env python3
"""Every composed book carries a `study_track` — a data-integrity check.

Real bug (2026-08-29): content/Sessions/love-of-the-prophet/meta.yml shipped
with no `study_track`. `publish_to_listener.py` reads the field, finds it
missing, and writes NULL to `unit_detail.study_track` — silently, by design
(`study_track not in {...} -> None` in publish_to_listener.py). The listener
app's "Browse by track" filter (listener/app/lib/study-track.ts `inTrack`) is
just as correct to treat a NULL track as "matches no specific track" as it is
to treat "all" as "matches everything" — so the item vanished under every
single track chip while still showing under "Everything"/"All tracks", which
read as a filter bug from the Podcast Factory Library rather than as what it
was: one book that had never been classified.

This is the other half of that fix. Assigning love-of-the-prophet a track
closes this one instance; this test is what stops the next Islamic or
Sessions book from shipping the same gap unnoticed — it runs at commit time,
long before anyone is looking at the live site wondering why a book is
missing from a track it should be in.

Scope: only `content/<Bucket>/<slug>/` directories that actually have a
composed `book/book.md` are checked. A book earlier than that in the pipeline
(still ingesting, no book.md yet) has not reached the point where its track
would be reviewed, and `_listener_book.py`/`publish_to_listener.py` never
touch it either.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _content_types import BUCKETS  # noqa: E402

REPO_ROOT = SCRIPTS_PODCAST.parents[1]
CONTENT_DIR = REPO_ROOT / "content"

# Mirrors the exact validity check in publish_to_listener.py's `study_track`
# assignment — kept as the same literal set deliberately: that is the one
# place a value is accepted or discarded, and duplicating its logic behind a
# shared constant would be a second thing to keep in sync for a five-item enum
# that changes by a whole taxonomy revision, not by refactor.
VALID_STUDY_TRACKS = {"theology", "history", "shariah", "esoteric", "reality"}


def _composed_books() -> list[Path]:
    """Every `<Bucket>/<slug>/` directory with a composed `book/book.md`."""
    found = []
    for bucket in BUCKETS:
        bucket_dir = CONTENT_DIR / bucket
        if not bucket_dir.is_dir():
            continue
        for slug_dir in sorted(bucket_dir.iterdir()):
            if not slug_dir.is_dir() or slug_dir.name.startswith("_"):
                continue
            if (slug_dir / "book" / "book.md").is_file():
                found.append(slug_dir)
    return found


class TestStudyTrackCoverage(unittest.TestCase):
    def test_finds_composed_books(self):
        # Guards the test itself: if this collapses to zero, every case below
        # passes vacuously and the whole file stops proving anything.
        self.assertGreater(len(_composed_books()), 0)

    def test_every_composed_book_has_a_valid_study_track(self):
        missing = []
        invalid = []
        for book_dir in _composed_books():
            meta_path = book_dir / "meta.yml"
            if not meta_path.is_file():
                missing.append(f"{book_dir.relative_to(CONTENT_DIR)} (no meta.yml)")
                continue
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            track = meta.get("study_track")
            if track is None:
                missing.append(str(book_dir.relative_to(CONTENT_DIR)))
            elif track not in VALID_STUDY_TRACKS:
                invalid.append(f"{book_dir.relative_to(CONTENT_DIR)} -> {track!r}")

        self.assertEqual(
            missing,
            [],
            f"composed books with no study_track in meta.yml (they will show "
            f"under Everything/All tracks but vanish under every specific "
            f"track filter): {missing}",
        )
        self.assertEqual(
            invalid,
            [],
            f"composed books with a study_track publish_to_listener.py would "
            f"silently discard as invalid: {invalid}",
        )


if __name__ == "__main__":
    unittest.main()
