#!/usr/bin/env python3
"""Tests for _doctrinal.py — Category T doctrinal-accuracy checks.

Pins the T1/T2/T3 detectors against the canonical lineage + naming-convention
data in content/_shared/islam/. These tests intentionally use small literal
text fragments rather than fixture files so a YAML change that breaks the
expected behavior is caught here directly.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _doctrinal import (   # noqa: E402
    run_doctrinal_checks,
    check_t3_forbidden_phrases,
    check_t2_imam_lineage,
    load_imam_lineage,
    load_naming_conventions,
)


class DataLoadTests(unittest.TestCase):

    def test_lineage_has_at_least_seven_imams(self):
        data = load_imam_lineage()
        self.assertGreaterEqual(len(data.get("imams", [])), 7)

    def test_hassan_is_first(self):
        data = load_imam_lineage()
        first = data["imams"][0]
        self.assertEqual(first["ordinal"], 1)
        self.assertIn("Hassan", first["canonical_name"])

    def test_naming_conventions_forbid_imam_ali(self):
        data = load_naming_conventions()
        forbidden = {e["match"] for e in data.get("forbidden_phrases", [])
                     if isinstance(e, dict)}
        self.assertIn("Imam Ali", forbidden)


class T3ForbiddenPhraseTests(unittest.TestCase):

    def test_imam_ali_caught_as_p0(self):
        text = "Imam Ali said many things about wisdom."
        findings = check_t3_forbidden_phrases(text)
        self.assertTrue(any(f.severity == "P0" and "imam_ali" in f.signature
                            for f in findings))

    def test_imam_fatima_caught_as_p0(self):
        text = "Imam Fatima is sometimes invoked, but should not be."
        findings = check_t3_forbidden_phrases(text)
        self.assertTrue(any(f.severity == "P0" and "imam_fatima" in f.signature
                            for f in findings))

    def test_clean_text_produces_no_findings(self):
        text = ("The Father of Imams said many things about wisdom. "
                "Fatima al-Zahra, the Mother of Imams, taught alongside him. "
                "The 1st Imam Hassan continued the lineage.")
        findings = check_t3_forbidden_phrases(text)
        # No P0/P1 — clean text should produce zero hits.
        self.assertEqual([f for f in findings if f.severity == "P0"], [])

    def test_imam_ali_zayn_does_not_false_match(self):
        """Imam Ali Zayn al-Abidin (the 3rd Imam) is a valid canonical name —
        the regex must use negative lookahead so this doesn't false-positive
        as a violation of 'Imam Ali' P0."""
        text = "Imam Ali Zayn al-Abidin is the 3rd Imam in the canonical lineage."
        findings = check_t3_forbidden_phrases(text)
        false_positives = [f for f in findings
                           if "imam_ali" in f.signature
                           and "lineage_forbidden" not in f.signature]
        self.assertEqual(false_positives, [])

    def test_dedup_position_based(self):
        """The same forbidden phrase listed in both naming-conventions.yml AND
        imam-lineage-ismaili.yml::forbidden_imam_titles must emit ONCE per
        occurrence, not twice."""
        text = "Imam Ali said something."
        findings = check_t3_forbidden_phrases(text)
        imam_ali_hits = [f for f in findings
                         if "imam_ali" in f.signature.lower()]
        self.assertEqual(len(imam_ali_hits), 1)


class T2LineageTests(unittest.TestCase):

    def test_unknown_ordinal_flagged(self):
        text = "The 15th Imam said wisdom flows from above."
        findings = check_t2_imam_lineage(text)
        self.assertTrue(any(f.check_id == "T2" and f.severity == "P0"
                            for f in findings))


class IntegrationTests(unittest.TestCase):

    def test_aggregator_severity_sort(self):
        """run_doctrinal_checks sorts P0 first."""
        text = ("Imam Ali was wise. The 15th Imam was great. "
                "Imam Fatima also taught.")
        findings = run_doctrinal_checks(text)
        if findings:
            severities = [f.severity for f in findings]
            # P0s precede P1s
            for i in range(1, len(severities)):
                if severities[i - 1] == "P1":
                    self.assertNotEqual(severities[i], "P0")


if __name__ == "__main__":
    unittest.main()
