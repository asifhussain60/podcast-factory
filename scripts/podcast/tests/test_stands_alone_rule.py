#!/usr/bin/env python3
"""Every book's contract author is told the rule its contracts are judged by.

`_extract_contract` REJECTS a contract carrying a cross-episode reference — and it
rejects it at extract time, after the chapter has been designed, enriched and paid
for. The instruction that prevents that used to live inside the volume-allocation
block, which is emitted only when `_system/_volume-split.json` exists. So every
single-volume book authored contracts with no idea the rule existed.

Degrees of Excellence lost chapter 3 to it mid-run on 2026-07-31, on a tone
constraint reading "it belongs to the next episode" — a phrase the author was never
warned about and the validator has forbidden all along.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _extract_contract import CONTRACT_META_PROSE_TELLS, stands_alone_rule


class TheRuleQuotesTheGateTests(unittest.TestCase):
    def test_the_phrase_that_cost_a_chapter_is_named(self) -> None:
        self.assertIn("next episode", stands_alone_rule())

    def test_it_is_built_from_the_enforced_list_not_a_restatement(self) -> None:
        # A hand-written copy is how the author gets told one list while the gate
        # enforces another. The first tells must appear verbatim.
        rule = stands_alone_rule()
        for tell in CONTRACT_META_PROSE_TELLS[:6]:
            self.assertIn(tell, rule, f"the prompt no longer quotes the enforced tell {tell!r}")

    def test_it_names_the_regex_case_too(self) -> None:
        self.assertIn("EP##", stands_alone_rule())

    def test_it_says_what_to_do_instead_not_only_what_to_avoid(self) -> None:
        # The failing contract had a legitimate intent — keep a teaching out of
        # this episode. A rule that only forbids leaves the author no way to say it.
        self.assertIn("out of scope", stands_alone_rule().lower())


class TheRuleReachesEveryBookTests(unittest.TestCase):
    def test_phase_0d_injects_it_unconditionally(self) -> None:
        text = (SCRIPTS_PODCAST / "_authoring" / "_chapter_design.py").read_text(encoding="utf-8")
        self.assertIn("stands_alone_rule()", text)

    def test_it_is_NOT_inside_the_volume_allocation_branch(self) -> None:
        """The regression that hid it from single-volume books for good."""
        text = (SCRIPTS_PODCAST / "_authoring" / "_chapter_design.py").read_text(encoding="utf-8")
        alloc = text.find("def _volume_allocation")
        self.assertGreater(alloc, 0)
        # Find the next top-level def after it — the allocation function's body.
        rest = text[alloc + 1 :]
        end = alloc + 1 + (re.search(r"\ndef ", rest).start() if re.search(r"\ndef ", rest) else len(rest))
        self.assertNotIn(
            "stands_alone_rule()",
            text[alloc:end],
            "the rule is inside _volume_allocation again — single-volume books lose it",
        )

    def test_the_injection_precedes_the_allocation_block(self) -> None:
        text = (SCRIPTS_PODCAST / "_authoring" / "_chapter_design.py").read_text(encoding="utf-8")
        inject = text.find("stands_alone_rule()\n")
        alloc_call = text.find("_volume_allocation(book_dir)")
        self.assertGreater(inject, 0)
        self.assertGreater(alloc_call, 0)
        self.assertLess(inject, alloc_call, "the rule must not depend on the allocation path running")


if __name__ == "__main__":
    unittest.main()
