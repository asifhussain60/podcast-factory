"""_elevenlabs.py — thin ElevenLabs API client for the podcast pipeline.

Productionized from the proven experiment callers
(_workspace/experiments/elevenlabs-audition/render_audition.py and
.../stephanie-interview-prep/generate_audio_v3.py): same key resolution,
same REST endpoints, same subscription-meter pattern. stdlib urllib only —
no SDK dependency in the pipeline path.

Used by:
  - pronunciation_compiler.py  (dictionary upload, version pinning)
  - render_dialogue_audio.py   (text-to-dialogue synthesis, credit metering)

All methods are instance methods on ElevenLabsClient so tests can inject a
fake transport (`transport=` callable) and never touch the network.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API_BASE = "https://api.elevenlabs.io"
KEYCHAIN_SERVICE = "elevenlabs_api_key"


def resolve_api_key() -> str:
    """ELEVENLABS_API_KEY env -> repo .env -> macOS keychain (experiment order)."""
    key = os.getenv("ELEVENLABS_API_KEY")
    if key:
        return key
    repo_root = Path(__file__).resolve().parents[2]
    env_file = repo_root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ELEVENLABS_API_KEY="):
                val = line.split("=", 1)[1].strip().strip("'\"")
                if val:
                    return val
    out = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True, text=True,
    )
    if out.returncode == 0 and out.stdout.strip():
        return out.stdout.strip()
    raise RuntimeError(
        "No ElevenLabs API key found. Either:\n"
        f"  echo 'ELEVENLABS_API_KEY=sk_...' >> {repo_root}/.env\n"
        "or\n"
        f"  security add-generic-password -s {KEYCHAIN_SERVICE} -a elevenlabs -w 'sk_...'"
    )


class ElevenLabsError(RuntimeError):
    """Raised on a non-retryable API failure."""


class ElevenLabsClient:
    """Minimal client: subscription meter, text-to-dialogue, dictionary upload.

    *transport* (tests): callable(method, url, headers, body, timeout) ->
    (status:int, body:bytes). When None, urllib performs the real request.
    """

    def __init__(self, api_key: str | None = None, *, transport=None,
                 retries: int = 3, retry_sleep_s: float = 10.0):
        self._key = api_key
        self._transport = transport
        self._retries = retries
        self._retry_sleep_s = retry_sleep_s

    @property
    def api_key(self) -> str:
        if self._key is None:
            self._key = resolve_api_key()
        return self._key

    # ── transport ────────────────────────────────────────────────────────────

    def _request(self, method: str, path: str, *, body: bytes | None = None,
                 content_type: str | None = None, timeout: int = 300) -> bytes:
        url = f"{API_BASE}{path}"
        headers = {"xi-api-key": self.api_key}
        if content_type:
            headers["Content-Type"] = content_type
        last_err: Exception | None = None
        for attempt in range(self._retries):
            try:
                if self._transport is not None:
                    status, data = self._transport(method, url, headers, body, timeout)
                    if status >= 400:
                        raise ElevenLabsError(
                            f"{method} {path} -> HTTP {status}: {data[:300]!r}")
                    return data
                req = urllib.request.Request(url, data=body, headers=headers,
                                             method=method)
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return r.read()
            except ElevenLabsError:
                raise
            except urllib.error.HTTPError as e:
                detail = b""
                try:
                    detail = e.read()[:300]
                except Exception:  # noqa: BLE001
                    pass
                # 4xx (except 429) are caller errors — retrying won't help.
                if 400 <= e.code < 500 and e.code != 429:
                    raise ElevenLabsError(
                        f"{method} {path} -> HTTP {e.code}: {detail!r}") from e
                last_err = e
            except Exception as e:  # noqa: BLE001 — transient network failures
                last_err = e
            if attempt < self._retries - 1:
                print(f"  [elevenlabs] retry {attempt + 1}/{self._retries - 1} "
                      f"on {method} {path}: {last_err}", file=sys.stderr)
                time.sleep(self._retry_sleep_s)
        raise ElevenLabsError(
            f"{method} {path} failed after {self._retries} attempts: {last_err}")

    # ── endpoints ────────────────────────────────────────────────────────────

    def subscription(self) -> dict:
        """The account's usage meter: character_count / character_limit / tier."""
        return json.loads(self._request("GET", "/v1/user/subscription", timeout=60))

    def text_to_dialogue(
        self,
        inputs: list[dict],
        *,
        model_id: str,
        seed: int | None = None,
        settings: dict | None = None,
        pronunciation_dictionary_locators: list[dict] | None = None,
        output_format: str = "mp3_44100_128",
        timeout: int = 300,
    ) -> bytes:
        """POST /v1/text-to-dialogue. inputs = [{"text": ..., "voice_id": ...}].

        seed: best-effort determinism (0..4294967295; vendor does not
        guarantee). pronunciation_dictionary_locators: up to 3, each
        {"pronunciation_dictionary_id": ..., "version_id": ...} — version
        ALWAYS pinned by the caller."""
        payload: dict = {"model_id": model_id, "inputs": inputs}
        if seed is not None:
            payload["seed"] = int(seed)
        if settings:
            payload["settings"] = settings
        if pronunciation_dictionary_locators:
            if len(pronunciation_dictionary_locators) > 3:
                raise ValueError("at most 3 pronunciation dictionaries per request")
            payload["pronunciation_dictionary_locators"] = pronunciation_dictionary_locators
        return self._request(
            "POST", f"/v1/text-to-dialogue?output_format={output_format}",
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json", timeout=timeout)

    def create_pronunciation_dictionary(self, *, name: str, pls_text: str,
                                        description: str = "") -> tuple[str, str]:
        """Upload a PLS lexicon -> (dictionary_id, version_id).

        POST /v1/pronunciation-dictionaries/add-from-file (multipart). A
        glossary CHANGE uploads a fresh dictionary (new id+version) and the
        book state records the new pin — prior renders stay reproducible
        against their ledger-pinned ids."""
        boundary = f"----podcastfactory{uuid.uuid4().hex}"
        parts: list[bytes] = []

        def field(fname: str, value: str) -> None:
            parts.append(
                (f"--{boundary}\r\nContent-Disposition: form-data; "
                 f"name=\"{fname}\"\r\n\r\n{value}\r\n").encode("utf-8"))

        field("name", name)
        if description:
            field("description", description)
        parts.append(
            (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
             f"filename=\"{name}.pls\"\r\nContent-Type: application/xml\r\n\r\n"
             ).encode("utf-8"))
        parts.append(pls_text.encode("utf-8"))
        parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)
        data = json.loads(self._request(
            "POST", "/v1/pronunciation-dictionaries/add-from-file",
            body=body, content_type=f"multipart/form-data; boundary={boundary}",
            timeout=120))
        dict_id = data.get("id") or data.get("pronunciation_dictionary_id")
        version_id = data.get("version_id") or data.get("latest_version_id")
        if not dict_id or not version_id:
            raise ElevenLabsError(
                f"dictionary upload response missing ids: {data}")
        return str(dict_id), str(version_id)
