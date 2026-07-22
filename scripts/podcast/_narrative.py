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

THE VOWELLING GAP, and how it was closed (2026-07-20). ``supplied_diacritics_findings``
compares a rewrite against its own base, so it cannot see vowelling fabricated at
TRANSLATION time and baked into the base itself — which is how one live run reached
the printed edition fully vowelled while the scan carried it bare. Three attempts at
a scan-grounded guard were tried and REMOVED: the scan is itself inconsistently
vowelled, so a bare-portion comparison misses the real case, and an equality or
containment comparison returns a list dominated by canonical Quran that is
legitimately vowelled.

What unblocked it was a discriminator for canonical scripture, which turned out to
need no new corpus at all — ``content/knowledge-base/mirror.db`` already carried all
6,236 ayat, tracked in git and never wired to verification. ``ocr_vowelling_findings``
below uses ``_mushaf.is_quranic`` to exclude canonical verses, which are legitimately
vowelled whatever the scan does, and reports only the rest. It ships ADVISORY, as
``vowelling_review`` in ``_system/book-arabic-audit.json``, and never enters
``frame_findings``: a wrong revert costs real authored text, so this one surfaces for
a human instead of acting. The challenger's BK-N5 remains the judgment-based backstop.

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

# Shortest Arabic run the vowelling review will judge at all. Matches the word
# floor `_mushaf.is_quranic` needs to beat coincidence — below it, neither
# "this is scripture" nor "this is fabricated" can be supported by evidence.
_MIN_JUDGED_WORDS = 3

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
#
# The whitespace between the closing quote and the tag is HORIZONTAL ONLY. With a
# plain `\s*` the match crossed the blank line between paragraphs, so an ordinary
# head attribution following a closed quotation — `...meaning."\n\nThe boy said:` —
# counted as interior, which is precisely the case the comment above says must not
# count. On a nine-chapter book that was 284 of 320 matches: the real signal was
# swamped, and any pass that legitimately ADDED quotation marks tripped the gate
# purely by closing quotes it had opened. An interior tag interrupts a quotation
# on its own line; a newline between them means the quotation already ended.
_INTERIOR_TAG_RE = re.compile(
    r"[\"”][^\S\n]*,?[^\S\n]*(?:[A-Z][\w'\-]*(?:[^\S\n]+[A-Z][\w'\-]*)?|he|she|they)[^\S\n]+"
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


_VOWELLING_EXCESS = 0.12
"""How much more marked than its scan a run must be before it is called fabricated.

Compared as DENSITY, not presence, because the earlier rule only ever built its
haystack from scan spans carrying NO marks at all — so a span the scanner had
lightly marked exempted everything inside it. That is not a corner case: the
chapter 2 sermon close of `the-master-and-the-disciple` carries three marks in
twenty-three words, the book printed it fully vowelled from model memory, and the
check stayed silent because those three marks disqualified the whole span from
being a witness. A challenger found it by reading the Arabic against the scan.

0.12 marks per letter sits well above the noise of a scanner marking a shadda
here and a tanween there (the live case: 0.03) and well below anything a genuine
re-vowelling produces (that same run in the book: 0.48).
"""


def _mark_density(span: str) -> float:
    """Tashkeel marks per Arabic letter. 0.0 for an empty or unmarked run."""
    letters = sum(1 for ch in span if ch.isalpha() and ch not in _TASHKEEL_CHARS)
    if not letters:
        return 0.0
    return sum(1 for ch in span if ch in _TASHKEEL_CHARS) / letters


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

    Runs shorter than ``_MIN_JUDGED_WORDS`` are SKIPPED rather than judged. A one-
    or two-word Arabic run carries too little evidence in either direction: it is
    too short to confirm as canonical scripture (``is_quranic`` needs three words
    to beat coincidence — 17% of two-word spans of this book's own prose align
    somewhere in 6,236 verses) and therefore too short to accuse of fabrication on
    the strength of that same failure. Declining to judge is the honest outcome;
    the alternative is an accusation resting on an absence of evidence, and it was
    live — `فَيَكُونُ`, from Q 2:117, sat on this list as a suspected fabrication.

    The comparison is by mark DENSITY against the matching scan span, not by the
    scan span being bare. Requiring bareness meant one stray shadda disqualified a
    whole span from being a witness and exempted everything inside it — see
    ``_VOWELLING_EXCESS`` for the live case that reached print.

    Returns [] when the mushaf is unavailable rather than flagging everything —
    a checkout without the mirror gets no signal, not a false one.

    KNOWN RESIDUE. A verse the discriminator cannot recognise still lands here.
    Q 41:35 does, because the mushaf writes `يُلَقَّىٰهَآ` with alif maqsura where a
    modern edition writes `يُلَقَّاهَا` with alif, and the skeleton fold handles
    alif-hazf and the waw/alif words but not that pair. The fix would be to fold
    the weak letters together, and it is deliberately NOT taken: a false positive
    in `is_quranic` EXCUSES a run from this check, so loosening the discriminator
    trades a visible advisory entry for an invisible exemption. One line a
    reviewer dismisses beats one fabrication that ships.
    """
    if not ocr_text or not mushaf_available():
        return []

    # Scan vowelling, WORD by word: bare skeleton -> the most marked the scanner
    # ever set that word. Word-level because a run in the book rarely shares its
    # boundaries with a run in the scan, and a whole-run comparison inherits every
    # boundary mismatch as a false verdict.
    scan_marks: dict[str, float] = {}
    for span in arabic_run_spans(ocr_text):
        for word in span.split():
            key = normalize_arabic(word)
            if key:
                scan_marks[key] = max(scan_marks.get(key, 0.0), _mark_density(word))

    findings: list[str] = []
    for span in arabic_run_spans(text):
        if not (set(span) & _TASHKEEL_CHARS) or is_quranic(span):
            continue
        words = span.split()
        if len(words) < _MIN_JUDGED_WORDS:
            continue

        # A run may be part scripture and part the author's own words — the live
        # case is a sermon closing around Q 25:62. Judging the whole run flags the
        # verse's canonical vowelling as fabricated, so the Quranic stretches are
        # exempted first, by sliding the discriminator's own minimum window.
        quranic: set[int] = set()
        for i in range(len(words) - _MIN_JUDGED_WORDS + 1):
            window = words[i : i + _MIN_JUDGED_WORDS]
            if is_quranic(" ".join(window)):
                quranic.update(range(i, i + _MIN_JUDGED_WORDS))

        excess = 0
        for i, word in enumerate(words):
            if i in quranic:
                continue
            source = scan_marks.get(normalize_arabic(word))
            if source is None:  # the scan does not carry this word at all
                continue
            if _mark_density(word) - source >= _VOWELLING_EXCESS:
                excess += 1
        if excess >= _MIN_JUDGED_WORDS:
            findings.append(f"non-Quranic run vowelled beyond the scan: {span[:44]}")
    return findings[:limit]


def enumeration_findings(base_text: str, candidate: str, *, minimum: int = 3) -> list[str]:
    """Flag a source enumeration dissolved into running prose.

    Loses no words, so every word-level fidelity check passes it — while a text
    that argues by enumerated structure loses the structure the argument hangs on.
    Only fires when the source enumerates substantially (``minimum`` items).

    Section numbering is NOT an enumeration. A scholarly transcription that
    numbers EVERY paragraph — "(1)", "(2)", "(3)" down the whole text — is
    carrying per-paragraph apparatus, and the edition drops those numbers as
    editorial policy. Requiring their survival blocked the RCA-001 recovery
    compose on a chapter whose source numbers all of its paragraphs: the gate
    read the transcription's numbering as a 19-item argument list no faithful
    translation could ever "preserve". The discriminator is the run's SHAPE:
    a chapter slice is a WINDOW into the numbered source, so its markers run
    "(3) (4) (5)" — a consecutive ascending NUMERIC run that starts above 1,
    which no argument list ever does. A run starting above 1 is numbering
    continued from earlier text (apparatus at any length); a run starting AT 1
    is apparatus only when it is long (6+ — a whole-document scan), because a
    genuine numbered list also starts at 1 and stays short. Lettered markers
    never qualify. Apparatus markers are subtracted; any real enumeration that
    coexists with them (a lettered list inside numbered sections) stays
    policed. A run-length gate alone was tried first and passed a whole-source
    check while failing the per-chapter slices the pipeline actually judges —
    its retry then "preserved" the section numbers into the translation.
    """
    # ONE scan, in document order, for both the total and the run detection.
    # (A paragraph-head scan under-counted: a section number that follows an
    # inline Arabic line sits mid-paragraph, so the run looked broken and the
    # apparatus went half-detected.)
    markers = [(m.group(1) or m.group(2)) for m in _ENUM_MARKER_RE.finditer(base_text or "")]
    base_n = len(markers)
    if base_n < minimum:
        return []
    # Maximal consecutive ascending numeric runs, in document order.
    runs: list[tuple[int, int]] = []  # (start_number, length)
    start = prev = None
    length = 0
    for digits in markers:
        if digits and digits.isdigit():
            number = int(digits)
            if prev is not None and number == prev + 1 and length:
                length += 1
            else:
                if length:
                    runs.append((start, length))
                start, length = number, 1
            prev = number
        else:
            if length:
                runs.append((start, length))
            start, length = None, 0
            prev = None
    if length:
        runs.append((start, length))
    apparatus = sum(n for s, n in runs if s > 1 or n >= 6)
    effective = base_n - apparatus
    if effective < minimum:
        return []
    cand_n = len(_ENUM_MARKER_RE.findall(candidate or ""))
    if cand_n < effective:
        return [f"source enumeration lost ({cand_n} of {effective} items survive as items)"]
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
