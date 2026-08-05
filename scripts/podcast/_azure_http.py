"""scripts/podcast/_azure_http.py — minimal stdlib HTTP transport for the Azure helpers.

Extracted verbatim from _azure.py (R3 DR-005 split, 2026-07-18); behavior unchanged.
_azure.py re-exports `_http`, so `import _azure` call sites keep working.
"""

from __future__ import annotations

import urllib.error
import urllib.request


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
