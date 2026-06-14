"""Tests for FIX 14 — unified contract validation (one validator, four gates).

Each failure-class test reproduces the REAL shape that cost money on the
the-master-and-the-disciple run (2026-06-10), where 7 of 20 chapters were lost
to three contract defects caught at three different, increasingly expensive
layers:

  (a) episode_format=debate with no `debate:` block  — caught only at extract
  (b) slug/chapter_ref renamed without the chapter file — caught at extract
  (c) debate.host_a/host_b.role outside the R-HOST-ROLE-PARITY enums
      ('advocate — voices Salih' instead of 'master') — caught only by
      pipeline_lint AFTER an ~11-minute framing authoring

After FIX 14 all three must surface at EVERY gate, starting with the $0
pre-loop smoke gate (phases/preflight_chapter.smoke_check_book).

Covers:
  - _contract_validation.validate_contract_full  (the one validator)
  - _contract_validation.validate_book_contracts (book-level sweep)
  - phases/preflight_chapter.smoke_check_book    ($0 gate surfaces findings)
  - phases/initial_driver._gate_0d_contracts     (0d fails loudly before 0e)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

from _contract_validation import (  # noqa: E402
    validate_contract_full,
    validate_book_contracts,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────────────

def _valid_contract(slug: str = "alpha", n: int = 1, **overrides) -> dict:
    """A minimal contract that passes every gate (green path)."""
    c = {
        "chapter_ref": f"ch{n:02d}-{slug}",
        "slug": slug,
        "source_type": "book-chapter",
        "episode_number": n,
        "title": f"Test Chapter {slug.title()}",
        "audience": "Listeners new to the test book.",
        "angle": "faithful_exposition",
        "episode_format": "deep_dive",
        "host_dynamic": "curious_mind + scholar_companion",
        "adaptation_mode": "faithful",
        "key_tensions": ["The first tension."],
    }
    c.update(overrides)
    return c


def _valid_debate_block(role_a: str = "master", role_b: str = "debater") -> dict:
    """A complete debate block in tonight's repaired (passing) shape."""
    return {
        "proposition": ("True seeking begins with demolition: the seeker's cup "
                        "must be emptied before it can be refilled."),
        "host_a": {
            "role": role_a,
            "position": "The seeker must first be emptied of borrowed certainty.",
            "source_moves": ["The three kinds of seeker.",
                             "The naming of kasrah and the mukasir."],
        },
        "host_b": {
            "role": role_b,
            "position": "A scholar's learning qualifies him to weigh claims unaided.",
            "source_moves": ["The threshold riddle read as news of death."],
        },
        "resolution": "host_b_concedes",
    }


def _make_book(tmp: Path, slugs: list[str]) -> Path:
    """Book dir with chapters/ch0N-<slug>.txt; contracts written by callers."""
    book = tmp / "book"
    (book / "chapters").mkdir(parents=True)
    (book / "chapter-contracts").mkdir(parents=True)
    for i, s in enumerate(slugs, 1):
        (book / "chapters" / f"ch{i:02d}-{s}.txt").write_text(
            "word " * 600, encoding="utf-8")
    return book


def _contract_yaml(slug: str, n: int, *, episode_format: str = "deep_dive",
                   debate_yaml: str = "", title: str | None = None) -> str:
    """YAML text parseable by BOTH PyYAML (smoke gate) and _extract_yaml.load_yaml."""
    title = title or f"Test Chapter {slug.title()}"
    return (
        f"chapter_ref: ch{n:02d}-{slug}\n"
        f"slug: {slug}\n"
        f"source_type: book-chapter\n"
        f"episode_number: {n}\n"
        f"title: {title}\n"
        f"audience: Listeners new to the test book.\n"
        f"angle: faithful_exposition\n"
        f"episode_format: {episode_format}\n"
        f"host_dynamic: curious_mind + scholar_companion\n"
        f"adaptation_mode: faithful\n"
        f"key_tensions:\n"
        f"  - The first tension of chapter {n}.\n"
        + debate_yaml
    )


_DEBATE_YAML_OK = (
    "debate:\n"
    "  proposition: >\n"
    "    True seeking begins with demolition of borrowed certainty.\n"
    "  host_a:\n"
    "    role: master\n"
    "    position: >\n"
    "      The seeker must first be emptied.\n"
    "    source_moves:\n"
    "      - The three kinds of seeker.\n"
    "  host_b:\n"
    "    role: debater\n"
    "    position: >\n"
    "      Learning qualifies the scholar to weigh claims unaided.\n"
    "    source_moves:\n"
    "      - The threshold riddle.\n"
    "  resolution: host_b_concedes\n"
)

_DEBATE_YAML_BAD_ROLE = _DEBATE_YAML_OK.replace(
    "    role: master\n", "    role: advocate — voices Salih\n")


# ─────────────────────────────────────────────────────────────────────────────
# 1. The one validator — validate_contract_full
# ─────────────────────────────────────────────────────────────────────────────

class GreenPathTests(unittest.TestCase):
    def test_valid_deep_dive_contract_zero_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            findings = validate_contract_full(_valid_contract("alpha"), None, book)
            self.assertEqual(findings, [], findings)

    def test_valid_debate_contract_zero_findings(self):
        """Tonight's repaired shape — master/debater roles, full block — passes."""
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            contract = _valid_contract(
                "alpha", episode_format="debate", debate=_valid_debate_block())
            findings = validate_contract_full(contract, None, book)
            self.assertEqual(findings, [], findings)

    def test_on_disk_contract_with_unique_title_zero_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha", "beta"])
            cpath = book / "chapter-contracts" / "alpha.yml"
            cpath.write_text(_contract_yaml("alpha", 1), encoding="utf-8")
            (book / "chapter-contracts" / "beta.yml").write_text(
                _contract_yaml("beta", 2), encoding="utf-8")
            findings = validate_contract_full(
                _valid_contract("alpha"), None, book, contract_path=cpath)
            self.assertEqual(findings, [], findings)


class DebateNoBlockTests(unittest.TestCase):
    """Failure class (a): episode_format=debate with no debate: block."""

    def test_debate_with_null_block_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            contract = _valid_contract("alpha", episode_format="debate", debate=None)
            findings = validate_contract_full(contract, None, book)
            joined = "\n".join(findings)
            self.assertIn("contract.debate is null/missing", joined)

    def test_debate_with_missing_key_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            contract = _valid_contract("alpha", episode_format="debate")
            contract.pop("debate", None)
            findings = validate_contract_full(contract, None, book)
            self.assertTrue(any("contract.debate is null/missing" in f for f in findings),
                            findings)

    def test_debate_partial_block_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            debate = _valid_debate_block()
            del debate["host_b"]
            debate["host_a"]["source_moves"] = []
            contract = _valid_contract("alpha", episode_format="debate", debate=debate)
            findings = validate_contract_full(contract, None, book)
            joined = "\n".join(findings)
            self.assertIn("contract.debate.host_b is missing or empty", joined)
            self.assertIn("source_moves must be a non-empty list", joined)

    def test_debate_proposition_question_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            debate = _valid_debate_block()
            debate["proposition"] = "Is demolition the right way to begin seeking?"
            contract = _valid_contract("alpha", episode_format="debate", debate=debate)
            findings = validate_contract_full(contract, None, book)
            self.assertTrue(any("not a question" in f for f in findings), findings)

    def test_debate_bad_resolution_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            debate = _valid_debate_block()
            debate["resolution"] = "host_b_wins"
            contract = _valid_contract("alpha", episode_format="debate", debate=debate)
            findings = validate_contract_full(contract, None, book)
            self.assertTrue(any("contract.debate.resolution" in f for f in findings),
                            findings)


class SlugMismatchTests(unittest.TestCase):
    """Failure class (b): slug/chapter_ref renamed without the chapter file."""

    def test_renamed_slug_without_chapter_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["air-and-the-instance-beyond-air"])
            contract = _valid_contract("air-and-the-instance-beyond-air-renamed", 7)
            findings = validate_contract_full(contract, None, book)
            self.assertTrue(any("has no chapter file" in f for f in findings), findings)

    def test_explicit_chapter_path_slug_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            chapter = book / "chapters" / "ch01-alpha.txt"
            contract = _valid_contract("beta")
            findings = validate_contract_full(contract, chapter, book)
            self.assertTrue(
                any("does not match chapter slug" in f for f in findings), findings)

    def test_chapter_ref_stem_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            contract = _valid_contract("alpha", chapter_ref="ch99-alpha-old")
            findings = validate_contract_full(contract, None, book)
            self.assertTrue(
                any("contract.chapter_ref" in f and "does not match" in f
                    for f in findings), findings)


class HostRoleEnumTests(unittest.TestCase):
    """Failure class (c): descriptive role labels vs the R-HOST-ROLE-PARITY enums."""

    def test_master_and_debater_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            contract = _valid_contract(
                "alpha", episode_format="debate",
                debate=_valid_debate_block(role_a="master", role_b="debater"))
            findings = validate_contract_full(contract, None, book)
            self.assertEqual(findings, [], findings)

    def test_descriptive_role_label_fails(self):
        """The exact label that burned an ~11-minute framing authoring tonight."""
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            contract = _valid_contract(
                "alpha", episode_format="debate",
                debate=_valid_debate_block(role_a="advocate — voices Salih"))
            findings = validate_contract_full(contract, None, book)
            self.assertTrue(any("R-HOST-ROLE-PARITY" in f for f in findings), findings)

    def test_host_b_out_of_pool_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            contract = _valid_contract(
                "alpha", episode_format="debate",
                debate=_valid_debate_block(role_b="arbiter — voices Abu Malik"))
            findings = validate_contract_full(contract, None, book)
            self.assertTrue(any("R-HOST-ROLE-PARITY" in f and "host_b" in f
                                for f in findings), findings)


class EnumAndSchemaTests(unittest.TestCase):
    def test_unknown_episode_format_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            contract = _valid_contract("alpha", episode_format="fireside_chat")
            findings = validate_contract_full(contract, None, book)
            self.assertTrue(any("contract.episode_format" in f for f in findings),
                            findings)

    def test_missing_required_fields_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            contract = _valid_contract("alpha")
            del contract["audience"]
            del contract["key_tensions"]
            findings = validate_contract_full(contract, None, book)
            joined = "\n".join(findings)
            self.assertIn("missing required fields", joined)
            self.assertIn("audience", joined)
            self.assertIn("key_tensions", joined)

    def test_non_mapping_contract_single_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            self.assertEqual(validate_contract_full(None, None, book),
                             ["contract is not a YAML mapping"])

    def test_duplicate_title_fails_for_on_disk_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha", "beta"])
            cpath = book / "chapter-contracts" / "alpha.yml"
            cpath.write_text(
                _contract_yaml("alpha", 1, title="Same Title"), encoding="utf-8")
            (book / "chapter-contracts" / "beta.yml").write_text(
                _contract_yaml("beta", 2, title="Same Title"), encoding="utf-8")
            contract = _valid_contract("alpha", title="Same Title")
            findings = validate_contract_full(contract, None, book, contract_path=cpath)
            self.assertTrue(any("duplicates another chapter" in f for f in findings),
                            findings)


# ─────────────────────────────────────────────────────────────────────────────
# 2. The $0 smoke gate surfaces every class pre-loop
# ─────────────────────────────────────────────────────────────────────────────

class SmokeGateContractTests(unittest.TestCase):
    def _write(self, book: Path, slug: str, text: str) -> None:
        (book / "chapter-contracts" / f"{slug}.yml").write_text(text, encoding="utf-8")

    def test_smoke_gate_catches_debate_no_block(self):
        from phases.preflight_chapter import smoke_check_book
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha", "beta"])
            self._write(book, "alpha", _contract_yaml("alpha", 1))
            # tonight's class (a): debate declared, no debate block at all
            self._write(book, "beta",
                        _contract_yaml("beta", 2, episode_format="debate"))
            failures = smoke_check_book(book, ["alpha", "beta"])
            failed_slugs = [s for s, _ in failures]
            self.assertEqual(failed_slugs, ["beta"], failures)
            self.assertIn("contract validation", failures[0][1])
            self.assertIn("debate", failures[0][1])

    def test_smoke_gate_catches_role_enum(self):
        from phases.preflight_chapter import smoke_check_book
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            self._write(book, "alpha",
                        _contract_yaml("alpha", 1, episode_format="debate",
                                       debate_yaml=_DEBATE_YAML_BAD_ROLE))
            failures = smoke_check_book(book, ["alpha"])
            self.assertEqual(len(failures), 1, failures)
            self.assertIn("R-HOST-ROLE-PARITY", failures[0][1])

    def test_smoke_gate_catches_renamed_slug(self):
        from phases.preflight_chapter import smoke_check_book
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            # contract for a slug whose chapter file does not exist
            self._write(book, "alpha-renamed", _contract_yaml("alpha-renamed", 1))
            failures = smoke_check_book(book, ["alpha-renamed"])
            self.assertEqual(len(failures), 1, failures)
            self.assertIn("chapter file missing", failures[0][1])

    def test_smoke_gate_green_path(self):
        from phases.preflight_chapter import smoke_check_book
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha", "beta"])
            self._write(book, "alpha", _contract_yaml("alpha", 1))
            self._write(book, "beta",
                        _contract_yaml("beta", 2, episode_format="debate",
                                       debate_yaml=_DEBATE_YAML_OK))
            failures = smoke_check_book(book, ["alpha", "beta"])
            self.assertEqual(failures, [], failures)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Book-level sweep + the Phase-0d post-write gate
# ─────────────────────────────────────────────────────────────────────────────

class BookSweepAnd0dGateTests(unittest.TestCase):
    def test_validate_book_contracts_flags_bad_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha", "beta"])
            (book / "chapter-contracts" / "alpha.yml").write_text(
                _contract_yaml("alpha", 1), encoding="utf-8")
            (book / "chapter-contracts" / "beta.yml").write_text(
                _contract_yaml("beta", 2, episode_format="debate"), encoding="utf-8")
            failures = validate_book_contracts(book)
            self.assertEqual([s for s, _ in failures], ["beta"], failures)

    def test_validate_book_contracts_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            (book / "chapter-contracts" / "alpha.yml").write_text(
                _contract_yaml("alpha", 1), encoding="utf-8")
            self.assertEqual(validate_book_contracts(book), [])

    def test_0d_gate_raises_authoring_error_with_findings(self):
        from _authoring import AuthoringError
        from phases.initial_driver import _gate_0d_contracts
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            (book / "chapter-contracts" / "alpha.yml").write_text(
                _contract_yaml("alpha", 1, episode_format="debate"), encoding="utf-8")
            with self.assertRaises(AuthoringError) as ctx:
                _gate_0d_contracts(book)
            msg = str(ctx.exception)
            self.assertIn("Phase-0d contract gate FAIL", msg)
            self.assertIn("alpha", msg)
            self.assertIn("debate", msg)
            self.assertIn("--retry-phase 0d", ctx.exception.manual_fallback)

    def test_0d_gate_passes_clean_book(self):
        from phases.initial_driver import _gate_0d_contracts
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), ["alpha"])
            (book / "chapter-contracts" / "alpha.yml").write_text(
                _contract_yaml("alpha", 1), encoding="utf-8")
            _gate_0d_contracts(book)  # must not raise


if __name__ == "__main__":
    unittest.main()
