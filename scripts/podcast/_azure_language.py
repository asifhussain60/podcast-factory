"""scripts/podcast/_azure_language.py — Azure Language (TextAnalytics) helpers.

NER, key-phrase extraction, and sentiment analysis for the augmentation pipeline.
Extracted verbatim from _azure.py (R3 DR-005 split, 2026-07-18); behavior unchanged.
_azure.py re-exports every name here, so `import _azure` call sites keep working.
"""

from __future__ import annotations

import json
from typing import Any

from _azure_creds import LanguageCreds
from _azure_http import _http

LANGUAGE_API_VERSION = "2023-04-01"
LANGUAGE_MAX_DOCS_PER_REQUEST = 5  # conservative; API allows 25, but batching keeps latency low
LANGUAGE_MAX_CHARS_PER_DOC = 5_000  # well under the 125,000-char hard limit


def _language_post(creds: LanguageCreds, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST to the Language API and return the parsed JSON response."""
    url = f"{creds.endpoint}/language/:analyze-text?api-version={LANGUAGE_API_VERSION}"
    body = json.dumps({**payload, "analysisInput": payload.get("analysisInput", {})}).encode("utf-8")
    status, _, resp_body = _http(
        "POST",
        url,
        headers={
            "Ocp-Apim-Subscription-Key": creds.key,
            "Content-Type": "application/json; charset=UTF-8",
        },
        body=body,
    )
    if status != 200:
        raise RuntimeError(
            f"Language API {path} failed: HTTP {status}\n{resp_body.decode('utf-8', errors='replace')[:600]}"
        )
    return json.loads(resp_body)


def extract_key_phrases(creds: LanguageCreds, texts: list[str]) -> list[list[str]]:
    """Extract key phrases from a list of texts.

    Returns a parallel list of key-phrase lists, one per input text. Batches
    internally to stay under API limits.

    Used by the augmentation pipeline for topic identification and episode
    planning: surface the dominant concepts in a chapter before deciding
    whether enrichment is needed.
    """
    results: list[list[str]] = []
    for i in range(0, len(texts), LANGUAGE_MAX_DOCS_PER_REQUEST):
        batch = texts[i : i + LANGUAGE_MAX_DOCS_PER_REQUEST]
        docs = [{"id": str(j), "text": t[:LANGUAGE_MAX_CHARS_PER_DOC], "language": "en"} for j, t in enumerate(batch)]
        payload = {
            "kind": "KeyPhraseExtraction",
            "analysisInput": {"documents": docs},
        }
        resp = _language_post(creds, "KeyPhraseExtraction", payload)
        docs_out = {d["id"]: d for d in resp.get("results", {}).get("documents", [])}
        for j in range(len(batch)):
            phrases = docs_out.get(str(j), {}).get("keyPhrases", [])
            results.append(phrases)
    return results


def extract_named_entities(
    creds: LanguageCreds,
    texts: list[str],
    *,
    categories: list[str] | None = None,
) -> list[list[dict[str, Any]]]:
    """Extract named entities from a list of texts.

    Each entity dict has keys: `text`, `category`, `subcategory`, `confidenceScore`.
    Common categories: Person, Location, Organization, Event, DateTime, Quantity.

    Pass `categories` to filter (e.g. `["Person", "Location"]`). Used by the
    augmentation pipeline to detect characters, places, and events in fiction
    chapters, and to find uncited people/works in scholarly text.
    """
    results: list[list[dict[str, Any]]] = []
    for i in range(0, len(texts), LANGUAGE_MAX_DOCS_PER_REQUEST):
        batch = texts[i : i + LANGUAGE_MAX_DOCS_PER_REQUEST]
        docs = [{"id": str(j), "text": t[:LANGUAGE_MAX_CHARS_PER_DOC], "language": "en"} for j, t in enumerate(batch)]
        payload = {
            "kind": "EntityRecognition",
            "analysisInput": {"documents": docs},
        }
        resp = _language_post(creds, "EntityRecognition", payload)
        docs_out = {d["id"]: d for d in resp.get("results", {}).get("documents", [])}
        for j in range(len(batch)):
            entities = docs_out.get(str(j), {}).get("entities", [])
            if categories:
                entities = [e for e in entities if e.get("category") in categories]
            results.append(entities)
    return results


def analyze_sentiment(
    creds: LanguageCreds,
    texts: list[str],
) -> list[dict[str, Any]]:
    """Analyze sentiment for a list of texts.

    Each result dict has keys: `sentiment` ("positive"/"neutral"/"negative"),
    `confidenceScores` ({positive, neutral, negative} floats).

    Used by the fiction augmentation pipeline for arc analysis: detecting
    tone shifts between episodes (tension, resolution, comic relief).
    """
    results: list[dict[str, Any]] = []
    for i in range(0, len(texts), LANGUAGE_MAX_DOCS_PER_REQUEST):
        batch = texts[i : i + LANGUAGE_MAX_DOCS_PER_REQUEST]
        docs = [{"id": str(j), "text": t[:LANGUAGE_MAX_CHARS_PER_DOC], "language": "en"} for j, t in enumerate(batch)]
        payload = {
            "kind": "SentimentAnalysis",
            "analysisInput": {"documents": docs},
        }
        resp = _language_post(creds, "SentimentAnalysis", payload)
        docs_out = {d["id"]: d for d in resp.get("results", {}).get("documents", [])}
        for j in range(len(batch)):
            doc = docs_out.get(str(j), {})
            results.append(
                {
                    "sentiment": doc.get("sentiment", "neutral"),
                    "confidenceScores": doc.get("confidenceScores", {}),
                }
            )
    return results
