"""scripts/podcast/_azure_http.py — minimal stdlib HTTP transport for the Azure helpers.

Extracted verbatim from _azure.py (R3 DR-005 split, 2026-07-18); behavior unchanged.
_azure.py re-exports `_http`, so `import _azure` call sites keep working.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request

#: Replies worth a second try: throttling and the gateway/transient server family.
#: Nothing else -- a 400/401/404 is a defect in the request and will not change.
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
_BACKOFF_CAP_S = 30.0


def _http(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: bytes | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict[str, str], bytes]:
    """Minimal urllib wrapper. Returns (status, headers, body_bytes).

    Does NOT raise on non-2xx — callers decide whether to retry or surface.
    """
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as e:
        # HTTPError IS a response — read the body so the caller can surface the Azure error JSON.
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read() or b""


def _http_retry(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: bytes | None = None,
    timeout: float = 60.0,
    max_attempts: int = 5,
) -> tuple[int, dict[str, str], bytes]:
    """`_http`, re-sent on 429/5xx with capped exponential backoff.

    Honours `Retry-After` (seconds) when Azure sends one, else 1s, 2s, 4s, ... capped
    at 30s. Returns the LAST reply — still never raises on a non-2xx, so callers keep
    deciding what a final failure means. Added 2026-09-03: one throttled chunk in a
    long translation raised and threw away a finished OCR, and the watchdog then
    re-paid both stages to reach the same throttle.
    """
    status, hdrs, resp = _http(method, url, headers=headers, body=body, timeout=timeout)
    for attempt in range(1, max_attempts):
        if status not in RETRYABLE_STATUSES:
            break
        try:
            delay = float(hdrs.get("retry-after", ""))
        except ValueError:
            delay = float(2 ** (attempt - 1))
        time.sleep(min(delay, _BACKOFF_CAP_S))
        status, hdrs, resp = _http(method, url, headers=headers, body=body, timeout=timeout)
    return status, hdrs, resp
