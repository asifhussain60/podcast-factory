#!/usr/bin/env python3
"""The scaffold must write where every reader looks.

`scaffold_book.book_dir_for` hardcoded `content/drafts/<category>/<slug>` — the
layout retired on 2026-06-04 — while `phases/scaffold.phase_scaffold` asserted
`_paths.content_dir(...)` afterwards. Every new-book intake therefore died at the
scaffold step with "scaffold did not create ...", leaving a stranded directory in
the legacy tree. Fixed 2026-07-31; these tests pin both halves of that failure.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import scaffold_book
from _paths import content_dir


class ScaffoldTargetTests(unittest.TestCase):
    def test_target_is_the_shared_resolver_not_a_second_opinion(self) -> None:
        # The exact equality phases/scaffold.py checks after shelling out.
        for category in ("books", "lectures"):
            self.assertEqual(
                scaffold_book.book_dir_for(category, "some-slug"),
                content_dir("some-slug", category=category),
                f"scaffold target drifted from the resolver for category={category}",
            )

    def test_target_is_bucket_first_never_the_retired_drafts_tree(self) -> None:
        target = scaffold_book.book_dir_for("books", "degrees-of-excellence")
        self.assertNotIn(
            "drafts",
            target.parts,
            "scaffold regressed to the retired content/drafts/ layout",
        )
        self.assertEqual(target.parts[-2:], ("Islamic", "degrees-of-excellence"))

    def test_no_writes_to_the_retired_content_podcast_folder(self) -> None:
        # content/podcast/ was deleted as stale in 6105fb27; the books.md index
        # append kept resurrecting it on every scaffold.
        text = (SCRIPTS_PODCAST / "scaffold_book.py").read_text(encoding="utf-8")
        self.assertNotIn("BOOKS_INDEX", text, "scaffold re-grew the retired books.md index")
        self.assertNotIn(
            'REPO_ROOT / "content" / "drafts"',
            text,
            "scaffold re-grew a hardcoded legacy content root",
        )


if __name__ == "__main__":
    unittest.main()
