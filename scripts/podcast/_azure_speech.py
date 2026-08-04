#!/usr/bin/env python3
"""Azure Speech — Fast Transcription, and the two ways we ask for it.

Split out of `_azure.py` when that facade crossed the 600-line gate. It is the
same code and the same request; `_azure` re-exports every name here, so
`_azure.transcribe_audio(...)` and `from _azure import SPEECH_AUDIO_MIME` both
still work and no caller changed.

Two entry points on purpose:

    transcribe_audio        returns the flat text, as it always has, to five
                            callers that want a `str` and nothing else
    transcribe_audio_timed  returns the same text PLUS the per-phrase clock the
                            response has always carried and this module used to
                            discard

Keeping the first exactly as it was is the point of having two. See the note on
`transcribe_audio_timed` for what the response actually contains.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from _azure_creds import SpeechCreds
from _azure_http import _http

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
    parts.append(f'Content-Disposition: form-data; name="audio"; filename="{audio_filename}"'.encode("utf-8") + nl)
    parts.append(f"Content-Type: {audio_mime}".encode("ascii") + nl)
    parts.append(nl)
    parts.append(audio_bytes + nl)
    parts.append(f"--{boundary}--".encode("ascii") + nl)
    return b"".join(parts)


@dataclass(frozen=True)
class Phrase:
    """One run of speech, with the clock the API already sends back.

    `speaker` is None unless diarization was asked for; it is a small integer
    (1, 2, …) the service assigns, NOT a name, and nothing here pretends to know
    which host is which.
    """

    offset_ms: int
    duration_ms: int
    text: str
    speaker: int | None = None


@dataclass(frozen=True)
class TimedTranscript:
    """The same transcript `transcribe_audio` returns, plus where each line falls."""

    text: str
    phrases: tuple[Phrase, ...]
    duration_ms: int


def transcribe_audio_timed(
    creds: SpeechCreds,
    audio_bytes: bytes,
    audio_filename: str,
    *,
    locale: str = SPEECH_DEFAULT_LOCALE,
    diarize: bool = True,
    max_speakers: int = 2,
    timeout_s: float = 900.0,
) -> TimedTranscript:
    """Transcribe, and KEEP the per-phrase clock instead of discarding it.

    A sibling of `transcribe_audio` rather than a change to it. That function
    returns a plain `str` to five call sites — lecture transcription, episode
    transcription, reference audio, the dialogue renderer, NotebookLM output —
    and widening its return type would break every one of them for the benefit of
    a caller none of them are. So the HTTP request below is deliberately the same
    request; only the parsing differs.

    What the response carries (probed 2026-08-04 against api-version 2024-11-15,
    on a 9-minute episode):

        combinedPhrases[0].text   the flat transcript, and the ONLY field
                                  `transcribe_audio` has ever read
        phrases[]                 181 entries, each with offsetMilliseconds,
                                  durationMilliseconds, text, confidence, locale
                                  and a words[] of its own with per-word offsets
        phrases[].speaker         present ONLY when diarization is enabled

    Median phrase: 2.0 seconds, 37 characters — sentence-fragment granularity,
    which is the right size for a transcript that follows playback. Word-level
    offsets are available in the same response and are deliberately dropped here:
    they are ten times the bytes for a refinement nothing has asked for, and
    re-asking for them costs one more call, not a redesign.

    Diarization is ON by default because these are two-host conversations and a
    wall of undifferentiated text is a poor reading of one. It is the same price.
    """
    ext = audio_filename.lower().rsplit(".", 1)[-1] if "." in audio_filename else ""
    audio_mime = SPEECH_AUDIO_MIME.get(ext, "application/octet-stream")

    definition: dict[str, object] = {"locales": [locale]}
    if diarize:
        definition["diarization"] = {"maxSpeakers": max_speakers, "enabled": True}

    boundary = f"----PodcastFormBoundary{os.urandom(16).hex()}"
    body = _multipart_body(
        boundary=boundary,
        audio_filename=audio_filename,
        audio_mime=audio_mime,
        audio_bytes=audio_bytes,
        definition_json=json.dumps(definition).encode("utf-8"),
    )

    url = f"{creds.endpoint}/speechtotext/transcriptions:transcribe?api-version={SPEECH_API_VERSION}"
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
            f"Speech transcribe failed: HTTP {status}\n{response_body.decode('utf-8', errors='replace')[:600]}"
        )

    data = json.loads(response_body)
    combined = data.get("combinedPhrases") or []
    text = "\n\n".join(p.get("text", "") for p in combined if p.get("text"))

    phrases: list[Phrase] = []
    for raw in data.get("phrases") or []:
        said = (raw.get("text") or "").strip()
        if not said:
            continue
        speaker = raw.get("speaker")
        phrases.append(
            Phrase(
                offset_ms=int(raw.get("offsetMilliseconds") or 0),
                duration_ms=int(raw.get("durationMilliseconds") or 0),
                text=said,
                speaker=int(speaker) if isinstance(speaker, int) else None,
            )
        )

    return TimedTranscript(
        text=text,
        phrases=tuple(phrases),
        duration_ms=int(data.get("durationMilliseconds") or 0),
    )


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

    url = f"{creds.endpoint}/speechtotext/transcriptions:transcribe?api-version={SPEECH_API_VERSION}"
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
            f"Speech transcribe failed: HTTP {status}\n{response_body.decode('utf-8', errors='replace')[:600]}"
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
