"""_narrative.py — deterministic narrative-frame, attribution, and script guards.

Pure functions, no LLM shellouts, shared by EVERY route that rewrites book prose:
the author-companion re-voice and the fluency de-calque (`_book_voice.py`), and
the translation edition (`_translation_edition.py`). Route-agnostic on purpose —
the defects below are properties of the SOURCE being mishandled, not of the
product being built, so a rule that lived in one route would simply wait to be
rediscovered in the next.

Every check here answers a failure that actually shipped on
`the-master-and-the-disciple` (2026-07-19/20) and that no existing gate caught:

  * ``narrative_person_findings`` — the re-voice converted an anonymous
    transmitted report into a participant narrator, differently in different
    chapters, so one volume ended up with four narrators.
  * ``speech_tag_findings`` — a tag inserted into a paragraph the source left
    untagged handed the Master's own indictment to his opponent.
  * ``arabic_retention_findings`` — replacing Arabic script with a Latin
    transliteration deletes the very text an argument about letters depends on.
  * ``supplied_diacritics_findings`` — vowel marks written from model memory onto
    an unvowelled source are fabricated scripture, the worst defect available.
  * ``enumeration_findings`` — dissolving the source's lettered items into
    running prose loses no words and destroys the argument's skeleton, which is
    why every word-level fidelity check passes it.

KNOWN GAP, deliberately NOT papered over (2026-07-20). ``supplied_diacritics_findings``
compares a rewrite against its own base, so it cannot see vowelling fabricated at
TRANSLATION time and baked into the base itself — which is how one live run reached
the printed edition fully vowelled while the scan carried it bare. Three attempts at
a scan-grounded guard were tried and REMOVED: the scan is itself inconsistently
vowelled, so a bare-portion comparison misses the real case, and an equality or
containment comparison returns a list dominated by canonical Quran that is
legitimately vowelled. Closing this needs a canonical mushaf corpus to verify
against (the knowledge base holds ~9.5k chars, nowhere near enough). Until then it
is the challenger's BK-N5 and the Arabic audit's `unverified` bucket that carry it,
and both are judgment, not arithmetic.

Detection philosophy: HIGH PRECISION over recall. Each check fires only on
evidence it can point at, because a false revert costs a chapter while a missed
finding is still caught downstream by the `book-challenger` agent's semantic
pass. Where a check inspects a window rather than whole text, that mirrors the
existing `narrative_opening_findings` convention in `_book_voice.py`.
"""

from __future__ import annotations

import re
import unicodedata

from _arabic_coverage import arabic_run_spans, normalize_arabic
from _mushaf import is_quranic, mushaf_available
from _rules import (
    DEFAULT_NARRATIVE_FRAME,
    NARRATIVE_FRAMES,
    R_ARABIC_TASHKEEL,
    narrative_person_for,
)

# Speech tags live at the head of a paragraph. Every real defect found on the
# live book landed inside this window, and confining the scan to it is what keeps
# the check from reverting legitimate first-person prose INSIDE quoted speech —
# which is where first person belongs even under a third-person frame.
_ATTRIBUTION_WINDOW = 140

_ARABIC_RUN_RE = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]{2,}")
_TASHKEEL_CHARS = frozenset(chr(cp) for lo, hi in R_ARABIC_TASHKEEL for cp in range(lo, hi + 1))

# First-person narration in an ATTRIBUTION position — the narrator reporting that
# someone spoke to him, or naming a character as his own. These are frame markers,
# not register markers: they cannot appear in a transmitted report.
_FIRST_PERSON_ATTRIBUTION = (
    (re.compile(r"\b(?:he|she|they) (?:told|said to|asked) (?:me|us)\b", re.I), "narrator is spoken to"),
    (re.compile(r"\bcame to (?:me|us) and (?:said|asked)\b", re.I), "narrator is approached"),
    (
        re.compile(r"\b(?:and |so |then )?I (?:said|say|asked|answered|replied|told) (?:to )?(?:him|her|them)\b", re.I),
        "narrator speaks",
    ),
    (
        # SUBJECT position only. "My father stood over me" is the narrator
        # claiming a relationship; "my son, you have heard the charge" is a
        # VOCATIVE inside a character's own speech — correct under every frame,
        # and so common in a dialogue text that six of the eight live base
        # chapters trip a bare match. Requiring a following verb separates them.
        re.compile(
            r"\bmy (?:Master|Shaykh|Sheikh|teacher|father|mother|son|companion)\s+"
            r"(?:said|told|asked|answered|replied|spoke|began|stood|came|went|opened|"
            r"put|turned|looked|took|gave|held|sat|rose)\b",
            re.I,
        ),
        "narrator claims a relationship",
    ),
    (re.compile(r"\bI (?:have )?(?:set down|recount|relate|write|record)\b", re.I), "narrator claims authorship"),
)

# The mirror case: a first-person frame that lapses back into reporting its own
# narrator from outside. `narrator_subject` supplies the name to look for.
_THIRD_PERSON_SELF_REPORT = r"\b{name}\b\s+(?:said|replied|answered|asked|went|stood|came)\b"

# INTERIOR tags — an attribution that INTERRUPTS a quotation: `..." he said, "...`.
# This is the shape of the live P0: the source ran a paragraph on unbroken inside
# one speaker's speech, and the rewrite cut in with `," he said, "`, which re-points
# everything after it to whoever the narration last named. A tag at the HEAD of a
# paragraph ("The scholar said:") is an ordinary attribution and rewording one is
# harmless — counting those made a de-calque pass that legitimately reworded an
# opening look like an insertion, which cost a real chapter its pass on the first
# live run. Only interior tags are gated; head tags are left to the challenger.
_INTERIOR_TAG_RE = re.compile(
    r"[\"”]\s*,?\s*(?:[A-Z][\w'\-]*(?:\s+[A-Z][\w'\-]*)?|he|she|they)\s+"
    r"(?:said|replied|answered|asked|told)\b"
)

# Source-style enumeration markers at the head of a paragraph: "(a)", "(1)", "1.".
_ENUM_MARKER_RE = re.compile(r"(?m)^\s*(?:\(([a-z]|[0-9]{1,2})\)|([0-9]{1,2})\.)\s+\S")


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", (text or "").strip()) if p.strip()]


def _attribution_zones(text: str) -> list[str]:
    """The opening window of each paragraph, where speech tags live."""
    return [p[:_ATTRIBUTION_WINDOW] for p in _paragraphs(text)]


def narrative_person_findings(
    text: str,
    frame: str,
    *,
    narrator_subject: str = "",
) -> list[str]:
    """Flag narration whose grammatical person contradicts the book's frame.

    Scans only paragraph-opening attribution windows, so first person inside a
    character's quoted speech — correct under every frame — is never flagged.
    """
    findings: list[str] = []
    person = narrative_person_for(frame)
    zones = _attribution_zones(text)
    if person == "third":
        for zone in zones:
            for pattern, label in _FIRST_PERSON_ATTRIBUTION:
                hit = pattern.search(zone)
                if hit:
                    findings.append(f"first-person narration under {frame} frame ({label}): {hit.group(0)!r}")
                    break
    elif person == "first" and narrator_subject:
        self_report = re.compile(_THIRD_PERSON_SELF_REPORT.format(name=re.escape(narrator_subject)), re.I)
        for zone in zones:
            hit = self_report.search(zone)
            if hit:
                findings.append(
                    f"narrator {narrator_subject!r} reported in third person under {frame} frame: {hit.group(0)!r}"
                )
    # Dedupe while preserving order; one representative per distinct message.
    seen: set[str] = set()
    return [f for f in findings if not (f in seen or seen.add(f))]


def speech_tag_findings(base_text: str, candidate: str) -> list[str]:
    """Flag speech tags the rewrite added relative to its source.

    A rewrite may reword a tag; it may not cut a NEW one into a quotation. An
    interior tag re-points everything after it to whoever the narration last
    named, which is how a doctrinal argument ends up attributed to the person it
    argues against.

    Scoped to INTERIOR tags only. Gating the whole-chapter tag count instead
    conflated that defect with harmless rewording of an opening attribution, and
    on the first live de-calque run it reverted a chapter for exactly that.
    """
    base_n = len(_INTERIOR_TAG_RE.findall(base_text or ""))
    cand_n = len(_INTERIOR_TAG_RE.findall(candidate or ""))
    if cand_n > base_n:
        return [
            f"speech tag cut into a quotation ({cand_n} interior vs {base_n} in source) — attribution may have moved"
        ]
    return []


def _arabic_runs(text: str) -> list[str]:
    return [unicodedata.normalize("NFC", r) for r in _ARABIC_RUN_RE.findall(text or "")]


def _strip_tashkeel(run: str) -> str:
    return "".join(ch for ch in run if ch not in _TASHKEEL_CHARS)


def arabic_retention_findings(base_text: str, candidate: str) -> list[str]:
    """Flag Arabic script present in the source but missing from the rewrite.

    Set-based rather than count-based: a rewrite that drops one quotation and
    invents another keeps the count identical and passes a counting check.
    Transliterating a run away is the common way this happens — the Latin form
    reads fine, and the script the argument depends on is simply gone.
    """
    base_skeletons = {_strip_tashkeel(r) for r in _arabic_runs(base_text)}
    cand_skeletons = {_strip_tashkeel(r) for r in _arabic_runs(candidate)}
    missing = base_skeletons - cand_skeletons
    if not missing:
        return []
    sample = "; ".join(sorted(missing)[:3])
    return [f"Arabic script dropped ({len(missing)} run(s)) — replaced or removed: {sample}"]


def supplied_diacritics_findings(base_text: str, candidate: str) -> list[str]:
    """Flag vowel marks the rewrite added to an unvowelled source run.

    Tashkeel written from model memory onto an unvowelled scan is fabricated
    scripture. Matching is by consonantal skeleton, so a run that merely moved
    within the chapter is still compared against its own source form.
    """
    # ALL source forms per skeleton, not just the last one. A word like `الله`
    # occurs many times in one chapter, vowelled in a scripture block and bare in
    # running prose; keeping only the last occurrence made a chapter compared
    # against ITSELF report supplied diacritics.
    base_vowelled: dict[str, bool] = {}
    for run in _arabic_runs(base_text):
        skeleton = _strip_tashkeel(run)
        base_vowelled[skeleton] = base_vowelled.get(skeleton, False) or bool(set(run) & _TASHKEEL_CHARS)
    findings: list[str] = []
    for run in _arabic_runs(candidate):
        skeleton = _strip_tashkeel(run)
        if skeleton not in base_vowelled:
            continue
        if (set(run) & _TASHKEEL_CHARS) and not base_vowelled[skeleton]:
            findings.append(f"diacritics supplied onto unvowelled source run: {run[:40]}")
    return findings[:3]


def ocr_vowelling_findings(text: str, ocr_text: str, *, limit: int = 8) -> list[str]:
    """Flag NON-Quranic runs vowelled beyond what the scan carries.

    Closes the gap ``supplied_diacritics_findings`` cannot see: that one compares
    a rewrite against its own base, so vowelling fabricated at TRANSLATION time
    and baked into the base is invisible to it — which is how one live run reached
    the printed edition fully vowelled while the scan carried it bare.

    The discriminator this needs is ``_mushaf.is_quranic``. Canonical Quran is
    LEGITIMATELY vowelled whatever the scan does, and without a way to recognise
    it every earlier attempt returned a review list that was mostly verses. With
    the mushaf wired in, only the runs that are the source's OWN words are held to
    the scan's vowelling.

    Returns [] when the mushaf is unavailable rather than flagging everything —
    a checkout without the mirror gets no signal, not a false one.
    """
    if not ocr_text or not mushaf_available():
        return []
    scan_bare = normalize_arabic("".join(s for s in arabic_run_spans(ocr_text) if not (set(s) & _TASHKEEL_CHARS)))
    findings: list[str] = []
    for span in arabic_run_spans(text):
        if not (set(span) & _TASHKEEL_CHARS) or is_quranic(span):
            continue
        skeleton = normalize_arabic(span)
        if skeleton and skeleton in scan_bare:
            findings.append(f"non-Quranic run vowelled beyond the scan: {span[:44]}")
    return findings[:limit]


def enumeration_findings(base_text: str, candidate: str, *, minimum: int = 3) -> list[str]:
    """Flag a source enumeration dissolved into running prose.

    Loses no words, so every word-level fidelity check passes it — while a text
    that argues by enumerated structure loses the structure the argument hangs on.
    Only fires when the source enumerates substantially (``minimum`` items).
    """
    base_n = len(_ENUM_MARKER_RE.findall(base_text or ""))
    if base_n < minimum:
        return []
    cand_n = len(_ENUM_MARKER_RE.findall(candidate or ""))
    if cand_n < base_n:
        return [f"source enumeration lost ({cand_n} of {base_n} items survive as items)"]
    return []


def frame_prompt_directive(frame: str, narrator_subject: str = "") -> str:
    """The instruction block that makes a model PRODUCE what the guards enforce.

    Gates alone would simply revert every chapter: a model told to write an
    intimate first-person companion and then failed for doing so burns a pass and
    ships the base. The prompt and the gate must state the same rule, so this is
    the single place that rule is worded for both.
    """
    spec = NARRATIVE_FRAMES.get(frame) or NARRATIVE_FRAMES[DEFAULT_NARRATIVE_FRAME]
    if spec["person"] == "third":
        who = (
            "an anonymous transmitter reporting what passed between other people"
            if frame == "transmitted_report"
            else "a narrator outside the story who never appears in it"
        )
        return f"""
NARRATIVE FRAME (binding — this is the source's structure, not a style preference)
Narrate in the THIRD PERSON. The narrator is {who}, and is NOT a character.
Write "The Master said", "The boy said", "he asked" — never "my Master", "he told
me", "I said to him", or "the boy came to me". First person appears ONLY inside a
character's own quoted speech, where it belongs.
Do NOT add, remove, or re-point a speech tag. If the source attributes a passage
to a speaker, keep that attribution; if the source leaves a paragraph untagged,
leave it untagged. An invented tag hands one person's words to another.
"""
    named = f" You are {narrator_subject}." if narrator_subject else ""
    return f"""
NARRATIVE FRAME (binding — this is the source's structure, not a style preference)
Narrate in the FIRST PERSON throughout, consistently, from the opening word.{named}
Never lapse into reporting yourself from outside{f' as "{narrator_subject} said"' if narrator_subject else ""}.
Do NOT add, remove, or re-point a speech tag. If the source attributes a passage
to a speaker, keep that attribution; if the source leaves a paragraph untagged,
leave it untagged. An invented tag hands one person's words to another.
"""


ARABIC_DIRECTIVE = """
ARABIC (binding)
Reproduce every Arabic-script run EXACTLY as given, character for character.
Never replace Arabic script with a Latin transliteration. Where the passage
discusses the Arabic AS LETTERS, keep the script and add the transliteration
beside it in parentheses.
Never add vowel marks (tashkeel) that the source does not have. Diacritics are
carried from the source or they are absent — never written from memory.

STRUCTURE (binding)
If the source enumerates — lettered or numbered items — keep the enumeration as
enumeration. Do not dissolve it into running prose.
"""


def frame_findings(
    base_text: str,
    candidate: str,
    *,
    frame: str,
    narrator_subject: str = "",
) -> list[str]:
    """Every deterministic narrative guard, in one call for route wiring."""
    findings: list[str] = []
    findings.extend(narrative_person_findings(candidate, frame, narrator_subject=narrator_subject))
    findings.extend(speech_tag_findings(base_text, candidate))
    findings.extend(arabic_retention_findings(base_text, candidate))
    findings.extend(supplied_diacritics_findings(base_text, candidate))
    findings.extend(enumeration_findings(base_text, candidate))
    return findings
