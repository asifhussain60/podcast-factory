"""Tests for the pre-synthesis content gate (Step 3): _validators_dialogue.py

deterministic checks + _dialogue_convergence.py loop semantics (LLM passes
mocked — no spend)."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _dialogue_script as ds
import _validators_dialogue as vd

FIXTURE_BOOK = Path(__file__).resolve().parent / "fixtures" / "audio-engine-book"
EPISODE_ID = "EP01-the-lamp-and-the-wick"
CHAPTER_SLUG = "the-lamp-and-the-wick"

# A clean script: develops the chapter, surfaces the contracted tension
# ("light is paid for in the self that carries it"), both hosts, no deny hits.
CLEAN_SCRIPT = """\
# EP01-the-lamp-and-the-wick — dialogue script
# engine: elevenlabs

HOST_A: Welcome. We are with the teaching on the lamp, the oil, and the wick — and the hard claim at its center: the flame finds the lamp that is ready for it.

HOST_B: Before we get to readiness, the student's objection deserves its full weight. If the wick is consumed, then light is paid for in the self that carries it. Why praise a lamp that eats itself?

HOST_A: The teacher refuses to soften that point. Light is paid for. Every hour of clarity costs an hour of the self that produced it. The person who refuses the cost keeps the wick intact and sits in the dark.

HOST_B: I don't buy that yet — keeping a reserve of knowledge sounds prudent, not dangerous. A cistern against drought.

HOST_A: The teacher answers with that exact image. A cistern holds what was poured into it and goes stale. A spring gives constantly and stays sweet. The difference is not capacity but motion.

HOST_B: So stored learning sours. That concedes my cistern. What about the vessel — the discipline that holds the whole thing steady?

HOST_A: Each part is incomplete without the others. The vessel without oil is an ornament. Oil without a wick is a stored danger. A wick without a vessel gutters in the first wind.

HOST_B: Then who lights it? The student assumes the teacher does.

HOST_A: And the teacher refuses the compliment. A hand lights a lamp, but the hand is not the fire. The teacher trims the wick, fills the vessel, shelters the flame. What actually catches is not in the teacher's gift. The flame finds the lamp that is ready for it.

HOST_B: Which leaves the listener with the real question: of the three parts — the vessel, the oil, the wick — which one is most neglected this week, and what would trimming it look like?
"""


def make_book(config_append: str = "audio_engine: elevenlabs\n") -> Path:
    tmp = tempfile.mkdtemp()
    book = Path(tmp) / "book"
    shutil.copytree(FIXTURE_BOOK, book)
    (book / "chapter-contracts").mkdir()
    (book / "chapter-contracts" / f"{CHAPTER_SLUG}.yml").write_text(
        "title: The Lamp and the Wick\n"
        "episode_format: deep_dive\n"
        "key_tensions:\n"
        "  - light is paid for in the self that carries it\n"
        "concepts:\n"
        "  - the cistern and the spring\n",
        encoding="utf-8",
    )
    cfg = book / "_system" / "series-config.yaml"
    cfg.write_text(cfg.read_text(encoding="utf-8") + config_append, encoding="utf-8")
    return book


def write_script(book: Path, text: str) -> Path:
    p = ds.script_path_for(book, EPISODE_ID)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


class TestGate(unittest.TestCase):
    def setUp(self):
        self.book = make_book()
        self.addCleanup(shutil.rmtree, self.book.parent, ignore_errors=True)

    def test_clean_script_has_no_p0_p1(self):
        write_script(self.book, CLEAN_SCRIPT)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        self.assertEqual([f for f in r.findings if f.severity in ("P0", "P1")], [], msg=str(r.findings))
        self.assertFalse(r.render_blocked)

    def test_credit_estimate_matches_char_count(self):
        write_script(self.book, CLEAN_SCRIPT)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        turns = ds.parse_dialogue_script(CLEAN_SCRIPT)
        self.assertEqual(r.char_count, ds.script_char_count(turns))
        self.assertEqual(r.credit_estimate, r.char_count)  # eleven_v3: 1 credit/char

    def test_missing_script_is_p0(self):
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        self.assertEqual(r.findings[0].check_id, "DLG-MISSING")
        self.assertTrue(r.render_blocked)

    def test_deny_phrase_is_p0(self):
        bad = CLEAN_SCRIPT + "\nHOST_B: This reminds me of social media somehow.\n"
        write_script(self.book, bad)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        self.assertIn("DLG-DENY-MODERNIZE", [f.check_id for f in r.findings])
        self.assertTrue(r.render_blocked)

    def test_surprise_noise_is_p0(self):
        bad = CLEAN_SCRIPT + "\nHOST_B: Wow, it's fascinating how that lands.\n"
        write_script(self.book, bad)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        ids = [f.check_id for f in r.findings]
        self.assertIn("DLG-DENY-SURPRISE", ids)

    def test_meta_prose_is_p0(self):
        bad = CLEAN_SCRIPT + "\nHOST_A: As we said in the previous episode, the oil matters.\n"
        write_script(self.book, bad)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        self.assertIn("DLG-META-PROSE", [f.check_id for f in r.findings])

    def test_coverage_missing_tension_is_p0(self):
        # A script that never develops the contracted tension or concept.
        thin = (
            "HOST_A: The lamp is a fine image for a teaching dialogue.\n\n"
            "HOST_B: It is. Vessels and wicks and oil, all very tidy.\n"
        )
        write_script(self.book, thin)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        self.assertIn("DLG-COVERAGE", [f.check_id for f in r.findings])
        self.assertTrue(r.render_blocked)

    def test_single_speaker_is_p0(self):
        mono = "HOST_A: I will carry this whole conversation alone tonight.\n"
        write_script(self.book, mono)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        self.assertIn("DLG-HOST-PARITY", [f.check_id for f in r.findings])

    def test_arabic_script_engine_aware(self):
        arabic_line = "\nHOST_A: The word is كن — two letters.\n"
        # elevenlabs supports Arabic script: no finding.
        write_script(self.book, CLEAN_SCRIPT + arabic_line)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        self.assertNotIn("DLG-ARABIC-SCRIPT", [f.check_id for f in r.findings])
        # notebooklm does not: P0.
        book2 = make_book(config_append="")  # default engine
        self.addCleanup(shutil.rmtree, book2.parent, ignore_errors=True)
        write_script(book2, CLEAN_SCRIPT + arabic_line)
        r2 = vd.gate_dialogue_script(book2, EPISODE_ID)
        self.assertIn("DLG-ARABIC-SCRIPT", [f.check_id for f in r2.findings])

    def test_tags_engine_aware(self):
        tagged = CLEAN_SCRIPT.replace("HOST_A: Welcome.", "HOST_A: [warm] Welcome.")
        # Supported + sparse: fine.
        write_script(self.book, tagged)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        self.assertNotIn("DLG-TAGS-UNSUPPORTED", [f.check_id for f in r.findings])
        # Unsupported engine: P0.
        book2 = make_book(config_append="")
        self.addCleanup(shutil.rmtree, book2.parent, ignore_errors=True)
        write_script(book2, tagged)
        r2 = vd.gate_dialogue_script(book2, EPISODE_ID)
        self.assertIn("DLG-TAGS-UNSUPPORTED", [f.check_id for f in r2.findings])

    def test_tag_density_p1(self):
        dense = CLEAN_SCRIPT.replace("HOST_A: ", "HOST_A: [warm] ").replace("HOST_B: ", "HOST_B: [curious] ")
        write_script(self.book, dense)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        self.assertIn("DLG-TAGS-NOT-SPARSE", [f.check_id for f in r.findings])

    def test_honorific_repeat_is_p1(self):
        bad = CLEAN_SCRIPT + (
            "\nHOST_A: The Prophet (peace be upon him) taught readiness."
            "\n\nHOST_B: And the Prophet (peace be upon him) embodied it.\n"
        )
        write_script(self.book, bad)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        self.assertIn("DLG-HONORIFIC-ONCE", [f.check_id for f in r.findings])

    def test_doubled_phrase_is_p1(self):
        bad = CLEAN_SCRIPT + (
            "\nHOST_A: The classical Quran commentator the classical Quran commentator said this plainly enough.\n"
        )
        write_script(self.book, bad)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        self.assertIn("DLG-DOUBLED-PHRASE", [f.check_id for f in r.findings])

    def test_soft_band_is_p2_advisory_only(self):
        write_script(self.book, CLEAN_SCRIPT)  # far under the 10.8k default band
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        band = [f for f in r.findings if f.check_id == "DLG-SOFT-BAND"]
        self.assertEqual(len(band), 1)
        self.assertEqual(band[0].severity, "P2")
        self.assertIn("never cut", band[0].message.lower())
        self.assertFalse(r.render_blocked)

    def test_gate_report_carries_credit_estimate(self):
        write_script(self.book, CLEAN_SCRIPT)
        r = vd.gate_dialogue_script(self.book, EPISODE_ID)
        text = vd.render_gate_report(r)
        self.assertIn(f"credit estimate: {r.credit_estimate:,} credits", text)
        self.assertIn(vd.DIALOGUE_GATE_VERSION, text)


class TestConvergence(unittest.TestCase):
    """Loop semantics with the LLM passes mocked (semantic=False, fixer mocked)."""

    def setUp(self):
        self.book = make_book()
        self.addCleanup(shutil.rmtree, self.book.parent, ignore_errors=True)
        import _dialogue_convergence as dc

        self.dc = dc
        # Keep the learning ledger inside the tmp book, not the real repo.
        self._ledger_patch = mock.patch.object(dc, "REPO_ROOT", self.book.parent)
        self._ledger_patch.start()
        self.addCleanup(self._ledger_patch.stop)

    def test_clean_script_ships_first_iteration(self):
        write_script(self.book, CLEAN_SCRIPT)
        res = self.dc.converge_dialogue_script(
            self.book, CHAPTER_SLUG, semantic=False, author_first=False, log=lambda *a: None
        )
        self.assertEqual(res.verdict, "SHIP-READY")
        self.assertEqual(res.iterations, 1)
        self.assertEqual(self.dc.read_verdict(self.book, EPISODE_ID), "SHIP-READY")
        self.assertTrue(self.dc.gate_report_path(self.book, EPISODE_ID).exists())
        # Findings ledger written under the patched repo root.
        self.assertTrue((self.book.parent / "_learning" / "findings.jsonl").exists())

    def test_p1_residual_accepts_ship_with_caution(self):
        bad = CLEAN_SCRIPT + (
            "\nHOST_A: The classical Quran commentator the classical Quran commentator said this plainly enough.\n"
        )
        write_script(self.book, bad)
        with mock.patch.object(self.dc, "_fixer_pass") as fx:
            res = self.dc.converge_dialogue_script(
                self.book, CHAPTER_SLUG, semantic=False, author_first=False, log=lambda *a: None
            )
        self.assertEqual(res.verdict, "SHIP-WITH-CAUTION")
        self.assertGreaterEqual(res.iterations, 2)
        fx.assert_called_once()  # one fixer attempt before cautioned-ship

    def test_persistent_p0_stalls_to_failed(self):
        bad = CLEAN_SCRIPT + "\nHOST_B: This reminds me of social media somehow.\n"
        write_script(self.book, bad)
        with mock.patch.object(self.dc, "_fixer_pass"):  # fixer no-ops
            res = self.dc.converge_dialogue_script(
                self.book, CHAPTER_SLUG, semantic=False, author_first=False, log=lambda *a: None
            )
        self.assertEqual(res.verdict, "FAILED")
        self.assertGreater(res.p0_remaining, 0)
        self.assertEqual(self.dc.read_verdict(self.book, EPISODE_ID), "FAILED")

    def test_semantic_blocked_verdict_blocks(self):
        write_script(self.book, CLEAN_SCRIPT)
        with (
            mock.patch.object(
                self.dc,
                "_semantic_pass",
                return_value=(
                    "BLOCKED",
                    [vd.Finding("DLG-SEM-INVENTED", "P0", "host invents an attribution not in the chapter")],
                ),
            ),
            mock.patch.object(self.dc, "_fixer_pass"),
        ):
            res = self.dc.converge_dialogue_script(
                self.book, CHAPTER_SLUG, semantic=True, author_first=False, log=lambda *a: None
            )
        self.assertEqual(res.verdict, "FAILED")

    def test_fixer_timeout_never_aborts_convergence(self):
        """Live failure 2026-06-12: claude -p applied its edits then hung past
        the 900s timeout; the AuthoringError crashed the whole loop. The loop
        must instead re-gate the artifact as it stands."""
        from _authoring._core import AuthoringError

        bad = CLEAN_SCRIPT + (
            "\nHOST_A: The classical Quran commentator the classical Quran commentator said this plainly enough.\n"
        )
        write_script(self.book, bad)

        def hanging_fixer(book_dir, episode_id, chapter_slug, findings, **kw):
            # Simulate edits-applied-then-timeout: fix the script, then raise.
            write_script(self.book, CLEAN_SCRIPT)
            raise AuthoringError(phase="audio-script", message="LLM call timed out after 900s.")

        with mock.patch.object(self.dc, "_fixer_pass", side_effect=hanging_fixer):
            res = self.dc.converge_dialogue_script(
                self.book, CHAPTER_SLUG, semantic=False, author_first=False, log=lambda *a: None
            )
        # The fixed artifact re-gates clean on iteration 2 -> SHIP-READY.
        self.assertEqual(res.verdict, "SHIP-READY")
        self.assertTrue(any("fixer error" in n for n in res.notes))

    def test_credit_estimate_propagates_to_result(self):
        write_script(self.book, CLEAN_SCRIPT)
        res = self.dc.converge_dialogue_script(
            self.book, CHAPTER_SLUG, semantic=False, author_first=False, log=lambda *a: None
        )
        turns = ds.parse_dialogue_script(CLEAN_SCRIPT)
        self.assertEqual(res.credit_estimate, ds.script_char_count(turns))


if __name__ == "__main__":
    unittest.main()
