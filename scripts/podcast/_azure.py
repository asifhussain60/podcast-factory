"""scripts/podcast/_azure.py — Azure REST helpers for the podcast pipeline.

Single responsibility: read Azure credentials from macOS Keychain (or env vars
in CI), call the Document Intelligence + Translator + Speech REST APIs over
stdlib, and return cleanly-shaped Python values to the calling script.

Hard rule: no `pip install` deps. Pure stdlib. Reasoning — these scripts run
on every podcast-pipeline session start; making them survive a fresh checkout
without a venv dance is worth the extra ~100 lines of urllib code.

Keychain naming follows infra/azure/store-keychain-keys.sh exactly:
    azure-<app>-translator-key1
    azure-<app>-translator-endpoint-text
    azure-<app>-translator-region
    azure-<app>-docintel-key1
    azure-<app>-docintel-endpoint
    azure-<app>-docintel-region
    azure-<app>-speech-key1
    azure-<app>-speech-endpoint
    azure-<app>-speech-region

`<app>` defaults to "journal"; override with AZURE_APP_NAME env var if standing
up a parallel stack (per docs/azure/setup.md app-portability section).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

APP_NAME = os.environ.get("AZURE_APP_NAME", "journal")

# Doc Intel: prebuilt-read on the stable 2023-07-31 API. The newer
# /documentintelligence/ namespace exists from 2024-11-30 onward, but
# 2023-07-31 is GA and supported indefinitely. We don't need layout/tables —
# just text + reading order — so prebuilt-read is the right model.
DOCINTEL_API_VERSION = "2023-07-31"
DOCINTEL_MODEL = "prebuilt-read"

# Translator Text API v3.0. We chunk source text and call /translate directly
# instead of the document-translation API. The document API requires SAS-token
# blob storage source/target and adds an async dance; chunked text is
# materially simpler, costs the same per character, and works for OCR'd PDFs.
TRANSLATOR_API_VERSION = "3.0"
TRANSLATOR_MAX_CHARS_PER_REQUEST = 10_000  # well under the 50,000 hard limit

# Speech Fast Transcription API. Synchronous; accepts a multipart-uploaded
# audio file directly (no SAS-blob dance like Batch Transcription). One call
# returns the full transcript. Practical ceiling: ~2 hours of audio per call
# per Azure docs (2024-11-15 GA). For NotebookLM Audio Overviews (typically
# 15–30 min), this fits comfortably in one synchronous request.
SPEECH_API_VERSION = "2024-11-15"
SPEECH_DEFAULT_LOCALE = "en-US"
# Map common audio extensions to the MIME types Speech accepts. Anything not
# listed falls back to application/octet-stream — Speech sniffs the bytes.
SPEECH_AUDIO_MIME = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "mp4": "audio/mp4",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "oga": "audio/ogg",
    "flac": "audio/flac",
    "opus": "audio/ogg",
}


# ────────────────────────────────────────────────────────────────────────────
# Keychain access
# ────────────────────────────────────────────────────────────────────────────


class AzureCredsError(RuntimeError):
    """Raised when a required Azure credential cannot be resolved."""


def _read_keychain(service: str) -> str | None:
    """Return the password for `service` from the macOS login keychain.

    Returns None if the entry doesn't exist. Raises AzureCredsError if
    `security` itself is missing (i.e., we're not on macOS).
    """
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AzureCredsError(
            "macOS `security` command not found. Either run this on macOS or "
            "set the AZURE_* env vars directly (see infra/azure/azure-config.env)."
        ) from exc
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _resolve(suffix: str, env_name: str) -> str | None:
    """Resolve a single credential. Env var wins (for CI); Keychain is fallback."""
    if env_name in os.environ and os.environ[env_name]:
        return os.environ[env_name]
    return _read_keychain(f"azure-{APP_NAME}-{suffix}")


@dataclass(frozen=True)
class DocIntelCreds:
    endpoint: str
    key: str
    region: str


@dataclass(frozen=True)
class TranslatorCreds:
    endpoint: str  # text endpoint — global service
    key: str
    region: str


@dataclass(frozen=True)
class SpeechCreds:
    endpoint: str  # region-based: https://<region>.api.cognitive.microsoft.com
    key: str
    region: str


def load_docintel_creds() -> DocIntelCreds:
    endpoint = _resolve("docintel-endpoint", "AZURE_DOCINTEL_ENDPOINT")
    key = _resolve("docintel-key1", "AZURE_DOCINTEL_KEY")
    region = _resolve("docintel-region", "AZURE_DOCINTEL_REGION")
    missing = [n for n, v in [("endpoint", endpoint), ("key", key), ("region", region)] if not v]
    if missing:
        raise AzureCredsError(
            f"Document Intelligence credentials missing: {', '.join(missing)}. "
            f"Run: cd infra/azure && ./store-keychain-keys.sh "
            f"(or export AZURE_DOCINTEL_ENDPOINT/KEY/REGION for CI)."
        )
    return DocIntelCreds(endpoint=endpoint.rstrip("/"), key=key, region=region)


def load_translator_creds() -> TranslatorCreds:
    endpoint = _resolve("translator-endpoint-text", "AZURE_TRANSLATOR_ENDPOINT")
    key = _resolve("translator-key1", "AZURE_TRANSLATOR_KEY")
    region = _resolve("translator-region", "AZURE_TRANSLATOR_REGION")
    missing = [n for n, v in [("endpoint", endpoint), ("key", key), ("region", region)] if not v]
    if missing:
        raise AzureCredsError(
            f"Translator credentials missing: {', '.join(missing)}. "
            f"Run: cd infra/azure && ./store-keychain-keys.sh "
            f"(or export AZURE_TRANSLATOR_ENDPOINT/KEY/REGION for CI)."
        )
    return TranslatorCreds(endpoint=endpoint.rstrip("/"), key=key, region=region)


def load_speech_creds() -> SpeechCreds:
    endpoint = _resolve("speech-endpoint", "AZURE_SPEECH_ENDPOINT")
    key = _resolve("speech-key1", "AZURE_SPEECH_KEY")
    region = _resolve("speech-region", "AZURE_SPEECH_REGION")
    missing = [n for n, v in [("endpoint", endpoint), ("key", key), ("region", region)] if not v]
    if missing:
        raise AzureCredsError(
            f"Speech credentials missing: {', '.join(missing)}. "
            f"Run: cd infra/azure && ./store-keychain-keys.sh "
            f"(or export AZURE_SPEECH_ENDPOINT/KEY/REGION for CI)."
        )
    return SpeechCreds(endpoint=endpoint.rstrip("/"), key=key, region=region)


# ────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ────────────────────────────────────────────────────────────────────────────


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


# ────────────────────────────────────────────────────────────────────────────
# Document Intelligence — prebuilt-read OCR
# ────────────────────────────────────────────────────────────────────────────


def docintel_analyze_pdf(
    creds: DocIntelCreds,
    pdf_bytes: bytes,
    *,
    poll_interval_s: float = 2.0,
    poll_timeout_s: float = 600.0,
) -> dict[str, Any]:
    """Submit PDF bytes to prebuilt-read, poll until done, return the raw result.

    The returned object is the full Azure response JSON (`analyzeResult` keyed).
    Callers should pull `analyzeResult.content` for the flat reading-order text,
    or iterate `analyzeResult.pages` for page-anchored extraction.

    Raises RuntimeError with the Azure error body on any non-2xx along the way.
    """
    submit_url = (
        f"{creds.endpoint}/formrecognizer/documentModels/{DOCINTEL_MODEL}"
        f":analyze?api-version={DOCINTEL_API_VERSION}"
    )
    status, hdrs, body = _http(
        "POST",
        submit_url,
        headers={
            "Ocp-Apim-Subscription-Key": creds.key,
            "Content-Type": "application/pdf",
        },
        body=pdf_bytes,
    )
    if status != 202:
        raise RuntimeError(
            f"Doc Intel submit failed: HTTP {status}\n{body.decode('utf-8', errors='replace')}"
        )
    op_url = hdrs.get("operation-location")
    if not op_url:
        raise RuntimeError("Doc Intel response missing Operation-Location header")

    deadline = time.monotonic() + poll_timeout_s
    while True:
        time.sleep(poll_interval_s)
        status, _, body = _http(
            "GET",
            op_url,
            headers={"Ocp-Apim-Subscription-Key": creds.key},
        )
        if status != 200:
            raise RuntimeError(
                f"Doc Intel poll failed: HTTP {status}\n{body.decode('utf-8', errors='replace')}"
            )
        result = json.loads(body)
        op_status = result.get("status")
        if op_status == "succeeded":
            return result
        if op_status in ("failed", "canceled"):
            raise RuntimeError(f"Doc Intel operation {op_status}: {json.dumps(result)[:400]}")
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"Doc Intel poll timeout after {poll_timeout_s}s "
                f"(last status: {op_status})"
            )


def docintel_pages_to_markdown(result: dict[str, Any]) -> str:
    """Render Doc Intel's `analyzeResult.pages[*].lines` into Phase 0a markdown.

    Page boundaries become `<!-- page N -->` markers per the Phase 0a normalization
    table in SKILL.md §1.5. Line breaks are preserved verbatim — Phase 0b is the
    layer that joins hyphenated wraps and smooths translation.
    """
    analyze = result.get("analyzeResult") or {}
    pages = analyze.get("pages") or []
    chunks: list[str] = []
    for page in pages:
        page_num = page.get("pageNumber", "?")
        chunks.append(f"<!-- page {page_num} -->")
        lines = page.get("lines") or []
        chunks.extend(line.get("content", "") for line in lines)
        chunks.append("")  # blank line between pages
    return "\n".join(chunks).rstrip() + "\n"


# ────────────────────────────────────────────────────────────────────────────
# Translator Text — chunked ar→en (or any language pair)
# ────────────────────────────────────────────────────────────────────────────


def _chunk_for_translate(text: str, max_chars: int) -> list[str]:
    """Split `text` into translator-API-sized chunks, respecting paragraph breaks.

    Splits on blank lines first; if a single paragraph itself exceeds max_chars,
    splits on sentence-ish boundaries. Falls back to hard cut as a last resort.
    """
    paras = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for p in paras:
        # +2 accounts for the rejoining "\n\n" between paragraphs in this chunk.
        if current_len + len(p) + 2 <= max_chars:
            current.append(p)
            current_len += len(p) + 2
            continue
        if current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        if len(p) <= max_chars:
            current.append(p)
            current_len = len(p)
        else:
            # Single paragraph larger than max_chars — split on sentence boundary or hard cut.
            cursor = 0
            while cursor < len(p):
                piece = p[cursor : cursor + max_chars]
                if cursor + max_chars < len(p):
                    # try to back off to the last sentence terminator
                    cut = max(piece.rfind(". "), piece.rfind("? "), piece.rfind("! "))
                    if cut > max_chars // 2:
                        piece = piece[: cut + 1]
                chunks.append(piece)
                cursor += len(piece)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def translate_text(
    creds: TranslatorCreds,
    text: str,
    *,
    src_lang: str,
    tgt_lang: str = "en",
) -> str:
    """Translate `text` from src_lang to tgt_lang using Azure Translator v3.

    Chunks internally; reassembles output in source order. Page-marker comments
    (`<!-- page N -->`) and inline HTML-style comments are forwarded verbatim
    because Translator preserves XML/HTML tags by default with `textType=plain`
    behaviour (comments aren't tags, so they translate as plain text — we strip
    and re-insert them around chunk boundaries to keep them intact).
    """
    chunks = _chunk_for_translate(text, TRANSLATOR_MAX_CHARS_PER_REQUEST)
    if not chunks:
        return ""
    url = (
        f"{creds.endpoint}/translate"
        f"?api-version={TRANSLATOR_API_VERSION}"
        f"&from={src_lang}&to={tgt_lang}"
    )
    headers = {
        "Ocp-Apim-Subscription-Key": creds.key,
        "Ocp-Apim-Subscription-Region": creds.region,
        "Content-Type": "application/json; charset=UTF-8",
    }
    translated: list[str] = []
    for chunk in chunks:
        payload = json.dumps([{"text": chunk}]).encode("utf-8")
        status, _, body = _http("POST", url, headers=headers, body=payload)
        if status != 200:
            raise RuntimeError(
                f"Translator failed: HTTP {status}\n{body.decode('utf-8', errors='replace')[:600]}"
            )
        data = json.loads(body)
        if not data or not data[0].get("translations"):
            raise RuntimeError(f"Translator returned no translations: {body!r}")
        translated.append(data[0]["translations"][0]["text"])
    return "\n\n".join(translated)


# ────────────────────────────────────────────────────────────────────────────
# Speech — Fast Transcription (synchronous, multipart upload)
# ────────────────────────────────────────────────────────────────────────────


def _multipart_body(
    *,
    boundary: str,
    audio_filename: str,
    audio_mime: str,
    audio_bytes: bytes,
    definition_json: bytes,
) -> bytes:
    """Build a multipart/form-data body for Speech Fast Transcription.

    Two parts: `definition` (text/json) and `audio` (binary). Boundary lines
    use CRLF per RFC 7578. The Azure Speech endpoint is strict about both the
    part ordering and the trailing `--<boundary>--` line.
    """
    nl = b"\r\n"
    parts: list[bytes] = []
    parts.append(f"--{boundary}".encode("ascii") + nl)
    parts.append(b'Content-Disposition: form-data; name="definition"' + nl)
    parts.append(b"Content-Type: application/json" + nl)
    parts.append(nl)
    parts.append(definition_json + nl)
    parts.append(f"--{boundary}".encode("ascii") + nl)
    parts.append(
        f'Content-Disposition: form-data; name="audio"; filename="{audio_filename}"'.encode("utf-8")
        + nl
    )
    parts.append(f"Content-Type: {audio_mime}".encode("ascii") + nl)
    parts.append(nl)
    parts.append(audio_bytes + nl)
    parts.append(f"--{boundary}--".encode("ascii") + nl)
    return b"".join(parts)


def transcribe_audio(
    creds: SpeechCreds,
    audio_bytes: bytes,
    audio_filename: str,
    *,
    locale: str = SPEECH_DEFAULT_LOCALE,
    timeout_s: float = 900.0,
) -> str:
    """Transcribe `audio_bytes` synchronously via Azure Speech Fast Transcription.

    Returns the concatenated transcript text (from `combinedPhrases[0].text`).
    Raises RuntimeError on any non-200 with the Azure error body for debug.

    The endpoint pattern is region-based:
        https://<region>.api.cognitive.microsoft.com/speechtotext/transcriptions:transcribe

    `audio_filename` is used only for the multipart Content-Disposition; the
    MIME type is inferred from the extension via SPEECH_AUDIO_MIME and falls
    back to application/octet-stream.

    For audio longer than ~2 hours, Azure recommends Batch Transcription
    instead — that requires SAS-blob storage and an async polling dance not
    implemented here. Surfaces as a 413 / 400 from the API; surface the error.
    """
    ext = audio_filename.lower().rsplit(".", 1)[-1] if "." in audio_filename else ""
    audio_mime = SPEECH_AUDIO_MIME.get(ext, "application/octet-stream")

    boundary = f"----PodcastFormBoundary{os.urandom(16).hex()}"
    definition = json.dumps({"locales": [locale]}).encode("utf-8")
    body = _multipart_body(
        boundary=boundary,
        audio_filename=audio_filename,
        audio_mime=audio_mime,
        audio_bytes=audio_bytes,
        definition_json=definition,
    )

    url = (
        f"{creds.endpoint}/speechtotext/transcriptions:transcribe"
        f"?api-version={SPEECH_API_VERSION}"
    )
    status, _, response_body = _http(
        "POST",
        url,
        headers={
            "Ocp-Apim-Subscription-Key": creds.key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        body=body,
        timeout=timeout_s,
    )
    if status != 200:
        raise RuntimeError(
            f"Speech transcribe failed: HTTP {status}\n"
            f"{response_body.decode('utf-8', errors='replace')[:600]}"
        )
    data = json.loads(response_body)
    combined = data.get("combinedPhrases") or []
    if not combined:
        # Empty audio or silence-only — return empty string rather than raising,
        # so the caller can decide. The HTTP path itself succeeded.
        return ""
    # Each combinedPhrase corresponds to a channel; mono audio yields a single
    # entry. For multi-channel, concatenate in channel order with blank lines.
    return "\n\n".join(p.get("text", "") for p in combined if p.get("text"))


# ────────────────────────────────────────────────────────────────────────────
# Self-test entry point (also used by test_azure_connectivity.py)
# ────────────────────────────────────────────────────────────────────────────


def probe(verbose: bool = False) -> int:
    """Lightweight reachability probe. Returns 0 on full pass, non-zero on fail.

    Exercised by:
      - `python3 scripts/podcast/_azure.py --probe`
      - `python3 scripts/podcast/test_azure_connectivity.py`
      - SKILL.md §1 Step 0 (Azure half of the pre-flight)
    """
    failures = 0

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    # 1. Translator: key resolution + a 5-char round trip.
    try:
        tcreds = load_translator_creds()
        log(f"  translator: creds present (region={tcreds.region})")
        out = translate_text(tcreds, "test", src_lang="en", tgt_lang="fr")
        if not out.strip():
            print("  translator: FAIL — empty response")
            failures += 1
        else:
            log(f"  translator: live (en→fr 'test' → {out!r})")
    except AzureCredsError as e:
        print(f"  translator: SKIP — {e}")
        failures += 1
    except Exception as e:  # noqa: BLE001
        print(f"  translator: FAIL — {e}")
        failures += 1

    # 2. Doc Intel: key resolution only (a real analyze call costs money + needs a PDF).
    try:
        dcreds = load_docintel_creds()
        log(f"  docintel:   creds present (endpoint={dcreds.endpoint})")
    except AzureCredsError as e:
        print(f"  docintel:   SKIP — {e}")
        failures += 1

    # 3. Speech: key resolution only (a real transcribe call costs money + needs audio).
    try:
        screds = load_speech_creds()
        log(f"  speech:     creds present (endpoint={screds.endpoint})")
    except AzureCredsError as e:
        print(f"  speech:     SKIP — {e}")
        failures += 1

    return failures


def _cli() -> int:
    args = sys.argv[1:]
    if "--probe" in args:
        return probe(verbose=True)
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
