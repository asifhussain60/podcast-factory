"""Tests for render_dialogue_audio.py (Step 5) — render-once/cache-forever,

verdict gating, spend approval, ledger determinism, canonical layout, credit
metering, sanity band. ElevenLabs + ffmpeg fully mocked: no network, no spend.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import render_dialogue_audio as rda  # noqa: E402
import _dialogue_convergence as dc  # noqa: E402
import _dialogue_script as ds  # noqa: E402

FIXTURE_BOOK = Path(__file__).resolve().parent / "fixtures" / "audio-engine-book"
EPISODE_ID = "EP01-the-lamp-and-the-wick"

SCRIPT = """\
# EP01-the-lamp-and-the-wick — dialogue script
HOST_A: Welcome. We are with the teaching on the lamp, the oil, and the wick tonight.

HOST_B: And the question the chapter opens with deserves its weight: why praise a lamp that eats itself?

HOST_A: Light is paid for. Every hour of clarity costs an hour of the self that produced it, says the teacher.

HOST_B: So the difference between the cistern and the spring is not capacity but motion.
"""


class FakeClient:
    """Counts dialogue calls; serves a fake meter and dictionary upload."""

    def __init__(self, meter_per_call: int = 100):
        self.dialogue_calls: list[dict] = []
        self.dict_uploads = 0
        self._meter = 5000
        self._meter_per_call = meter_per_call

    def subscription(self):
        return {"character_count": self._meter, "character_limit": 100_000}

    def text_to_dialogue(self, inputs, *, model_id, seed=None, settings=None,
                         pronunciation_dictionary_locators=None,
                         output_format="mp3_44100_128", timeout=300):
        self.dialogue_calls.append({
            "inputs": inputs, "model_id": model_id, "seed": seed,
            "settings": settings, "locators": pronunciation_dictionary_locators,
        })
        self._meter += self._meter_per_call
        return b"FAKEAUDIO:" + str(len(self.dialogue_calls)).encode()

    def create_pronunciation_dictionary(self, *, name, pls_text, description=""):
        self.dict_uploads += 1
        return f"dict-{self.dict_uploads}", f"ver-{self.dict_uploads}"


def fake_concat(chunk_files, out_path):
    out_path.write_bytes(b"".join(p.read_bytes() for p in chunk_files))


def fake_duration(path):
    # ~15 chars/sec equivalent: in-band for every chunk.
    return max(len(path.read_bytes()), 100) / 15.0


class RenderTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.book = Path(tmp) / "book"
        shutil.copytree(FIXTURE_BOOK, self.book)
        cfg = self.book / "_system" / "series-config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8") + "audio_engine: elevenlabs\n",
                       encoding="utf-8")
        self._write_script(SCRIPT)
        self._write_verdict("SHIP-READY")
        self.client = FakeClient()

    def _write_script(self, text):
        p = ds.script_path_for(self.book, EPISODE_ID)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def _write_verdict(self, verdict):
        vp = dc.verdict_path(self.book, EPISODE_ID)
        vp.parent.mkdir(parents=True, exist_ok=True)
        vp.write_text(verdict + "\n", encoding="utf-8")

    def _render(self, **kw):
        kw.setdefault("client", self.client)
        kw.setdefault("approved", True)
        kw.setdefault("concat", fake_concat)
        kw.setdefault("duration_probe", fake_duration)
        kw.setdefault("meter_settle_s", 0.0)
        kw.setdefault("log", lambda *a: None)
        return rda.render_episode(self.book, EPISODE_ID, **kw)


class TestGating(RenderTestCase):
    def test_refuses_without_verdict(self):
        dc.verdict_path(self.book, EPISODE_ID).unlink()
        with self.assertRaises(RuntimeError) as cm:
            self._render()
        self.assertIn("passing verdict", str(cm.exception))
        self.assertEqual(self.client.dialogue_calls, [])

    def test_refuses_failed_verdict(self):
        self._write_verdict("FAILED")
        with self.assertRaises(RuntimeError):
            self._render()

    def test_refuses_paid_render_without_approval(self):
        with self.assertRaises(RuntimeError) as cm:
            self._render(approved=False)
        self.assertIn("not approved", str(cm.exception))
        self.assertEqual(self.client.dialogue_calls, [])

    def test_refuses_manual_engine(self):
        cfg = self.book / "_system" / "series-config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8").replace(
            "audio_engine: elevenlabs", "audio_engine: notebooklm"),
            encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self._render()


class TestRender(RenderTestCase):
    def test_canonical_outputs(self):
        res = self._render()
        self.assertTrue(res.rendered)
        self.assertEqual(res.m4a_path,
                         self.book / "m4a" / "ch01-the-lamp-and-the-wick.m4a")
        self.assertTrue(res.m4a_path.exists())
        tx1 = self.book / "m4a" / "transcripts" / "ch01-the-lamp-and-the-wick.transcript.txt"
        tx2 = self.book / "transcripts" / f"{EPISODE_ID}.transcript.txt"
        self.assertTrue(tx1.exists())
        self.assertTrue(tx2.exists())
        self.assertEqual(tx1.read_bytes(), tx2.read_bytes())
        self.assertIn("HOST_A: Welcome.", tx1.read_text(encoding="utf-8"))

    def test_pinned_settings_and_seed(self):
        self._render()
        self.assertGreater(len(self.client.dialogue_calls), 0)
        for call in self.client.dialogue_calls:
            self.assertEqual(call["model_id"], "eleven_v3")
            self.assertEqual(call["settings"], rda.DIALOGUE_SETTINGS)
            self.assertIsNotNone(call["seed"])
            self.assertGreaterEqual(call["seed"], 0)
            self.assertLessEqual(call["seed"], 4294967295)
            # voice library (2026-06-12) supersedes the registry default
            # cast: with no series-config override, the deterministic
            # per-slug pair from the approved pools applies.
            from _voice_library import pair_for_slug
            expected = set(pair_for_slug(self.book.name).values())
            for inp in call["inputs"]:
                self.assertIn(inp["voice_id"], expected)

    def test_render_ledger_input_to_output_hash(self):
        res = self._render()
        ledger = self.book / "_system" / "render-ledger.jsonl"
        rows = [json.loads(l) for l in ledger.read_text().splitlines()]
        self.assertEqual(len(rows), len(res.chunks))
        for row, cr in zip(rows, res.chunks):
            self.assertEqual(row["input_hash"], cr.input_hash)
            self.assertEqual(row["output_sha256"], cr.output_sha256)
            self.assertEqual(row["model_id"], "eleven_v3")
            self.assertIn("dictionary_version", row)

    def test_credit_metering_exact_from_subscription_delta(self):
        res = self._render()
        n_calls = len(self.client.dialogue_calls)
        self.assertEqual(res.credits_metered, n_calls * 100)
        cost_rows = [json.loads(l) for l in
                     (self.book / "_system" / "cost-ledger.jsonl")
                     .read_text().splitlines()]
        eleven = [r for r in cost_rows if r["model"] == "elevenlabs-eleven-v3"]
        self.assertEqual(len(eleven), 1)
        self.assertEqual(eleven[0]["input_tokens"], res.credits_metered)

    def test_sanity_band_flags_out_of_band_chunks(self):
        res = self._render(duration_probe=lambda p: 1.0)  # absurdly short audio
        self.assertGreater(len(res.sanity_failures), 0)
        self.assertTrue(any("truncation" in n for n in res.notes))


class TestCache(RenderTestCase):
    def test_second_render_is_fully_cached_and_free(self):
        self._render()
        first_calls = len(self.client.dialogue_calls)
        self.assertGreater(first_calls, 0)
        # Second render: zero paid calls, no approval needed.
        res2 = self._render(approved=False)
        self.assertEqual(len(self.client.dialogue_calls), first_calls)
        self.assertEqual(res2.cache_hits, len(res2.chunks))
        self.assertIsNone(res2.credits_metered)

    def test_revision_rerenders_only_changed_chunks(self):
        # Force multiple chunks with a small max via a long script.
        long_script = "# s\n" + "\n\n".join(
            f"HOST_{'A' if i % 2 == 0 else 'B'}: Sentence number {i} carries "
            f"its own weight in this long conversation about the lamp."
            for i in range(40))
        self._write_script(long_script)
        res1 = self._render()
        calls_after_first = len(self.client.dialogue_calls)
        self.assertGreater(len(res1.chunks), 1)
        # Change ONE turn near the end.
        revised = long_script.replace("Sentence number 39", "Sentence number thirty-nine")
        self._write_script(revised)
        res2 = self._render()
        new_calls = len(self.client.dialogue_calls) - calls_after_first
        self.assertGreaterEqual(new_calls, 1)
        self.assertLess(new_calls, len(res2.chunks))  # most chunks were cache hits
        self.assertGreater(res2.cache_hits, 0)

    def test_same_input_same_chunk_hashes(self):
        res1 = self._render()
        res2 = self._render(approved=False)
        self.assertEqual([c.input_hash for c in res1.chunks],
                         [c.input_hash for c in res2.chunks])


class TestDictionaryPinning(RenderTestCase):
    def test_glossary_dictionary_pinned_into_render_calls(self):
        import yaml
        (self.book / "_system" / "glossary.yml").write_text(yaml.safe_dump({
            "entries": [{"phonetic": "batin", "audio_phonetic": "BAA-tin"}]}),
            encoding="utf-8")
        self._render()
        for call in self.client.dialogue_calls:
            self.assertEqual(call["locators"], [{
                "pronunciation_dictionary_id": "dict-1", "version_id": "ver-1"}])
        self.assertEqual(self.client.dict_uploads, 1)
        # Re-render after cache clear: dictionary NOT re-uploaded (pin reused).
        shutil.rmtree(self.book / "_system" / "render-cache")
        self._render()
        self.assertEqual(self.client.dict_uploads, 1)


class TestEpisodeDiscovery(RenderTestCase):
    def test_episodes_with_scripts(self):
        self.assertEqual(rda.episodes_with_scripts(self.book), [EPISODE_ID])

    def test_chapter_stem_prefers_real_chapter_file(self):
        stem = rda.chapter_stem_for_episode(self.book, EPISODE_ID)
        self.assertEqual(stem, "ch01-the-lamp-and-the-wick")


if __name__ == "__main__":
    unittest.main()
