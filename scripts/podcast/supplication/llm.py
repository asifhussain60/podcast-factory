"""llm.py — steps 3 and 5, the only two model calls in the lane.

Both go through the Anthropic SDK, never the interactive `claude -p` binary:
this lane runs unattended, and DR-015 requires unattended spend to stay on the
isolated metered pool (see tests/test_no_claude_p_in_unattended.py).

WHAT THE MODEL IS AND IS NOT ALLOWED TO PRODUCE
-----------------------------------------------
segment()    emits GROUPINGS ONLY — arrays of OCR line ids. It never echoes,
             retypes, normalizes, or "cleans" source text. The prompt shows the
             model numbered lines and asks for numbers back.

translate()  emits ENGLISH ONLY — one string per unit. The source it is shown
             is derived from the immutable record and is never written back.

Because neither call can return source text, there is no code path by which
model output reaches the source column of the PDF. gates.py then re-proves this
independently.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from .schema import (  # noqa: E402
    SourceRecord,
    SupplicationError,
    Unit,
    UnitsDoc,
    derive_source,
    refrain_units,
)

SEGMENT_MODEL = "claude-sonnet-4-6"
TRANSLATE_MODEL = "claude-opus-4-8"

# Lines per segmentation request. Small enough that the model sees every line in
# a window it can reason over, large enough that phrase units spanning a few
# lines are never cut by the window edge (the overlap below handles the seam).
SEGMENT_WINDOW = 60

LANG_NAME = {"ar": "Arabic", "ur": "Urdu"}


def _client():
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - environment guard
        raise SupplicationError("anthropic package not installed. Run: pip install anthropic") from exc
    from _secrets import get_anthropic_key

    return anthropic.Anthropic(api_key=get_anthropic_key())


def _json_block(raw: str) -> dict:
    """Pull the first JSON object out of a model response."""
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise SupplicationError(f"no JSON object in model response: {raw[:300]!r}")
    return json.loads(raw[start:end])


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — segmentation (boundaries only)
# ─────────────────────────────────────────────────────────────────────────────

_SEGMENT_SYSTEM = """You are segmenting the {lang} text of a supplication (du'a, ziyarat, or munajat) into semantic PHRASE UNITS for a facing-column reading edition: English on the left, {lang} on the right, each unit's two cells sharing one row.

You will be shown the supplication's OCR lines, each with an id. OCR wraps text at the physical width of the page, so a single line is usually NOT a complete phrase.

Your job is to decide where one unit ENDS and the next BEGINS.

RULES — these are absolute:
1. Output ONLY line ids. Never reproduce, retype, transliterate, correct, or comment on the {lang} text. The source text is handled elsewhere and your output is discarded if it contains any.
2. Every line id you are given must appear in EXACTLY ONE unit. Drop nothing, duplicate nothing.
3. Keep the original order. A unit's ids must be consecutive.
4. A unit should be one breath of invocation — a complete address, petition, or clause that a reader can hold beside its English rendering. Typically 1-3 OCR lines. Prefer a slightly longer unit over splitting a grammatical clause in half.

Return ONLY this JSON:
{{"units": [{{"line_ids": ["p1l4", "p1l5"]}}]}}"""


def segment(
    record: SourceRecord,
    *,
    client=None,
    window: int = SEGMENT_WINDOW,
    log=print,
) -> UnitsDoc:
    """Group the OCR record's lines into phrase units. Returns an UNTRANSLATED doc."""
    cl = client or _client()
    lang = LANG_NAME[record.source_language]
    system = _SEGMENT_SYSTEM.format(lang=lang)

    grouped: list[dict] = []
    consumed = 0
    lines = record.lines
    while consumed < len(lines):
        chunk = lines[consumed : consumed + window]
        is_last = consumed + len(chunk) >= len(lines)
        body = "\n".join(f"{ln.id}\t{ln.text}" for ln in chunk)
        raw = _call(cl, SEGMENT_MODEL, system, body, max_tokens=4096)
        units = _json_block(raw).get("units") or []
        if not units:
            raise SupplicationError(f"segmentation returned no units for window at line {consumed}")

        valid_ids = {ln.id for ln in chunk}
        cleaned: list[dict] = []
        for u in units:
            ids = [i for i in (u.get("line_ids") or []) if i in valid_ids]
            if ids:
                cleaned.append({"line_ids": ids})

        # Drop the final unit of a non-final window: it may have been cut by the
        # window edge mid-phrase. Its lines are re-offered at the head of the
        # next window so the seam is decided with full context.
        if not is_last and len(cleaned) > 1:
            cleaned.pop()

        taken = sum(len(u["line_ids"]) for u in cleaned)
        if taken == 0:
            raise SupplicationError(f"segmentation made no progress at line {consumed}")
        grouped.extend(cleaned)
        consumed += taken
        log(f"  segmented {consumed}/{len(lines)} lines → {len(grouped)} units")

    # Repair pass: any line the model skipped is attached to the preceding unit
    # rather than lost. The coverage gate (G-SUP-3) is still the authority — this
    # only prevents a single dropped line from failing an otherwise good run.
    grouped = _reattach_gaps(grouped, [ln.id for ln in lines])

    return UnitsDoc(
        slug=record.slug,
        source_language=record.source_language,
        source_digest=record.digest,
        units=[Unit(n=i + 1, line_ids=g["line_ids"]) for i, g in enumerate(grouped)],
    )


def _reattach_gaps(grouped: list[dict], all_ids: list[str]) -> list[dict]:
    """Fold any unassigned line into the unit that precedes it in reading order."""
    assigned = {i for g in grouped for i in g["line_ids"]}
    missing = [i for i in all_ids if i not in assigned]
    if not missing:
        return grouped
    pos = {i: n for n, i in enumerate(all_ids)}
    for mid in missing:
        target = None
        for g in grouped:
            if pos[g["line_ids"][-1]] < pos[mid]:
                target = g
            else:
                break
        if target is None:
            grouped.insert(0, {"line_ids": [mid]})
        else:
            target["line_ids"].append(mid)
            target["line_ids"].sort(key=lambda i: pos[i])
    return grouped


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — translation (English only)
# ─────────────────────────────────────────────────────────────────────────────

_TRANSLATE_SYSTEM = """You are rendering a {lang} supplication (du'a, ziyarat, or munajat) into English for a facing-column reading edition. The English sits in the LEFT column beside its {lang} original on the right, unit by unit.

You will be given numbered units. Return an English rendering for each.

RULES — these are absolute:
1. STRICTLY 1:1. Unit n's English renders unit n's {lang} and nothing else. Never merge two units, never split one, never move content between them, never add a unit.
2. Do NOT return {lang} text, transliteration, or the original script in any field. Only English.
3. Translate what is there. Add no gloss, no explanation, no bracketed clarification, no honorific that the source does not contain.
4. Articulate, dignified, contemporary English in the register of devotional address — not archaic pastiche, not casual. Keep the vocative force of invocations ("O You who...").
5. Preserve parallelism: when consecutive units share a rhetorical shape in the original, let the English echo that shape too. A litany should read as a litany.
6. A unit marked as a refrain recurs verbatim; render it IDENTICALLY every time it appears.
7. Divine names and the names of the Prophet and the Imams: render conventionally and consistently across the whole document. Never substitute one name for another.

Return ONLY this JSON:
{{"translations": [{{"n": 1, "english": "..."}}]}}"""

# Units per translation request. Small enough for careful per-unit attention,
# large enough that parallelism across a litany is visible in one window.
TRANSLATE_BATCH = 12


def translate(
    doc: UnitsDoc,
    record: SourceRecord,
    *,
    client=None,
    batch: int = TRANSLATE_BATCH,
    log=print,
) -> UnitsDoc:
    """Fill in each unit's `english`. Mutates and returns `doc`.

    The source shown to the model is DERIVED from the immutable record; the
    model's reply is read for `english` only, so nothing it emits can reach the
    source column.
    """
    cl = client or _client()
    lang = LANG_NAME[doc.source_language]
    system = _TRANSLATE_SYSTEM.format(lang=lang)
    index = record.by_id()
    by_n = {u.n: u for u in doc.units}
    # Derived, not model-decided (schema.refrain_units): a unit is a refrain iff
    # its source text repeats verbatim in this document. Passed to the model so
    # repeated source gets an identical English rendering every time.
    refrains = refrain_units(doc, record)

    pending = [u for u in doc.units if not (u.english or "").strip()]
    for start in range(0, len(pending), batch):
        group = pending[start : start + batch]
        payload = {
            "units": [
                {
                    "n": u.n,
                    "source": derive_source(u.line_ids, index),
                    "refrain": u.n in refrains,
                }
                for u in group
            ]
        }
        raw = _call(cl, TRANSLATE_MODEL, system, json.dumps(payload, ensure_ascii=False), max_tokens=8192)
        for t in _json_block(raw).get("translations") or []:
            n = t.get("n")
            en = (t.get("english") or "").strip()
            if n in by_n and en:
                if _has_source_script(en, doc.source_language):
                    raise SupplicationError(
                        f"unit {n}: translation contains {lang} script — the English column is "
                        f"English-only by contract. Refusing to write it."
                    )
                by_n[n].english = en
        log(f"  translated {min(start + batch, len(pending))}/{len(pending)} units")

    return doc


_ARABIC_SCRIPT = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")


def _has_source_script(text: str, lang: str) -> bool:
    """Both ar and ur use the Arabic script block; one test covers both."""
    return bool(_ARABIC_SCRIPT.search(text))


def _call(client, model: str, system: str, body: str, *, max_tokens: int) -> str:
    """One SDK call. The stable system block is cached across windows."""
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": body}],
    )
    return msg.content[0].text if msg.content else ""
