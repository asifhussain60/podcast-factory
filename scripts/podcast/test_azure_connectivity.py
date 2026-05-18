#!/usr/bin/env python3
"""test_azure_connectivity.py — Azure half of the podcast pre-flight.

Companion to server/src/api-connectivity.test.js, which covers the Anthropic
proxy. This script verifies the Azure surface the podcast pipeline depends on:
Document Intelligence + Translator + Speech credentials reachable, Translator
live with a 4-character round-trip. Doc Intelligence and Speech are not
exercised against real input because that costs cents-per-invocation; key
resolution + endpoint reachability is enough to catch a misconfigured
environment. (Speech is gracefully skipped when not yet provisioned —
ENABLE_SPEECH defaults false; the probe is a no-fail if creds are absent.)

USAGE

    python3 scripts/podcast/test_azure_connectivity.py
    SKIP_LIVE=1 python3 scripts/podcast/test_azure_connectivity.py   # creds only, no HTTP
    python3 scripts/podcast/test_azure_connectivity.py --verbose

EXIT CODES

    0  — all checks passed
    1  — one or more checks failed (missing creds, network, auth)
    2  — invocation error (bad args, etc.)

The summary mirrors the Node test for symmetry:
    pass N  fail M
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _azure  # noqa: E402

SKIP_LIVE = os.environ.get("SKIP_LIVE") == "1"


class TestResult:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def check(
        self,
        name: str,
        fn: Callable[[], str],
        *,
        skip_when_live: bool = False,
        skip_on_missing_creds: bool = False,
    ) -> None:
        """Run a check.

        - `skip_when_live`: when SKIP_LIVE=1, don't make HTTP calls (use for any
          check whose body issues a live API request that costs money or quota).
        - `skip_on_missing_creds`: when the underlying `AzureCredsError` fires
          (keychain entry missing), count as SKIPPED rather than FAILED. Use for
          *optional* resources (e.g., Speech is not on the critical path for
          chapter ingestion; it activates only after explicit provisioning).
        """
        if skip_when_live and SKIP_LIVE:
            print(f"  SKIP  {name}  (SKIP_LIVE=1)")
            self.skipped += 1
            return
        try:
            detail = fn()
            print(f"  PASS  {name}  {detail}")
            self.passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}  {e}")
            self.failed += 1
        except _azure.AzureCredsError as e:
            if skip_on_missing_creds:
                print(f"  SKIP  {name}  not yet provisioned")
                self.skipped += 1
            else:
                print(f"  FAIL  {name}  {e}")
                self.failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL  {name}  {type(e).__name__}: {e}")
            self.failed += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true", help="Print full creds/endpoints.")
    args = parser.parse_args()

    print("Azure connectivity pre-flight")
    print(f"  app: {_azure.APP_NAME}  skip_live: {SKIP_LIVE}")
    print()

    result = TestResult()

    # ── 1. Translator creds present ──────────────────────────────────────
    def translator_creds() -> str:
        creds = _azure.load_translator_creds()
        assert creds.endpoint.startswith("https://"), f"endpoint missing https: {creds.endpoint}"
        assert creds.key, "key empty"
        assert creds.region, "region empty"
        if args.verbose:
            return f"endpoint={creds.endpoint}  region={creds.region}"
        return f"region={creds.region}"

    result.check("1. Translator credentials", translator_creds)

    # ── 2. Doc Intel creds present ───────────────────────────────────────
    def docintel_creds() -> str:
        creds = _azure.load_docintel_creds()
        assert creds.endpoint.startswith("https://"), f"endpoint missing https: {creds.endpoint}"
        assert creds.key, "key empty"
        if args.verbose:
            return f"endpoint={creds.endpoint}"
        return f"endpoint=<resource>.cognitiveservices.azure.com"

    result.check("2. Doc Intelligence credentials", docintel_creds)

    # ── 3. Translator live round-trip ────────────────────────────────────
    def translator_live() -> str:
        creds = _azure.load_translator_creds()
        out = _azure.translate_text(creds, "test", src_lang="en", tgt_lang="fr")
        assert out.strip(), f"empty response: {out!r}"
        return f"en→fr 'test' → {out.strip()!r}"

    result.check("3. Translator live (en→fr 'test')", translator_live, skip_when_live=True)

    # ── 4. Doc Intel endpoint reachable (no analyze; just hit the docs root) ─
    def docintel_reachable() -> str:
        creds = _azure.load_docintel_creds()
        # The bare /formrecognizer/info endpoint requires a key and returns 200 JSON.
        # If we get 401, auth is broken; 200 = healthy; 404 = wrong region/endpoint.
        url = f"{creds.endpoint}/formrecognizer/info?api-version={_azure.DOCINTEL_API_VERSION}"
        try:
            req = urllib.request.Request(
                url,
                headers={"Ocp-Apim-Subscription-Key": creds.key},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                body = resp.read()
        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read() or b""
        assert status == 200, (
            f"HTTP {status} from {url}\n        body: {body.decode('utf-8', errors='replace')[:200]}"
        )
        info = json.loads(body)
        custom_limit = info.get("customDocumentModels", {}).get("limit", "?")
        return f"reachable (custom-model limit: {custom_limit})"

    result.check("4. Doc Intelligence endpoint reachable", docintel_reachable, skip_when_live=True)

    # ── 5. Speech creds present (optional — only if ENABLE_SPEECH=true) ──
    # Speech is the post-publication Loop M automation (audio → transcript
    # under BOOK_DIR/transcripts/). When the resource isn't provisioned, the probe is
    # skipped rather than failed — Speech is not on the critical path for
    # chapter ingestion.
    def speech_creds() -> str:
        creds = _azure.load_speech_creds()
        assert creds.endpoint.startswith("https://"), f"endpoint missing https: {creds.endpoint}"
        assert creds.key, "key empty"
        assert creds.region, "region empty"
        if args.verbose:
            return f"endpoint={creds.endpoint}  region={creds.region}"
        return f"region={creds.region}"

    result.check("5. Speech credentials (optional)", speech_creds, skip_on_missing_creds=True)

    print()
    summary = f"pass {result.passed}  fail {result.failed}"
    if result.skipped:
        summary += f"  skip {result.skipped}"
    print(summary)

    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
