"""test_islamic_names_harvest.py — the curated proper-name harvest source.

RCA (sharh-al-masail-ghulam-hussain, 2026-08-18): `harvest_gloss_terms.py`
only ever found a term the SOURCE glosses parenthetically, which a translator
never does for a well-known name — so a finished, published-ready book had
"al-Husayn ibn 'Ali" on the page, its honorific "(ع)" fully in script, and
NOT ONE Ahl al-Bayt or Companion name anywhere in the glossary. `_islamic_names`
closes that with a small curated lexicon; `harvest_gloss_terms.harvest()`
merges its candidates in as a second, independent source.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _islamic_names as names
import harvest_gloss_terms as hg


class TestNameCandidates:
    def test_finds_a_bare_name_with_the_definite_article(self):
        text = "It is related of al-Husayn ibn 'Ali that he answered the invitation."
        cands = names.name_candidates(text)
        by_term = {c["term"]: c for c in cands}
        assert "al-Husayn" in by_term
        assert by_term["al-Husayn"]["arabic_script"] == "حسين"
        assert "Ali" in by_term
        assert by_term["Ali"]["arabic_script"] == "علي"

    def test_finds_a_bare_name_without_the_article(self):
        cands = names.name_candidates("Fatima said this of her father.")
        by_term = {c["term"]: c for c in cands}
        assert by_term["Fatima"]["arabic_script"] == "فاطمة"

    def test_counts_repeated_mentions_of_the_same_spelling(self):
        cands = names.name_candidates("Hasan spoke. Later, Hasan spoke again.")
        assert cands[0]["term"] == "Hasan"
        assert cands[0]["count"] == 2

    def test_a_two_word_root_claims_its_span_before_the_shorter_root_inside_it(self):
        # "Abu Bakr" must not also register a spurious standalone "Bakr" hit —
        # there is no such root, but the guard is what a longer curated root
        # existing alongside a shorter one depends on.
        cands = names.name_candidates("Abu Bakr entered.")
        terms = {c["term"] for c in cands}
        assert terms == {"Abu Bakr"}

    def test_does_not_match_the_name_inside_a_longer_word(self):
        cands = names.name_candidates("Alignment and Alibaba are not names.")
        assert cands == []

    def test_lowercase_spelling_is_never_matched(self):
        # "ali" lowercase is not a confident signal — only the capitalized form
        # (with or without a lowercase al- prefix) is trusted.
        cands = names.name_candidates("this alias is not a name")
        assert cands == []


class TestHarvestMergesNameCandidates:
    def _write_glossary(self, path: Path, entries: list[dict]) -> None:
        from _glossary_io import save_glossary

        path.parent.mkdir(parents=True, exist_ok=True)
        save_glossary(path, entries, {"schema_version": 1})

    def test_a_curated_name_is_harvested_with_its_script_already_filled(self, tmp_path):
        book_dir = tmp_path / "some-book"
        book_md = book_dir / "book" / "book.md"
        book_md.parent.mkdir(parents=True)
        book_md.write_text(
            "## Chapter\n\nIt is related of al-Husayn ibn 'Ali that he answered the invitation.\n",
            encoding="utf-8",
        )
        self._write_glossary(book_dir / "_system" / "glossary.yml", [])

        plan = hg.harvest(book_dir)
        new_terms = {c["term"]: c for c in plan["new"]}
        assert "al-Husayn" in new_terms
        assert new_terms["al-Husayn"]["arabic_script"] == "حسين"

        added = hg.apply(book_dir, plan)
        assert added >= 1

        entries, _top = hg.load_glossary(book_dir / "_system" / "glossary.yml")
        by_phon = {e["phonetic"]: e for e in entries}
        assert by_phon["al-Husayn"]["arabic_script"] == "حسين"

    def test_an_already_known_name_is_not_re_harvested(self, tmp_path):
        book_dir = tmp_path / "some-book"
        book_md = book_dir / "book" / "book.md"
        book_md.parent.mkdir(parents=True)
        book_md.write_text("## Chapter\n\nAli said this.\n", encoding="utf-8")
        self._write_glossary(
            book_dir / "_system" / "glossary.yml",
            [{"phonetic": "Ali", "transliteration": "Ali", "arabic_script": "علي"}],
        )

        plan = hg.harvest(book_dir)
        assert "Ali" not in {c["term"] for c in plan["new"]}
