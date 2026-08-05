"""_local_server_client.py — Wave J (J3): thin HTTP client for source_library_server.py.

Calls localhost:4390 with a 300 ms timeout.  Returns None on any failure
(timeout, connection refused, non-200) so callers can fall back gracefully.

No third-party dependencies — stdlib urllib only.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_BASE = "http://localhost:4390"
_TIMEOUT_S = 0.3


def _get(path: str) -> Any | None:
    """GET {_BASE}{path}, return parsed JSON or None on any error."""
    url = f"{_BASE}{path}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def quran_verse(surah: int, ayat: int) -> dict | None:
    """Fetch a single verse. Returns dict with arabic/pickthall/asad/phonetic or None."""
    return _get(f"/quran/verse?surah={surah}&ayat={ayat}")


def term_define(term: str) -> dict | None:
    """Look up a term. Returns dict with found/definition/etymology/related or None."""
    return _get(f"/term/define?term={urllib.parse.quote(term)}")


def session_style_fetch(theme: str, limit: int = 4) -> list[dict]:
    """Fetch session passages matching a theme. Returns list (empty on error)."""
    data = _get(f"/session/style?theme={urllib.parse.quote(theme)}&limit={limit}")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return []


def topic_search(keyword: str, limit: int = 10) -> list[dict]:
    """Search Wisdom topics by keyword. Returns list (empty on error)."""
    data = _get(f"/topic/search?q={urllib.parse.quote(keyword)}&limit={limit}")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return []


def topic_get(topic_id: int) -> dict | None:
    """Fetch a full topic record by ID. Returns dict or None."""
    return _get(f"/topic/get?id={topic_id}")
