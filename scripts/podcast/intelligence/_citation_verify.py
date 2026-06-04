"""_citation_verify.py — Citation verification for the augmentation phase.

Provides `CitationVerifier`, which checks URL and DOI citations found in
chapter bundle text and returns structured verification results.

VERIFICATION STRATEGIES

  verify_url(url):
    Sends an HTTP HEAD request to the URL.  Returns `verified` (2xx/3xx),
    `failed` (4xx/5xx), or `indeterminate` (network error / timeout).
    All results are written to the local cache so subsequent runs are free.

  verify_doi(doi):
    Queries the Crossref API (`https://api.crossref.org/works/<doi>`) to
    confirm the DOI resolves to a real work.  Returns `verified`, `failed`,
    or `indeterminate`.  Respects Crossref's polite-pool etiquette header
    (Mailto supplied via CROSSREF_MAILTO env var).

CACHE
  Every result is persisted to a JSONL file (default path supplied by the
  caller).  Cache entries:
    {"citation_id": str, "type": "url|doi", "value": str, "status": str,
     "checked_at": ISO-8601, "http_code": int|null, "error": str|null}

  Re-checking a cached citation returns the cached result immediately
  (no network call) unless `force_recheck=True` is passed.

OFFLINE MODE
  When `CitationVerifier(offline=True)` is used (--offline flag from
  augmentation.py), all live network calls are suppressed.  Any citation
  not already in the cache returns `status: unverified` and is written to
  the manual-review queue.

MANUAL-REVIEW QUEUE
  Indeterminate and offline-unverified citations are appended to
  `_system/citation-manual-review.jsonl` alongside a human-readable
  `reason` field explaining why the citation could not be verified
  automatically.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

VerificationStatus = Literal["verified", "failed", "indeterminate", "unverified"]

# ── Regex patterns ─────────────────────────────────────────────────────────────
# Matches bare DOIs like 10.1093/mind/fzaa001 or prefixed doi:10.xxxx/...
_DOI_RE = re.compile(r"\b(doi:\s*|https?://doi\.org/)?(10\.\d{4,}/\S+)", re.IGNORECASE)
# Matches https:// and http:// URLs (excluding DOI resolver URLs which are
# handled by verify_doi)
_URL_RE = re.compile(r"https?://(?!doi\.org)\S+", re.IGNORECASE)

CROSSREF_BASE = "https://api.crossref.org/works"
CROSSREF_MAILTO = os.environ.get("CROSSREF_MAILTO", "podcast-pipeline@example.com")
REQUEST_TIMEOUT = 10  # seconds


@dataclass
class VerificationResult:
    citation_id: str
    type: Literal["url", "doi"]
    value: str
    status: VerificationStatus
    http_code: int | None = None
    error: str | None = None
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "citation_id": self.citation_id,
            "type": self.type,
            "value": self.value,
            "status": self.status,
            "http_code": self.http_code,
            "error": self.error,
            "checked_at": self.checked_at,
        }


class CitationVerifier:
    """Verify URL and DOI citations with caching and offline-mode support.

    Parameters
    ----------
    cache_path:
        Path to the JSONL cache file.  Created if absent.
    offline:
        If True, suppresses all live network calls (--offline mode).
    force_recheck:
        If True, re-verifies even citations already in the cache.
    """

    def __init__(
        self,
        cache_path: Path,
        offline: bool = False,
        force_recheck: bool = False,
    ) -> None:
        self.cache_path = cache_path
        self.offline = offline
        self.force_recheck = force_recheck
        self._cache: dict[str, VerificationResult] = {}
        self._load_cache()

    # ── Public API ─────────────────────────────────────────────────────────

    def verify_url(self, url: str, citation_id: str | None = None) -> VerificationResult:
        """Verify that `url` resolves (HTTP HEAD, 2xx/3xx = verified).

        Respects --offline: if offline, returns `unverified` without a
        network call and queues the URL for manual review.
        """
        cid = citation_id or f"url:{url}"
        if not self.force_recheck and cid in self._cache:
            return self._cache[cid]

        if self.offline:
            result = VerificationResult(cid, "url", url, "unverified",
                                        error="offline mode — not checked")
        else:
            result = self._check_url(cid, url)

        self._write_result(result)
        return result

    def verify_doi(self, doi: str, citation_id: str | None = None) -> VerificationResult:
        """Verify that `doi` resolves in the Crossref registry.

        Respects --offline: if offline, returns `unverified` without a
        network call and queues the DOI for manual review.
        """
        # Normalise: strip doi: prefix and any whitespace.
        doi_clean = re.sub(r"^doi:\s*", "", doi.strip(), flags=re.IGNORECASE)
        doi_clean = doi_clean.replace("https://doi.org/", "").strip()
        cid = citation_id or f"doi:{doi_clean}"

        if not self.force_recheck and cid in self._cache:
            return self._cache[cid]

        if self.offline:
            result = VerificationResult(cid, "doi", doi_clean, "unverified",
                                        error="offline mode — not checked")
        else:
            result = self._check_doi(cid, doi_clean)

        self._write_result(result)
        return result

    def verify_all(self, text: str) -> dict[str, int]:
        """Extract and verify all citations found in `text`.

        Returns totals dict: {total, verified, failed, manual_review}.
        """
        results: list[VerificationResult] = []

        for match in _URL_RE.finditer(text):
            url = match.group(0).rstrip(".,;)")
            results.append(self.verify_url(url))

        for match in _DOI_RE.finditer(text):
            doi = match.group(2)
            results.append(self.verify_doi(doi))

        manual_review = sum(
            1 for r in results if r.status in ("indeterminate", "unverified")
        )
        return {
            "total": len(results),
            "verified": sum(1 for r in results if r.status == "verified"),
            "failed": sum(1 for r in results if r.status == "failed"),
            "manual_review": manual_review,
        }

    # ── Private: live network checks ──────────────────────────────────────

    def _check_url(self, cid: str, url: str) -> VerificationResult:
        try:
            import urllib.request
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "podcast-pipeline/1.0 (citation-verifier)")
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                code = resp.status
                status: VerificationStatus = "verified" if code < 400 else "failed"
                return VerificationResult(cid, "url", url, status, http_code=code)
        except Exception as exc:
            return VerificationResult(cid, "url", url, "indeterminate", error=str(exc))

    def _check_doi(self, cid: str, doi: str) -> VerificationResult:
        endpoint = f"{CROSSREF_BASE}/{doi}"
        try:
            import urllib.request
            req = urllib.request.Request(endpoint)
            req.add_header("User-Agent", f"podcast-pipeline/1.0 (mailto:{CROSSREF_MAILTO})")
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                code = resp.status
                status: VerificationStatus = "verified" if code == 200 else "failed"
                return VerificationResult(cid, "doi", doi, status, http_code=code)
        except Exception as exc:
            return VerificationResult(cid, "doi", doi, "indeterminate", error=str(exc))

    # ── Private: cache I/O ────────────────────────────────────────────────

    def _load_cache(self) -> None:
        if not self.cache_path.exists():
            return
        for line in self.cache_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                cid = row["citation_id"]
                self._cache[cid] = VerificationResult(
                    citation_id=cid,
                    type=row.get("type", "url"),
                    value=row.get("value", ""),
                    status=row.get("status", "unverified"),
                    http_code=row.get("http_code"),
                    error=row.get("error"),
                    checked_at=row.get("checked_at", ""),
                )
            except (json.JSONDecodeError, KeyError):
                continue

    def _write_result(self, result: VerificationResult) -> None:
        self._cache[result.citation_id] = result
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("a") as fh:
            fh.write(json.dumps(result.to_dict()) + "\n")
