"""scripts/podcast/_azure.py — Azure REST helpers for the podcast pipeline.

Single responsibility: read Azure credentials from macOS Keychain (or env vars
in CI), call the Document Intelligence + Translator + Speech REST APIs over
stdlib, and return cleanly-shaped Python values to the calling script.

Hard rule: no `pip install` deps. Pure stdlib. Reasoning — these scripts run
on every podcast-pipeline session start; making them survive a fresh checkout
without a venv dance is worth the extra ~100 lines of urllib code.

Keychain naming follows infra/azure/pull-secrets.sh exactly:
    azure-<app>-translator-key1
    azure-<app>-translator-endpoint-text
    azure-<app>-translator-region
    azure-<app>-docintel-key1
    azure-<app>-docintel-endpoint
    azure-<app>-docintel-region
    azure-<app>-speech-key1
    azure-<app>-speech-endpoint
    azure-<app>-speech-region

`<app>` defaults to "podcast-factory"; override with AZURE_APP_NAME env var if
standing up a parallel stack (per docs/azure/setup.md app-portability section).
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

# R3 DR-005 split (2026-07-18): credential resolution (_azure_creds), the HTTP
# transport (_azure_http), the TextAnalytics helpers (_azure_language), and the
# DALL-E helpers (_azure_openai) moved verbatim to those sibling modules. Every
# moved name is re-exported here (`X as X`, same pattern as _validator_constants)
# so existing `import _azure` call sites and patch targets keep working unchanged.
from _azure_creds import (
    APP_NAME as APP_NAME,
)
from _azure_creds import (
    AzureCredsError as AzureCredsError,
)
from _azure_creds import (
    DocIntelCreds as DocIntelCreds,
)
from _azure_creds import (
    LanguageCreds as LanguageCreds,
)
from _azure_creds import (
    OpenAICreds as OpenAICreds,
)
from _azure_creds import (
    SpeechCreds as SpeechCreds,
)
from _azure_creds import (
    TranslatorCreds as TranslatorCreds,
)
from _azure_creds import (
    _read_keychain as _read_keychain,
)
from _azure_creds import (
    _resolve as _resolve,
)
from _azure_creds import (
    load_docintel_creds as load_docintel_creds,
)
from _azure_creds import (
    load_language_creds as load_language_creds,
)
from _azure_creds import (
    load_openai_creds as load_openai_creds,
)
from _azure_creds import (
    load_speech_creds as load_speech_creds,
)
from _azure_creds import (
    load_translator_creds as load_translator_creds,
)
from _azure_http import _http as _http
from _azure_language import (
    LANGUAGE_API_VERSION as LANGUAGE_API_VERSION,
)
from _azure_language import (
    LANGUAGE_MAX_CHARS_PER_DOC as LANGUAGE_MAX_CHARS_PER_DOC,
)
from _azure_language import (
    LANGUAGE_MAX_DOCS_PER_REQUEST as LANGUAGE_MAX_DOCS_PER_REQUEST,
)
from _azure_language import (
    _language_post as _language_post,
)
from _azure_language import (
    analyze_sentiment as analyze_sentiment,
)
from _azure_language import (
    extract_key_phrases as extract_key_phrases,
)
from _azure_language import (
    extract_named_entities as extract_named_entities,
)
from _azure_openai import (
    DALLE_API_VERSION as DALLE_API_VERSION,
)
from _azure_openai import (
    DALLE_DEFAULT_QUALITY as DALLE_DEFAULT_QUALITY,
)
from _azure_openai import (
    DALLE_DEFAULT_SIZE as DALLE_DEFAULT_SIZE,
)
from _azure_openai import (
    generate_image_dalle as generate_image_dalle,
)

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
        f"{creds.endpoint}/formrecognizer/documentModels/{DOCINTEL_MODEL}:analyze?api-version={DOCINTEL_API_VERSION}"
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
        raise RuntimeError(f"Doc Intel submit failed: HTTP {status}\n{body.decode('utf-8', errors='replace')}")
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
            raise RuntimeError(f"Doc Intel poll failed: HTTP {status}\n{body.decode('utf-8', errors='replace')}")
        result = json.loads(body)
        op_status = result.get("status")
        if op_status == "succeeded":
            return result
        if op_status in ("failed", "canceled"):
            raise RuntimeError(f"Doc Intel operation {op_status}: {json.dumps(result)[:400]}")
        if time.monotonic() > deadline:
            raise RuntimeError(f"Doc Intel poll timeout after {poll_timeout_s}s (last status: {op_status})")


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
    text_type: str = "plain",
) -> str:
    """Translate `text` from src_lang to tgt_lang using Azure Translator v3.

    Chunks internally; reassembles output in source order. Page-marker comments
    (`<!-- page N -->`) and inline HTML-style comments are forwarded verbatim
    because Translator preserves XML/HTML tags by default with `textType=plain`
    behaviour (comments aren't tags, so they translate as plain text — we strip
    and re-insert them around chunk boundaries to keep them intact).

    Pass `text_type="html"` to preserve HTML tags (incl. self-closing void
    elements like `<x id="1"/>`). Callers use this to protect inline markers
    by tokenizing them as HTML void elements before translation.
    """
    chunks = _chunk_for_translate(text, TRANSLATOR_MAX_CHARS_PER_REQUEST)
    if not chunks:
        return ""
    url = (
        f"{creds.endpoint}/translate"
        f"?api-version={TRANSLATOR_API_VERSION}"
        f"&from={src_lang}&to={tgt_lang}"
        f"&textType={text_type}"
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
            raise RuntimeError(f"Translator failed: HTTP {status}\n{body.decode('utf-8', errors='replace')[:600]}")
        data = json.loads(body)
        if not data or not data[0].get("translations"):
            raise RuntimeError(f"Translator returned no translations: {body!r}")
        translated.append(data[0]["translations"][0]["text"])
    return "\n\n".join(translated)


# ────────────────────────────────────────────────────────────────────────────
# Speech — Fast Transcription
# ────────────────────────────────────────────────────────────────────────────
# Moved to `_azure_speech.py` when this facade crossed the 600-line gate, and
# re-exported here so that every existing caller — `_azure.transcribe_audio(...)`
# and `from _azure import SPEECH_AUDIO_MIME` alike — is untouched. This file has
# always been the one door to Azure; the rooms behind it are allowed to be
# separate.
from _azure_speech import (  # noqa: E402
    SPEECH_API_VERSION as SPEECH_API_VERSION,
)
from _azure_speech import (  # noqa: E402
    SPEECH_AUDIO_MIME as SPEECH_AUDIO_MIME,
)
from _azure_speech import (  # noqa: E402
    SPEECH_DEFAULT_LOCALE as SPEECH_DEFAULT_LOCALE,
)
from _azure_speech import (  # noqa: E402
    Phrase as Phrase,
)
from _azure_speech import (  # noqa: E402
    TimedTranscript as TimedTranscript,
)
from _azure_speech import (  # noqa: E402
    transcribe_audio as transcribe_audio,
)
from _azure_speech import (  # noqa: E402
    transcribe_audio_timed as transcribe_audio_timed,
)

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
    except Exception as e:
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

    # 4. Language: key resolution only.
    try:
        lcreds = load_language_creds()
        log(f"  language:   creds present (endpoint={lcreds.endpoint})")
    except AzureCredsError as e:
        print(f"  language:   SKIP — {e}")
        failures += 1

    # 5. Azure OpenAI / DALL-E: key resolution only (a real generation costs money).
    try:
        ocreds = load_openai_creds()
        log(f"  openai:     creds present (endpoint={ocreds.endpoint}, deployment={ocreds.dalle_deployment})")
    except AzureCredsError as e:
        print(f"  openai:     SKIP — {e}")
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
