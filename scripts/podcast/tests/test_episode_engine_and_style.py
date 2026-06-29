"""Tests for the per-episode engine override + the audio style fingerprint gate.

Covers the Workstream-A/B additions (2026-06-13):
  - episode_engine_overrides parsing + validation (typo raises)
  - engine_for_episode resolution (override else book default)
  - per-profile NEW-book default engine + cast (never retroactive)
  - intake_launch stamps audio_engine + voice_cast for a new Islamic book
  - the bundle/upload-table golden-test latch (no overrides => unfiltered)
  - the fingerprint gold-standard loader + scoring (pass/fail vs threshold)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _audio_engines as ae  # noqa: E402
import _rules as rules  # noqa: E402
import _audio_fingerprint as fp  # noqa: E402


def _book(tmp: str, cfg: str) -> Path:
    d = Path(tmp) / "bk"
    (d / "_system").mkdir(parents=True)
    (d / "_system" / "series-config.yaml").write_text(cfg, encoding="utf-8")
    return d


class TestEpisodeEngineOverride(unittest.TestCase):
    def test_no_overrides_is_empty(self):
        with tempfile.TemporaryDirectory() as t:
            d = _book(t, "audio_engine: elevenlabs\n")
            self.assertEqual(ae.episode_engine_overrides(d), {})

    def test_override_parsed_and_resolved(self):
        with tempfile.TemporaryDirectory() as t:
            d = _book(t, "audio_engine: elevenlabs\n"
                         "episode_engine_overrides:\n  EP07-x: notebooklm\n")
            self.assertEqual(ae.episode_engine_overrides(d), {"EP07-x": "notebooklm"})
            self.assertEqual(ae.engine_for_episode(d, "EP07-x"), "notebooklm")
            # Non-overridden episode falls back to the book default.
            self.assertEqual(ae.engine_for_episode(d, "EP01-y"), "elevenlabs")

    def test_unknown_override_engine_raises(self):
        with tempfile.TemporaryDirectory() as t:
            d = _book(t, "audio_engine: elevenlabs\n"
                         "episode_engine_overrides:\n  EP01-x: gimicktts\n")
            with self.assertRaises(ValueError):
                ae.episode_engine_overrides(d)

    def test_notebooklm_book_with_elevenlabs_override_symmetric(self):
        with tempfile.TemporaryDirectory() as t:
            d = _book(t, "audio_engine: notebooklm\n"
                         "episode_engine_overrides:\n  EP03-z: elevenlabs\n")
            self.assertEqual(ae.engine_for_episode(d, "EP03-z"), "elevenlabs")
            self.assertEqual(ae.engine_for_episode(d, "EP01-a"), "notebooklm")


class TestProfileDefaults(unittest.TestCase):
    def test_islamic_defaults_to_notebooklm_with_cast(self):
        # Locked 2026-06-13: all Islamic books use NotebookLM (ElevenLabs rejected).
        self.assertEqual(rules.audio_engine_default_for_profile("islamic_scholarly"),
                         "notebooklm")
        cast = rules.default_voice_cast_for_profile("islamic_scholarly")
        self.assertEqual(cast.get("host_a"), "Eric")
        self.assertEqual(cast.get("host_b"), "Lily")

    def test_other_profiles_default_notebooklm(self):
        for p in ("fiction", "technical", "general_nonfiction"):
            self.assertEqual(rules.audio_engine_default_for_profile(p), "notebooklm")

    def test_unknown_profile_falls_back_to_islamic(self):
        # Unknown profiles fall back to islamic_scholarly (notebooklm since 2026-06-13).
        self.assertEqual(rules.audio_engine_default_for_profile("nope"), "notebooklm")


class TestIntakeStamp(unittest.TestCase):
    def test_new_islamic_book_gets_notebooklm_engine(self):
        # 2026-06-13: Islamic books default to notebooklm; voice_cast not written
        # (it is ElevenLabs-only and gated by `if audio_engine == "elevenlabs"`).
        import yaml
        from intake_launch import _write_series_config
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "bk"
            (d / "_system").mkdir(parents=True)
            _write_series_config(d, "bk", "Title",
                                 {"content_profile": "islamic_scholarly"}, None)
            cfg = yaml.safe_load((d / "_system" / "series-config.yaml").read_text())
            self.assertEqual(cfg["audio_engine"], "notebooklm")
            self.assertNotIn("voice_cast", cfg)

    def test_operator_voice_choice_wins_on_elevenlabs(self):
        # voice_cast is only written for explicit elevenlabs books; operator must
        # select the engine AND the cast for it to land in series-config.yaml.
        import yaml
        from intake_launch import _write_series_config
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "bk"
            (d / "_system").mkdir(parents=True)
            _write_series_config(d, "bk", "Title", {
                "content_profile": "islamic_scholarly",
                "audio_engine": "elevenlabs",
                "voice_cast_host_a": "George", "voice_cast_host_b": "Sarah",
            }, None)
            cfg = yaml.safe_load((d / "_system" / "series-config.yaml").read_text())
            self.assertEqual(cfg["audio_engine"], "elevenlabs")
            self.assertEqual(cfg["voice_cast"], {"host_a": "George", "host_b": "Sarah"})

    def test_fiction_book_stays_notebooklm_no_cast(self):
        import yaml
        from intake_launch import _write_series_config
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "bk"
            (d / "_system").mkdir(parents=True)
            _write_series_config(d, "bk", "Title", {"content_profile": "fiction"}, None)
            cfg = yaml.safe_load((d / "_system" / "series-config.yaml").read_text())
            self.assertEqual(cfg["audio_engine"], "notebooklm")
            self.assertNotIn("voice_cast", cfg)


class TestFingerprintGoldStandard(unittest.TestCase):
    def test_islamic_gold_standard_loads(self):
        gold = fp.load_gold_standard("islamic_scholarly")
        self.assertIsNotNone(gold)
        self.assertEqual(gold["profile"], "islamic_scholarly")
        self.assertIn("wpm", gold["metrics"])
        self.assertIn("center", gold["metrics"]["wpm"])

    def test_score_central_clip_passes(self):
        gold = fp.load_gold_standard("islamic_scholarly")
        center = {k: v["center"] for k, v in gold["metrics"].items()}
        out = fp.score_against_profile(center, "islamic_scholarly")
        self.assertGreaterEqual(out["score"], 95)   # a clip at the corpus median
        self.assertTrue(out["passed"])

    def test_score_far_clip_fails(self):
        gold = fp.load_gold_standard("islamic_scholarly")
        far = {k: v["center"] * 3 + 50 for k, v in gold["metrics"].items()}
        out = fp.score_against_profile(far, "islamic_scholarly")
        self.assertFalse(out["passed"])

    def test_unknown_profile_no_block(self):
        out = fp.score_against_profile({"wpm": 180}, "no_such_profile_xyz")
        # falls back to islamic gold standard (exists) — so it scores, not None;
        # the contract is only that it never raises and never hard-blocks.
        self.assertIn("passed", out)

    def test_word_count_strips_tags_and_labels(self):
        n = fp.word_count("HOST_A: [warm] hello there friend\n\nHOST_B: yes indeed")
        self.assertEqual(n, 5)   # hello there friend yes indeed


if __name__ == "__main__":
    unittest.main()
