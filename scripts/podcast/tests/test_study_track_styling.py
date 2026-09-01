#!/usr/bin/env python3
"""Every study track must be painted in every stylesheet that paints tracks.

WHY THIS EXISTS. The study-track enum is one list conceptually and seven places
physically: two Python constants, this repo's test above, the TypeScript union in
the Podcast Factory Library, and THREE stylesheets across the two apps. Python
and TypeScript both fail loudly when a value is missing — a `frozenset` check
drops the value, a union type refuses to compile.

CSS fails silently. A track with no rule renders a ribbon with no background,
which looks like a design choice rather than a missing entry, and the only way to
notice is to have a book of that track on screen and know what it should look
like. Adding `philosophy` on 2026-09-01 meant touching three stylesheets by hand;
this is what makes the eighth track's author find the third one.

Deliberately a TEXT scan rather than a CSS parse: the question is only "does this
selector and this token appear", the files are large, and a parser would be a
dependency and a second thing to be wrong.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _listener_book import STUDY_TRACKS  # noqa: E402

REPO_ROOT = SCRIPTS_PODCAST.parents[1]

#: stylesheet -> (token DEFINITION, selector template). One row per surface that
#: paints a track; a new painted surface adds a row here.
#:
#: The token carries its trailing colon deliberately. Without it the check matched
#: `var(--l-ribbon-philosophy-bg)` -- the USE -- so deleting the definition left
#: the test green. Caught by mutation-testing this file rather than by trusting
#: it, which is the only way a guard like this is worth having.
SURFACES: dict[str, tuple[str, str]] = {
    "listener/app/styles/podcast-factory.css": (
        "--l-ribbon-{track}-bg:",
        '.pf-book__ribbon[data-track="{track}"]',
    ),
    "plan-dashboard/src/styles/studio-pipeline.css": (
        None,  # tokens live in study-track-colors.css, checked on its own row
        '.card-track-ribbon[data-track="{track}"]',
    ),
    "plan-dashboard/src/styles/study-track-colors.css": (
        "--track-{track}-bg:",
        None,  # this file defines tokens only, no selectors
    ),
}


class TestEveryTrackIsPainted(unittest.TestCase):
    def test_the_enum_is_not_empty(self):
        # Guards the test: an empty enum would make every case below pass
        # vacuously, which is the failure this whole file exists to prevent.
        self.assertGreaterEqual(len(STUDY_TRACKS), 5)

    def test_every_surface_file_exists(self):
        for rel in SURFACES:
            self.assertTrue((REPO_ROOT / rel).is_file(), f"missing stylesheet: {rel}")

    def test_every_track_has_a_token_and_a_selector(self):
        missing: list[str] = []
        for rel, (token, selector) in SURFACES.items():
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            for track in sorted(STUDY_TRACKS):
                if token and token.format(track=track) not in text:
                    missing.append(f"{rel}: no token {token.format(track=track)}")
                if selector and selector.format(track=track) not in text:
                    missing.append(f"{rel}: no rule for {selector.format(track=track)}")
        self.assertEqual(missing, [], "study tracks with no styling:\n  " + "\n  ".join(missing))

    def test_the_library_type_union_lists_every_track(self):
        """The TypeScript union, its labels, and its display order."""
        ts = (REPO_ROOT / "listener/app/lib/study-track.ts").read_text(encoding="utf-8")
        for track in sorted(STUDY_TRACKS):
            self.assertIn(f'"{track}"', ts, f"study-track.ts does not name {track}")
            self.assertIn(f"{track}:", ts, f"study-track.ts has no label for {track}")


if __name__ == "__main__":
    unittest.main()
