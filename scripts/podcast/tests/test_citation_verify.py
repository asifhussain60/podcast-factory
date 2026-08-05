"""Tests for intelligence/_citation_verify.py — URL/DOI verification with cache.

All network mocked (urllib.request.urlopen patched, or offline mode) — $0 cost,
no live calls. Covers the docstring contract: offline mode returns `unverified`
without touching the network, every result persists to the JSONL cache, a
cached citation is answered without a network call unless force_recheck=True,
DOI prefixes are normalised, and 2xx/4xx-5xx/network-error map to
verified / failed / indeterminate.
"""

from __future__ import annotations

import io
import json
import sys
import urllib.error
from pathlib import Path
from unittest import mock

_INTEL = Path(__file__).resolve().parents[1] / "intelligence"
if str(_INTEL) not in sys.path:
    sys.path.insert(0, str(_INTEL))

import _citation_verify as cv


def _verifier(tmp_path: Path, **kw) -> cv.CitationVerifier:
    return cv.CitationVerifier(tmp_path / "citation-cache.jsonl", **kw)


class _FakeResponse:
    def __init__(self, status: int):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


# ---------------------------------------------------------------- offline mode
def test_offline_url_is_unverified_and_cached(tmp_path):
    v = _verifier(tmp_path, offline=True)
    result = v.verify_url("https://example.com/paper")
    assert result.status == "unverified"
    assert "offline" in (result.error or "")

    rows = [json.loads(ln) for ln in (tmp_path / "citation-cache.jsonl").read_text().splitlines()]
    assert rows[0]["citation_id"] == "url:https://example.com/paper"
    assert rows[0]["status"] == "unverified"


def test_offline_doi_normalises_prefixes(tmp_path):
    v = _verifier(tmp_path, offline=True)
    a = v.verify_doi("doi: 10.1093/mind/fzaa001")
    b = v.verify_doi("https://doi.org/10.5555/xyz")
    assert a.value == "10.1093/mind/fzaa001"
    assert a.citation_id == "doi:10.1093/mind/fzaa001"
    assert b.value == "10.5555/xyz"
    assert a.type == "doi" and b.type == "doi"


# ---------------------------------------------------------------- cache behavior
def test_cached_result_answers_without_network(tmp_path):
    _verifier(tmp_path, offline=True).verify_url("https://example.com/a")
    # Second verifier, ONLINE: must serve the cached row, never hit the network.
    v2 = _verifier(tmp_path, offline=False)
    with mock.patch.object(cv.CitationVerifier, "_check_url") as check:
        result = v2.verify_url("https://example.com/a")
    check.assert_not_called()
    assert result.status == "unverified"  # the cached row, verbatim


def test_force_recheck_bypasses_cache(tmp_path):
    _verifier(tmp_path, offline=True).verify_url("https://example.com/a")
    v2 = _verifier(tmp_path, force_recheck=True)
    fresh = cv.VerificationResult(
        "url:https://example.com/a", "url", "https://example.com/a", "verified", http_code=200
    )
    with mock.patch.object(cv.CitationVerifier, "_check_url", return_value=fresh) as check:
        result = v2.verify_url("https://example.com/a")
    check.assert_called_once()
    assert result.status == "verified"


def test_corrupt_cache_lines_are_skipped(tmp_path):
    cache = tmp_path / "citation-cache.jsonl"
    good = {"citation_id": "url:https://ok.example", "type": "url", "value": "https://ok.example", "status": "verified"}
    cache.write_text("{not json}\n" + json.dumps(good) + '\n{"no_citation_id": true}\n', encoding="utf-8")
    v = _verifier(tmp_path)
    assert v.verify_url("https://ok.example").status == "verified"  # survived the junk


# ---------------------------------------------------------------- live checks (mocked)
def test_url_2xx_is_verified(tmp_path):
    with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(200)):
        result = _verifier(tmp_path).verify_url("https://example.com/ok")
    assert result.status == "verified"
    assert result.http_code == 200


def test_url_404_is_failed(tmp_path):
    err = urllib.error.HTTPError("https://example.com/gone", 404, "Not Found", hdrs=None, fp=io.BytesIO(b""))
    with mock.patch("urllib.request.urlopen", side_effect=err):
        result = _verifier(tmp_path).verify_url("https://example.com/gone")
    assert result.status == "failed"
    assert result.http_code == 404


def test_url_network_error_is_indeterminate(tmp_path):
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("dns down")):
        result = _verifier(tmp_path).verify_url("https://example.com/x")
    assert result.status == "indeterminate"
    assert "dns down" in (result.error or "")


def test_doi_200_verified_and_404_failed(tmp_path):
    with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(200)):
        ok = _verifier(tmp_path).verify_doi("10.1000/real")
    assert ok.status == "verified"

    err = urllib.error.HTTPError("x", 404, "Not Found", hdrs=None, fp=io.BytesIO(b""))
    with mock.patch("urllib.request.urlopen", side_effect=err):
        bad = _verifier(tmp_path).verify_doi("10.1000/fake")
    assert bad.status == "failed"
    assert bad.http_code == 404


# ---------------------------------------------------------------- verify_all
def test_verify_all_extracts_urls_and_dois(tmp_path):
    text = "See https://example.com/study. Also compare doi:10.1093/mind/fzaa001 for the full argument."
    v = _verifier(tmp_path, offline=True)
    totals = v.verify_all(text)
    assert totals == {"total": 2, "verified": 0, "failed": 0, "manual_review": 2}
    # Trailing sentence punctuation must be stripped from the extracted URL.
    rows = [json.loads(ln) for ln in (tmp_path / "citation-cache.jsonl").read_text().splitlines()]
    url_rows = [r for r in rows if r["type"] == "url"]
    assert url_rows[0]["value"] == "https://example.com/study"


def test_verify_all_counts_verified_and_failed(tmp_path):
    v = _verifier(tmp_path)
    ok = cv.VerificationResult("url:a", "url", "a", "verified", http_code=200)
    bad = cv.VerificationResult("doi:b", "doi", "b", "failed", http_code=404)
    with (
        mock.patch.object(cv.CitationVerifier, "_check_url", return_value=ok),
        mock.patch.object(cv.CitationVerifier, "_check_doi", return_value=bad),
    ):
        totals = v.verify_all("https://a.example/page and doi:10.2000/b")
    assert totals["verified"] == 1
    assert totals["failed"] == 1
    assert totals["manual_review"] == 0
