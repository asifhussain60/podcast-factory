"""test_book_translation_purity.py — an English translation blockquote must
carry no embedded Arabic.

Regression tests for the live defect on sharh-al-masail-ghulam-hussain
(2026-08-18): the hadith "The truthful merchant — اَلتَّاجِرُ الصَّدُوقُ — is
raised..." duplicated Arabic already shown in full, directly above, in its
own quotation block.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _book_translation_purity import embedded_arabic_in_translation, translation_purity_findings


class TestEmbeddedArabicInTranslation:
    def test_the_truthful_merchant_regression_is_caught(self):
        line = (
            '> "The truthful merchant — اَلتَّاجِرُ الصَّدُوقُ — is raised on the '
            "Day of Resurrection with الصِّدِّيقِينَ and the martyrs."
        )
        offenders = embedded_arabic_in_translation(line)
        assert len(offenders) == 2

    def test_comma_delimited_embedding_is_also_caught(self):
        line = '> "an arbitrator from his family, أهله, and from her family, أهلها."'
        offenders = embedded_arabic_in_translation(line)
        assert len(offenders) == 2

    def test_a_pure_arabic_quotation_block_is_never_flagged(self):
        line = "> يَا أَيُّهَا النَّبِىُّ اِنَّا اَحْلَلْنَا لَكَ اَزْوَاجَكَ"
        assert embedded_arabic_in_translation(line) == []

    def test_a_legitimate_single_term_gloss_is_never_flagged(self):
        line = '> "as for those women from whom you fear *nushuz* (نُشُوز), admonish them."'
        assert embedded_arabic_in_translation(line) == []

    def test_a_legitimate_honorific_is_never_flagged(self):
        line = '> "Ali (ع) said: seek knowledge."'
        assert embedded_arabic_in_translation(line) == []

    def test_plain_prose_outside_a_blockquote_is_not_scanned(self):
        # The single-term annotation convention lives in running prose too —
        # this module only gates TRANSLATION blockquotes, never that mechanism.
        line = "It is related of al-Husayn ibn 'Ali (ع) that he said this."
        assert embedded_arabic_in_translation(line) == []

    def test_a_clean_english_translation_line_passes(self):
        line = '> "The truthful merchant is raised on the Day of Resurrection with the truthful and the martyrs."'
        assert embedded_arabic_in_translation(line) == []


class TestTranslationPurityFindings:
    def test_reports_line_numbers_for_every_offending_line(self):
        book_md = (
            "# Book\n\n"
            "## Chapter One\n\n"
            'Some prose.\n\n> "A clean translation with no Arabic."\n\n'
            '> "The truthful merchant — اَلتَّاجِرُ الصَّدُوقُ — is raised."\n'
        )
        findings = translation_purity_findings(book_md)
        assert len(findings) == 1
        assert "line 9" in findings[0]
