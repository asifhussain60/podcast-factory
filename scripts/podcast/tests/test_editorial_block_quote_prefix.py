"""The editorial block never emits a NESTED blockquote marker.

`format_editorial_block` wraps every wrapped line in `> `. When the model's own
prose already opened a blockquote, the collapse step preserved that marker and
the wrap added a second one, so the composed book carried

    > > **A clarified term for this chapter.** When the boy names …

and both renderers printed the surviving ">" mid-sentence. It reached the
reading edition of the-master-and-the-disciple, chapter 2, and was found by eye
rather than by any gate — hence this test.

The renderers now flatten a nested marker defensively (see the `>+` match in
src/lib/reader/markdown.ts and its scripts/lib/book-html.mjs mirror), but the
emitter is where it must not be produced in the first place.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

# Ensure scripts/podcast/ is importable (this file lives in its tests/ subdir).
_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

from _book_augment import format_editorial_block  # noqa: E402

_NESTED = re.compile(r"(?m)^\s*>\s*>")


class EditorialBlockQuotePrefixTests(unittest.TestCase):
    def test_model_prose_that_opens_its_own_blockquote_is_not_double_wrapped(self):
        # Verbatim shape of the real failure.
        text = (
            "> **A clarified term for this chapter.** When the boy names being "
            '"of the people of the Umma" as one of the three qualities that make '
            'these men worth debating, the word carries more than "community."'
        )
        block = format_editorial_block(text)
        self.assertIsNone(
            _NESTED.search(block),
            f"nested blockquote marker survived:\n{block}",
        )
        # The prose itself is intact — stripping the marker must not eat the text.
        self.assertIn("A clarified term for this chapter.", block)
        self.assertIn("of the people of the Umma", block)

    def test_every_prose_line_carries_exactly_one_marker(self):
        text = "> first line of the note\n> second line of the note"
        block = format_editorial_block(text)
        prose = [ln for ln in block.splitlines() if ln.startswith(">") and "Editorial note" not in ln]
        self.assertTrue(prose, "block produced no prose lines")
        for line in prose:
            self.assertRegex(line, r"^> [^>]", f"line is not singly quoted: {line!r}")

    def test_a_greater_than_sign_inside_the_prose_is_left_alone(self):
        # Only LINE-LEADING markers are stripped; the prose may legitimately
        # contain the character.
        block = format_editorial_block("the ratio a > b holds throughout")
        self.assertIn("a > b", block)

    def test_unquoted_prose_is_unchanged_in_behaviour(self):
        block = format_editorial_block("plain prose with no marker at all")
        self.assertIn("> plain prose with no marker at all", block)
        self.assertIsNone(_NESTED.search(block))


if __name__ == "__main__":
    unittest.main()
