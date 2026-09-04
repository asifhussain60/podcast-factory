#!/usr/bin/env python3
"""Phase 0a must not pay for OCR twice, and one throttled reply must not fail it.

`ingest_source.py` wrote the OCR text only AFTER translation had also succeeded, and
the translator raised on the first non-200 reply. A single 429 on chunk 2 of a long
book therefore threw away a finished Doc Intelligence result, and the retry the
watchdog made re-submitted the whole PDF -- OCR paid again, translation paid again --
up to twenty times for a throttle that would have cleared in seconds.

Pinned here, against a stubbed Azure:

  1. the OCR text is on disk the moment OCR succeeds, before the translator runs;
  2. a re-run finds it and makes ZERO Doc Intelligence calls (translation still runs);
  3. `--force` re-submits;
  4. the shared transport retries 429 and 5xx with a sleep, and gives up after its cap.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _azure  # noqa: E402
import _azure_http  # noqa: E402
import ingest_source  # noqa: E402

DOCINTEL_RESULT = {
    "status": "succeeded",
    "analyzeResult": {
        "pages": [
            {"pageNumber": 1, "lines": [{"content": "sطر واحد"}]},
            {"pageNumber": 2, "lines": [{"content": "سطر اثنان"}]},
        ]
    },
}


class _Creds:
    endpoint = "https://stub.invalid"
    key = "k"
    region = "r"


class IngestCheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.book = self.root / "content" / "Islamic" / "a-book"
        (self.book / "_system" / "source").mkdir(parents=True)
        self.pdf = self.book / "_system" / "source" / "a-book.pdf"
        self.pdf.write_bytes(b"%PDF-1.4 stub")
        self.docintel = mock.Mock(return_value=DOCINTEL_RESULT)
        self.translate = mock.Mock(return_value="translated")
        self._patches = [
            mock.patch.object(ingest_source, "REPO_ROOT", self.root),
            mock.patch.object(ingest_source, "find_book_dir", return_value=self.book),
            mock.patch.object(_azure, "load_docintel_creds", return_value=_Creds()),
            mock.patch.object(_azure, "load_translator_creds", return_value=_Creds()),
            mock.patch.object(_azure, "docintel_analyze_pdf", self.docintel),
            mock.patch.object(_azure, "translate_text", self.translate),
            mock.patch("builtins.print"),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self.tmp.cleanup()

    def _run(self, *extra: str) -> int:
        argv = ["ingest_source", str(self.pdf), "--book-slug", "a-book", *extra]
        with mock.patch.object(sys, "argv", argv):
            return ingest_source.main()

    @property
    def ocr_path(self) -> Path:
        return self.book / "_system" / "source" / "ocr" / "raw-extract.md"

    @property
    def raw_path(self) -> Path:
        return self.book / "_system" / "source" / "text" / "raw-extract.md"

    def test_ocr_is_persisted_before_translation_and_reused_on_the_rerun(self):
        self.translate.side_effect = [RuntimeError("Translator failed: HTTP 429"), "translated"]
        with self.assertRaises(RuntimeError):
            self._run()
        self.assertTrue(self.ocr_path.exists(), "OCR text must be checkpointed the moment OCR succeeds")
        self.assertIn("<!-- page 2 -->", self.ocr_path.read_text(encoding="utf-8"))
        self.assertFalse(self.raw_path.exists(), "a failed translation must not leave a raw-extract behind")
        self.assertEqual(self.docintel.call_count, 1)

        self.assertEqual(self._run(), 0)
        self.assertEqual(self.docintel.call_count, 1, "the re-run must make ZERO Doc Intelligence calls")
        self.assertEqual(self.translate.call_count, 2, "translation still runs on the re-run")
        self.assertEqual(self.raw_path.read_text(encoding="utf-8"), "translated")
        prov = json.loads((self.book / "_system" / "source" / "text" / "_provenance.json").read_text(encoding="utf-8"))
        self.assertTrue(prov["doc_intelligence"]["reused_checkpoint"])
        self.assertEqual(prov["doc_intelligence"]["page_count"], 2)

    def test_force_resubmits_the_pdf(self):
        self.assertEqual(self._run(), 0)
        self.assertEqual(self._run("--force"), 0)
        self.assertEqual(self.docintel.call_count, 2, "--force must not reuse the checkpoint")


class HttpRetryTests(unittest.TestCase):
    def _transport(self, statuses: list[int]) -> mock.Mock:
        return mock.Mock(side_effect=[(s, {}, b"body") for s in statuses])

    def test_a_429_then_200_succeeds_with_one_sleep(self):
        transport, sleep = self._transport([429, 200]), mock.Mock()
        with mock.patch.object(_azure_http, "_http", transport), mock.patch.object(_azure_http.time, "sleep", sleep):
            status, _, body = _azure_http._http_retry("GET", "https://x.invalid", headers={})
        self.assertEqual((status, body), (200, b"body"))
        self.assertEqual(transport.call_count, 2)
        self.assertEqual(sleep.call_count, 1)

    def test_retry_after_header_is_honoured(self):
        transport = mock.Mock(side_effect=[(503, {"retry-after": "7"}, b""), (200, {}, b"ok")])
        sleep = mock.Mock()
        with mock.patch.object(_azure_http, "_http", transport), mock.patch.object(_azure_http.time, "sleep", sleep):
            _azure_http._http_retry("POST", "https://x.invalid", headers={}, body=b"{}")
        sleep.assert_called_once_with(7.0)

    def test_gives_up_after_the_cap_and_returns_the_last_reply(self):
        transport, sleep = self._transport([500] * 10), mock.Mock()
        with mock.patch.object(_azure_http, "_http", transport), mock.patch.object(_azure_http.time, "sleep", sleep):
            status, _, _ = _azure_http._http_retry("GET", "https://x.invalid", headers={}, max_attempts=5)
        self.assertEqual(status, 500)
        self.assertEqual(transport.call_count, 5)
        self.assertEqual(sleep.call_count, 4, "no sleep after the final attempt")

    def test_a_4xx_that_is_not_a_throttle_is_not_retried(self):
        transport, sleep = self._transport([401, 200]), mock.Mock()
        with mock.patch.object(_azure_http, "_http", transport), mock.patch.object(_azure_http.time, "sleep", sleep):
            status, _, _ = _azure_http._http_retry("GET", "https://x.invalid", headers={})
        self.assertEqual(status, 401)
        self.assertEqual(transport.call_count, 1)
        sleep.assert_not_called()

    def test_the_translator_chunk_loop_survives_one_throttle(self):
        # The end-to-end reason for the helper: one 429 mid-book used to raise.
        ok = json.dumps([{"translations": [{"text": "hi"}]}]).encode()
        transport = mock.Mock(side_effect=[(429, {}, b"slow down"), (200, {}, ok)])
        with (
            mock.patch.object(_azure_http, "_http", transport),
            mock.patch.object(_azure_http.time, "sleep", mock.Mock()),
        ):
            out = _azure.translate_text(_Creds(), "hello", src_lang="ar")
        self.assertEqual(out, "hi")
        self.assertEqual(transport.call_count, 2)


if __name__ == "__main__":
    unittest.main()
