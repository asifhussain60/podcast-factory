#!/usr/bin/env python3
"""The four-quotation-card contract: that it holds today, and that it can FAIL.

The second half is the point. This repo's recurring defect is a gate that reports clean
over a rule it never runs — three instances were found in one audit on 2026-08-06 — and a
contract asserted only against a repo that already satisfies it is exactly that shape. So
every rule is also fired against a copy of the file with its declaration removed, and the
test fails unless the finding appears.

The mutations are deliberately CRUDE (delete the line, delete the token). A subtle one
would test the regex; a crude one tests the thing the check is for — somebody deleting a
rule while tidying, or a renderer stopping emitting a class.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

import _quote_cards  # noqa: E402
from _quote_cards import (  # noqa: E402
    DECLARABLE,
    KINDS,
    card_rule_findings,
    guarantee_for,
    orphaned_quote_kinds,
    quote_kind_key,
    read_quote_kind,
)

#: A book big enough to carry the two failure modes: a chapter whose heading can be
#: renamed, and a quotation whose first line can be edited.
BOOK_MD = """# A Book

## 1. The First Chapter

A lead-in sentence.

> مَنْ جَاوَزَ الْأَرْبَعِينَ
> and its English rendering.

## 2. The Second Chapter

Another lead-in.

> سَهَرُ الْعُيُونِ * وَ بُكَاؤُهُنَّ
"""


def _book(tmp_path: Path, declarations: dict) -> Path:
    book = tmp_path / "a-book"
    (book / "book").mkdir(parents=True)
    (book / "_system").mkdir()
    (book / "book" / "book.md").write_text(BOOK_MD, encoding="utf-8")
    (book / "_system" / "quote-kind.json").write_text(
        json.dumps({"schema": "book.quote-kind/v1", "chapters": declarations}, ensure_ascii=False),
        encoding="utf-8",
    )
    return book


# ── the contract, as the repo stands ─────────────────────────────────────────


def test_the_card_design_is_intact_in_this_repo():
    """The four cards the specimen shows can be drawn. A failure here names what is gone."""
    findings = card_rule_findings()
    assert findings == [], "\n".join(f"{i}  {p}: {m}" for i, p, m in findings)


def test_every_rule_carries_a_reason_a_report_can_print():
    for rule in _quote_cards._card_rules():
        assert guarantee_for(rule["id"]), rule["id"]
        assert rule["requirements"], rule["id"]


def test_rule_ids_are_unique():
    ids = [r["id"] for r in _quote_cards._card_rules()]
    assert len(ids) == len(set(ids))


# ── each rule can fail ───────────────────────────────────────────────────────


@pytest.mark.parametrize("rule", _quote_cards._card_rules(), ids=lambda r: r["id"])
def test_each_requirement_fires_when_its_declaration_is_removed(rule, tmp_path, monkeypatch):
    """Delete what a requirement matches; the check must report that requirement.

    The file is copied and the module's path constant repointed, so nothing under
    `plan-dashboard/` is touched — the mutation lives and dies inside tmp_path.
    """
    original = rule["path"].read_text(encoding="utf-8")
    constant = next(
        name
        for name in ("CSS", "PRINT_RENDERER", "SCREEN_RENDERER", "SCREEN_CARD_BAND", "PDF_DRIVER", "SPECIMEN")
        if getattr(_quote_cards, name) == rule["path"]
    )

    for label, pattern in rule["requirements"]:
        # EVERY occurrence, not the first. A declaration usually appears in several
        # rules — the plate, the ink, the dark-paper lift — and removing one of them
        # leaves the check able to find it elsewhere and the mutation proving nothing.
        wounded = re.sub(pattern, "/* removed */", original, flags=re.S)
        assert wounded != original, f"{rule['id']}: {label} — the pattern matches nothing to remove"
        target = tmp_path / f"{rule['id']}-{abs(hash(label))}.txt"
        target.write_text(wounded, encoding="utf-8")
        monkeypatch.setattr(_quote_cards, constant, target)
        reported = [(i, m) for i, _, m in card_rule_findings() if i == rule["id"]]
        assert (rule["id"], label) in reported, f"{rule['id']} stayed silent with {label!r} deleted"


def test_a_missing_file_is_a_finding_not_a_crash(tmp_path, monkeypatch):
    """A stylesheet moved out from under the check must be reported, never swallowed."""
    monkeypatch.setattr(_quote_cards, "CSS", tmp_path / "gone.css")
    assert any(path.endswith("gone.css") and why == "the file is missing" for _, path, why in card_rule_findings())


# ── the per-book half ────────────────────────────────────────────────────────


def test_a_book_whose_declarations_all_match_reports_nothing(tmp_path):
    book = _book(tmp_path, {"the first chapter": {"مَنْ جَاوَزَ الْأَرْبَعِينَ": "hadith"}})
    assert orphaned_quote_kinds(book) == []


def test_an_edited_first_line_orphans_its_declaration(tmp_path):
    """The failure `quote-kind.mjs` names: edit the line and the card silently reverts."""
    book = _book(tmp_path, {"the first chapter": {"a line nobody wrote": "hadith"}})
    orphans = orphaned_quote_kinds(book)
    assert [(o[1], o[2]) for o in orphans] == [("a line nobody wrote", "hadith")]
    assert "opens with this line" in orphans[0][3]


def test_a_renamed_chapter_orphans_every_declaration_under_it(tmp_path):
    book = _book(tmp_path, {"a chapter that was renamed": {"مَنْ جَاوَزَ الْأَرْبَعِينَ": "hadith"}})
    orphans = orphaned_quote_kinds(book)
    assert len(orphans) == 1
    assert "no chapter has this key" in orphans[0][3]


def test_a_repair_that_rewrites_a_quotations_first_line_is_caught(tmp_path):
    """`compose_fix --fix` is one of the things that causes this, which is why it checks.

    Deleting a duplicated Arabic run off the top of a blockquote re-keys the declaration
    filed under it.
    """
    book = _book(tmp_path, {"the first chapter": {"مَنْ جَاوَزَ الْأَرْبَعِينَ": "hadith"}})
    md = book / "book" / "book.md"
    md.write_text(md.read_text(encoding="utf-8").replace("> مَنْ جَاوَزَ الْأَرْبَعِينَ\n", ""), encoding="utf-8")
    assert len(orphaned_quote_kinds(book)) == 1


def test_a_book_with_no_declarations_is_not_a_finding(tmp_path):
    book = _book(tmp_path, {})
    (book / "_system" / "quote-kind.json").unlink()
    assert orphaned_quote_kinds(book) == []


def test_a_malformed_store_yields_nothing_rather_than_raising(tmp_path):
    """The reader's own tolerance: an edition renders every quotation in the default card
    rather than failing to render, so this must not be the one place that throws."""
    book = _book(tmp_path, {})
    (book / "_system" / "quote-kind.json").write_text("{ not json", encoding="utf-8")
    assert read_quote_kind(book) == {}
    assert orphaned_quote_kinds(book) == []


def test_an_undeclarable_kind_is_dropped(tmp_path):
    """`quran` is the audit's answer and can never be declared by hand — a store that
    asserts it is ignored, not honoured, or there would be two answers to keep in step."""
    book = _book(tmp_path, {"the first chapter": {"مَنْ جَاوَزَ الْأَرْبَعِينَ": "quran"}})
    assert read_quote_kind(book) == {}


# ── the key, which is a mirror ───────────────────────────────────────────────


def test_the_key_is_the_first_non_empty_line_not_the_joined_paragraph():
    """Mirrors `quoteKindKey`. Keying on the join is the exact bug that made a declared
    three-bayt poem print as a plain saying until 2026-08-09."""
    assert quote_kind_key(["", "  first line  ", "second line"]) == "first line"
    assert quote_kind_key([]) == ""
    assert quote_kind_key(["", "  "]) == ""


def test_the_declarable_kinds_match_the_javascript_that_owns_them():
    """`QUOTE_KIND_IDS` in quote-kind.mjs is the one definition; drift means a kind a
    person can declare in the Composer and this check silently discards."""
    js = (REPO / "plan-dashboard" / "scripts" / "lib" / "quote-kind.mjs").read_text(encoding="utf-8")
    declared = re.search(r"QUOTE_KIND_IDS\s*=\s*\[([^\]]*)\]", js).group(1)
    assert sorted(re.findall(r'"([^"]+)"', declared)) == sorted(DECLARABLE)


def test_every_kind_has_an_ink_token():
    assert sorted(_quote_cards.INK) == sorted(KINDS)


# ── the merge half: which declared groups no longer hold together ─────────────

from _quote_cards import orphaned_quote_groups, read_quote_groups  # noqa: E402

#: A chapter with one quote fragment, its tight gloss, and a second quote — the
#: shape a real group declares over.
GROUP_BOOK_MD = """# A Book

## 1. The First Chapter

A lead-in sentence.

> مَنْ جَاوَزَ الْأَرْبَعِينَ

A tight gloss of that line.

> وَ سَهَرُ الْعُيُونِ

## 2. The Second Chapter

Nothing declared here.
"""


def _group_book(tmp_path: Path, chapters: dict) -> Path:
    book = tmp_path / "a-book"
    (book / "book").mkdir(parents=True)
    (book / "_system").mkdir()
    (book / "book" / "book.md").write_text(GROUP_BOOK_MD, encoding="utf-8")
    (book / "_system" / "quote-groups.json").write_text(
        json.dumps({"schema": "book.quote-groups/v1", "chapters": chapters}, ensure_ascii=False),
        encoding="utf-8",
    )
    return book


def test_a_book_whose_group_members_all_match_reports_nothing(tmp_path):
    book = _group_book(
        tmp_path,
        {
            "the first chapter": {
                "مَنْ جَاوَزَ الْأَرْبَعِينَ": {"group": "g1", "type": "quote"},
                "A tight gloss of that line.": {"group": "g1", "type": "gloss"},
                "وَ سَهَرُ الْعُيُونِ": {"group": "g1", "type": "quote"},
            }
        },
    )
    assert orphaned_quote_groups(book) == []


def test_an_edited_member_orphans_its_group_entry(tmp_path):
    """Editing a member's line out from under its declaration reports it, the same
    silent-degrade shape as an orphaned kind."""
    book = _group_book(
        tmp_path,
        {
            "the first chapter": {
                "مَنْ جَاوَزَ الْأَرْبَعِينَ": {"group": "g1", "type": "quote"},
                "This gloss no longer matches anything.": {"group": "g1", "type": "gloss"},
                "وَ سَهَرُ الْعُيُونِ": {"group": "g1", "type": "quote"},
            }
        },
    )
    orphans = orphaned_quote_groups(book)
    assert len(orphans) == 1
    chapter, key, group, why = orphans[0]
    assert chapter == "the first chapter"
    assert key == "This gloss no longer matches anything."
    assert group == "g1"
    assert "no gloss" in why


def test_a_group_reduced_to_one_survivor_is_reported_as_inert(tmp_path):
    """Only one member of the group still exists — not wrong, just a no-op merge,
    and worth telling a person rather than letting it sit unnoticed."""
    book = _group_book(
        tmp_path,
        {
            "the first chapter": {
                "مَنْ جَاوَزَ الْأَرْبَعِينَ": {"group": "g1", "type": "quote"},
                "its partner was re-keyed away": {"group": "g1", "type": "gloss"},
            }
        },
    )
    orphans = orphaned_quote_groups(book)
    # The gloss is itself an orphan (no such paragraph exists), and the ONE
    # surviving member (the quote line) is reported as a singleton.
    reasons = {o[3] for o in orphans}
    assert any("no-op" in r for r in reasons)


def test_a_renamed_chapter_orphans_every_member_under_it(tmp_path):
    book = _group_book(
        tmp_path,
        {
            "a chapter that no longer exists": {
                "مَنْ جَاوَزَ الْأَرْبَعِينَ": {"group": "g1", "type": "quote"},
                "وَ سَهَرُ الْعُيُونِ": {"group": "g1", "type": "quote"},
            }
        },
    )
    orphans = orphaned_quote_groups(book)
    assert len(orphans) == 2
    assert all("no chapter" in o[3] for o in orphans)


def test_a_book_with_no_group_declarations_is_not_a_finding(tmp_path):
    book = _group_book(tmp_path, {})
    (book / "_system" / "quote-groups.json").unlink()
    assert orphaned_quote_groups(book) == []


def test_a_malformed_groups_store_yields_nothing_rather_than_raising(tmp_path):
    book = _group_book(tmp_path, {})
    (book / "_system" / "quote-groups.json").write_text("{ not json", encoding="utf-8")
    assert read_quote_groups(book) == {}
    assert orphaned_quote_groups(book) == []


def test_a_declaration_with_no_group_id_is_dropped(tmp_path):
    """An empty/missing `group` is the same as no declaration at all — matches
    writeQuoteGroup's own "" -> delete convention on the JS side."""
    book = _group_book(
        tmp_path,
        {"the first chapter": {"مَنْ جَاوَزَ الْأَرْبَعِينَ": {"group": "", "type": "quote"}}},
    )
    assert read_quote_groups(book) == {}


def test_type_is_preserved_per_member_not_inferred(tmp_path):
    """A quote member and a gloss member in the same group keep their own declared
    `type` — the renderer's merge pass reads this to decide whether to reuse the
    member's own rendering (quote) or synthesize a `.tr` paragraph from it (gloss),
    so a flipped type would draw the wrong markup for that member."""
    book = _group_book(
        tmp_path,
        {
            "the first chapter": {
                "مَنْ جَاوَزَ الْأَرْبَعِينَ": {"group": "g1", "type": "quote"},
                "A tight gloss of that line.": {"group": "g1", "type": "gloss"},
            }
        },
    )
    read = read_quote_groups(book)
    assert read["the first chapter"]["مَنْ جَاوَزَ الْأَرْبَعِينَ"] == ("g1", "quote")
    assert read["the first chapter"]["A tight gloss of that line."] == ("g1", "gloss")
