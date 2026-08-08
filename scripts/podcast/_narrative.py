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
  * ``enumeration_findings`` — dissolving the source's lettered items into
    running prose loses no words and destroys the argument's skeleton, which is
    why every word-level fidelity check passes it.

``lecture_voice_findings`` answers a later one, on `al-anwaar-al-lateefah`
(2026-08-03): a frame conversion that changes only the PERSON leaves a lecture
still a lecture. Every "I" became "the book" and every "Hold that frame", "Do not
pass over that phrase lightly" and "you should expect" stayed exactly where the
speaker put them — so the page passed every guard here and read nothing like the
edition printed beside it.

VOWELLING IS NO LONGER A DEFECT (Asif, 2026-07-29). Two checks lived here that
judged supplied tashkeel — ``supplied_diacritics_findings``, which compared a
rewrite against its own base, and ``ocr_vowelling_findings``, which held a
non-Quranic run to the scan's own marking using ``_mushaf.is_quranic`` to excuse
canonical verses. Both are deleted, because the rule they enforced is reversed:
Arabic in these editions ALWAYS carries its vowel marks now. Asif does not read
Arabic, so a bare run is not "unverified" to him, it is unreadable, and a guard
whose whole effect was to keep marks off the page made every edition worse for
the person it is printed for. ``vowel_book.py`` supplies the marks at compose
time and ``_vowelling.rejection_reason`` bounds each one to marks only.

WHAT STILL GUARDS THE ARABIC here is ``arabic_retention_findings``, and it is the
one that mattered all along: it compares consonantal SKELETONS, so a rewrite may
mark a run however it likes and still may not change a letter, drop a run, or
replace script with a transliteration. A wrong vowel is a reading choice; a
changed letter is a different word.

Detection philosophy: HIGH PRECISION over recall. Each check fires only on
evidence it can point at, because a false revert costs a chapter while a missed
finding is still caught downstream by the `book-challenger` agent's semantic
pass. Where a check inspects a window rather than whole text, that mirrors the
existing `narrative_opening_findings` convention in `_book_voice.py`.
"""

from __future__ import annotations

import re
import unicodedata

from _arabic_coverage import ARABIC_BODY
from _rules import (
    DEFAULT_NARRATIVE_FRAME,
    NARRATIVE_FRAMES,
    R_ARABIC_TASHKEEL,
    narrative_person_for,
)

# REQ-BA-125 (R-NO-LECTURE-VOICE) and REQ-BA-126 (R-NO-NAVIGATION-APPARATUS) are
# implemented below. Their IDS are not declared here: every `R_*` constant in
# this repo carries rule DATA that code imports — a pattern list, a threshold, a
# category set — and a bare id string that nothing cites is decoration. The ids
# themselves live once, in `docs/standards/book-articulation.md`, which is what
# `book-challenger` cites findings by.

# Speech tags live at the head of a paragraph. Every real defect found on the
# live book landed inside this window, and confining the scan to it is what keeps
# the check from reverting legitimate first-person prose INSIDE quoted speech —
# which is where first person belongs even under a third-person frame.
_ATTRIBUTION_WINDOW = 140

_ARABIC_RUN_RE = re.compile(f"[{ARABIC_BODY}]{{2,}}")  # this omitted extended-A
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
#
# The whitespace between the closing quote and the tag is HORIZONTAL ONLY. With a
# plain `\s*` the match crossed the blank line between paragraphs, so an ordinary
# head attribution following a closed quotation — `...meaning."\n\nThe boy said:` —
# counted as interior, which is precisely the case the comment above says must not
# count. On a nine-chapter book that was 284 of 320 matches: the real signal was
# swamped, and any pass that legitimately ADDED quotation marks tripped the gate
# purely by closing quotes it had opened. An interior tag interrupts a quotation
# on its own line; a newline between them means the quotation already ended.
#
# THE QUOTATION MUST RE-OPEN AFTER THE TAG (2026-07-31). Everything above states
# that the defect is a tag INTERRUPTING one utterance, and every example given is
# `," he said, "` — but the pattern only ever matched up to the verb, so it could
# not tell an interruption from a TRAILING tag. `"Thirty-three years," Hatim
# replied.` is ordinary English with the attribution exactly where the source put
# it, and it scored the same as `"I have gained," he said, "eight benefits."`,
# where the words after the tag really can change owner.
#
# That is not a theoretical difference. A source in the head-tag style — `Hatim
# replied: "Thirty-three years!"`, which is how this repo's Urdu-derived English
# translations are written — has a base count of ZERO, so the first natural
# de-calque of a line of dialogue trips a P0 and reverts the window. On
# `ayyuhal-walad`, a book of nothing but reported dialogue, that killed chapter 1,
# then killed chapter 3 twice and aborted the whole compose 27 minutes in
# (2026-07-31). The articulation route makes this the COMMON case rather than a
# corner: turning `X replied: "Y"` into `"Y," X replied.` is exactly what REQ-BA-020
# asks for.
#
# The separator may be a comma, colon, semicolon or dash — never a full stop. `X
# said. "..."` is two complete sentences with a terminated, unambiguous
# attribution; `X said, "..."` is one utterance with a tag cut into it, which is
# the shape that re-points speech. Narrowing here is deliberate and safe: this is
# a SEED for the challenger's BK-N2, whose spec already says an empty determin-
# istic result means "nothing cheap to find", not a pass — and the module's stated
# philosophy is high precision over recall, because a false revert costs a chapter
# while a missed finding is still caught by the semantic pass reading the source.
_INTERIOR_TAG_RE = re.compile(
    r"[\"”][^\S\n]*,?[^\S\n]*(?:[A-Z][\w'\-]*(?:[^\S\n]+[A-Z][\w'\-]*)?|he|she|they)[^\S\n]+"
    r"(?:said|replied|answered|asked|told)\b"
    r"[^\S\n]*[,:;—–-]?[^\S\n]*[\"“]"
)

# Source-style enumeration markers at the head of a paragraph: "(a)", "(1)", "1.".
_ENUM_MARKER_RE = re.compile(r"(?m)^\s*(?:\(([a-z]|[0-9]{1,2})\)|([0-9]{1,2})\.)\s+\S")

# ─── LECTURE VOICE ───────────────────────────────────────────────────────────
# A speaker addresses an audience; a book addresses nobody. Under a third-person
# frame the narration must not turn and instruct the reader.
#
# This is the SECOND half of a frame conversion, and until 2026-08-03 only the
# first half existed. `al-anwaar-al-lateefah` is transcribed from lectures, so
# converting it to a transmitted report removed every "I" and left the lecturer
# entirely intact: "Hold that frame, and step now inside it", "Do not pass over
# that phrase lightly", "so consider the grammar", "you should expect nothing
# else from these pages". Grammatical person passed on every paragraph, and Asif
# read chapter 1 and said it did "not at all read like" the edition beside it.
# The tells are not first person, so no person check can ever see them.
#
# Two families, both scoped to NARRATION — a character telling another character
# "consider what you have said" is dialogue, and dialogue is untouched:
#   1. second-person address of the reader
#   2. a closed list of stage-direction imperatives that only a speaker uses
_READER_ADDRESS_RE = re.compile(r"\b(?:you|your|yours|yourself|yourselves)\b", re.I)
_STAGE_DIRECTION_RE = re.compile(
    r"(?:(?m:^)|(?<=[.!?;:—]\s)|(?<=[.!?;:—]\s\s))\s*(?:And |But |Now |So |Then |Again )?"
    r"(?:Consider|Notice|Note|Observe|Recall|Remember|Imagine|Picture|Hold|Look|Watch|"
    r"Mark|Listen|Pay attention|Do not pass|Do not miss|Do not overlook|Step now|"
    r"Turn now|Set (?:that|this) beside|Think of|See how|Keep (?:that|this) in mind)\b"
)
# Blockquote lines, quoted spans and Arabic runs are not narration. The span match
# is deliberately forgiving — a quotation running over several paragraphs opens on
# each and closes once, so some quoted text survives into the "narration" slice.
# That costs nothing here: this check is DIFFERENTIAL, and both sides are measured
# by the same imperfect rule, so what it compares stays honest.
_BLOCKQUOTE_LINE_RE = re.compile(r"(?m)^[ \t]*>.*$")
_QUOTED_SPAN_RE = re.compile(r'[“"][^”"]{0,4000}[”"]')


# ─── NAVIGATION APPARATUS ────────────────────────────────────────────────────
# A lecture walks through a text and says where it is: "we now turn to the second
# section of the first chapter of the first canopy". A book has a heading.
#
# This is the same defect family as the lecture voice and was found the same way
# — Asif read the page (2026-08-03) and asked why chapter 1 opened on "useless
# information about Suradiq". It is not useless because it is wrong; it is
# useless because the EDITION does not use the source's division scheme. The
# reader is given five canopies of five gates of five chapters, 125 sections, and
# then a book with eight numbered chapters and no canopies in it. The scheme
# names nothing they can navigate by, and `al-anwaar-al-lateefah` explains what a
# suradiq is TWICE, four chapters apart, because the lecture did.
#
# Deliberately NOT a strip. Several of these sentences carry teaching alongside
# the locator — "The ascent was named in the last gate; now a second gate opens,
# and behind it lies something quieter" — so deleting the sentence deletes the
# thought. The rule is a RECAST, driven by the prompt, guarded differentially.
_DIVISION_WORD = (
    r"(?:suradiq|suradiqs|sardaq|bab|babs|abwab|fasl|fasls|fusul|"
    r"canopy|canopies|gate|gates|pavilion)"
)
#: Two shapes, and both are apparatus: LOCATING the prose in the scheme ("the
#: fourth chapter of the first gate"), and RECITING the scheme ("five canopies in
#: all"). The second is what opens chapter 1, so a locator-only pattern misses
#: precisely the passage that prompted the rule.
_NAVIGATION_RE = re.compile(
    r"[^.!?\n]*\b(?:"
    r"first|second|third|fourth|fifth|last|next|this"
    # `one` is excluded deliberately: it is an English PRONOUN far more often than
    # a count, and as a count no division scheme is ever "one canopy". Including
    # it matched "the perfection ... the one that the gate of the First Intellect
    # alone opens onto" — a metaphorical gate, in a chapter with no apparatus in
    # it at all.
    r"|two|three|four|five|six|seven|eight|nine|ten|[0-9]{1,3}"
    rf")\s+(?:\w+\s+){{0,2}}{_DIVISION_WORD}\b[^.!?\n]*[.!?]",
    re.I,
)


def navigation_findings(base_text: str, candidate: str, *, frame: str) -> list[str]:
    """Flag a rewrite that ADDS navigation apparatus to a third-person book.

    Differential for the same reason ``lecture_voice_findings`` is: a lecture
    transcript is full of these, and an absolute check would revert every window
    before the pass could remove one.
    """
    if narrative_person_for(frame) != "third":
        return []
    base_n = len(_NAVIGATION_RE.findall(_narration_only(base_text)))
    cand_n = len(_NAVIGATION_RE.findall(_narration_only(candidate)))
    if cand_n > base_n:
        return [f"navigation apparatus added — the source's division scheme ({cand_n} vs {base_n} in source)"]
    return []


def navigation_count(text: str) -> int:
    """How many sentences locate the prose inside the source's division scheme."""
    return len(_NAVIGATION_RE.findall(_narration_only(text)))


def _narration_only(text: str) -> str:
    """The prose the BOOK speaks — quotations and Arabic removed."""
    stripped = _BLOCKQUOTE_LINE_RE.sub(" ", text or "")
    stripped = _QUOTED_SPAN_RE.sub(" ", stripped)
    return _ARABIC_RUN_RE.sub(" ", stripped)


def lecture_voice_counts(text: str) -> tuple[int, int]:
    """``(reader-address, stage-direction)`` counts in ``text``'s narration."""
    narration = _narration_only(text)
    return (
        len(_READER_ADDRESS_RE.findall(narration)),
        len(_STAGE_DIRECTION_RE.findall(narration)),
    )


def lecture_voice_findings(base_text: str, candidate: str, *, frame: str) -> list[str]:
    """Flag a rewrite that ADDS lecture voice to a third-person book.

    DIFFERENTIAL, like ``narrative_opening_findings`` and for the same reason: a
    lecture-derived source is saturated with these, so an absolute check would
    revert every window of `al-anwaar` before the pass could improve one. What
    the pass must never do is put MORE of it on the page than it found. Removal
    is driven by ``frame_prompt_directive``, which states this same rule to the
    model — the module's standing contract that a gate and its prompt are worded
    once, together.

    Silent under a first-person frame: *Ayyuhal Walad* is a letter to a disciple,
    where addressing the reader is not a defect but the form itself.
    """
    if narrative_person_for(frame) != "third":
        return []
    base_address, base_stage = lecture_voice_counts(base_text)
    cand_address, cand_stage = lecture_voice_counts(candidate)
    findings: list[str] = []
    if cand_address > base_address:
        findings.append(
            f"lecture voice added — narration addresses the reader "
            f"({cand_address} vs {base_address} in source) under {frame} frame"
        )
    if cand_stage > base_stage:
        findings.append(
            f"lecture voice added — stage directions to an audience "
            f"({cand_stage} vs {base_stage} in source) under {frame} frame"
        )
    return findings


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
    is apparatus when it is long (6+ — a whole-document scan) OR when its
    markers are PARENTHESIZED numeric and short — kitab-al-riyad's critical
    edition carries dozens of independent footnotes ("(1) This imam lived in
    Salamiyya...", "(2) Philosophical Letters — Paul Kraus — p. 291", "(3) It
    fell in copy (B)"), each restarting at (1), each unrelated to its
    neighbours, several short runs of which summed past `minimum` and read as
    one lost list. Every genuine numbered ARGUMENT list found in this
    pipeline's source material instead uses BARE "1." dot-style numbering
    (the 9-item al-Mahsul/al-Islah dispute list, also in kitab-al-riyad): a
    short parenthesized run is apparatus, a short bare-dot run is real.
    Lettered markers never qualify, at any run length. Apparatus markers are
    subtracted; any real enumeration coexisting with them stays policed. A
    run-length gate alone was tried first and passed a whole-source check
    while failing the per-chapter slices the pipeline actually judges — its
    retry then "preserved" the section numbers into the translation.
    """
    # ONE scan, in document order, for both the total and the run detection.
    # (A paragraph-head scan under-counted: a section number that follows an
    # inline Arabic line sits mid-paragraph, so the run looked broken and the
    # apparatus went half-detected.) Marker STYLE travels with each one —
    # parenthesized vs. bare-dot vs. lettered — since the run classification
    # below depends on it.
    markers: list[tuple[str, str]] = []  # (digits, style) — style: "paren" | "dot" | "letter"
    for m in _ENUM_MARKER_RE.finditer(base_text or ""):
        if m.group(2):
            markers.append((m.group(2), "dot"))
        elif m.group(1).isdigit():
            markers.append((m.group(1), "paren"))
        else:
            markers.append((m.group(1), "letter"))
    base_n = len(markers)
    if base_n < minimum:
        return []
    # Maximal consecutive ascending numeric runs, in document order. Style is
    # the FIRST marker's — a run does not change style mid-sequence in
    # practice, and classification only needs one answer per run.
    runs: list[tuple[int, int, str]] = []  # (start_number, length, style)
    start = prev = None
    length = 0
    run_style = ""
    for digits, style in markers:
        if digits and digits.isdigit():
            number = int(digits)
            if prev is not None and number == prev + 1 and length:
                length += 1
            else:
                if length:
                    runs.append((start, length, run_style))
                start, length, run_style = number, 1, style
            prev = number
        else:
            if length:
                runs.append((start, length, run_style))
            start, length, run_style = None, 0, ""
            prev = None
    if length:
        runs.append((start, length, run_style))
    apparatus = sum(n for s, n, st in runs if s > 1 or n >= 6 or (st == "paren" and s == 1))
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

NO LECTURE VOICE (binding — a book addresses nobody)
This source may be transcribed from a spoken lecture. The narration must not turn
and address the reader, or direct an audience. RECAST every such move into
exposition — never delete the thought it carries:
  "Hold that frame, and step now inside it"     -> "Within that frame stands..."
  "Do not pass over that phrase lightly"        -> "The phrase carries weight."
  "so consider the grammar, because it sharpens" -> "The grammar sharpens..."
  "you should expect nothing else from these pages" -> "The book does no more."
  "Think of an enclosing canopy"                -> "The image is of a canopy."
Forbidden in narration: "you", "your", and imperatives aimed at the reader
(consider, notice, note, observe, recall, remember, imagine, picture, hold, look,
mark, listen). Also drop commentary about the discourse itself — "this is the
heart of it", "before we go on", "as we shall see" — and state the matter instead.
Second person and imperatives are UNTOUCHED inside a character's quoted speech,
inside a Quran verse, hadith, or prayer, and inside any block quotation: there
they are one person speaking to another, which every frame keeps.

NO NAVIGATION APPARATUS (binding — this edition has its own chapters)
Do not locate the prose inside the SOURCE's division scheme. This edition prints
numbered chapters; it has no canopies, gates, babs or fasls a reader can turn to,
so a sentence announcing "we now come to the fourth chapter of the first gate of
the first canopy" points at nothing they can find. Drop the locator and keep
whatever the sentence teaches:
  "And so the next hanging in the tent opens onto the fourth chapter of the
   first gate of the first canopy — the fourth *fasl*."   -> drop entirely
  "The ascent was named in the last gate; now a second gate opens, and behind
   it lies something quieter."  -> "What follows is quieter."
Also drop the scheme itself when it is being recited rather than used — "five
canopies, each of five gates", "one hundred and twenty-five sections in all" —
and any second explanation of what a suradiq, bab or fasl IS. Naming the source's
own term once, where the source's argument turns on it, is fine.
KEEP the division word wherever the TEXT QUOTED beside it uses it: a heading the
source prints, or an Arabic line naming itself, stays exactly as it is.
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
Keep whatever vowel marks (tashkeel) a run already carries, and do not strip them.
Adding marks is not your job here — a later pass vowels the Arabic under a gate
that checks the letters are unchanged — so reproduce each run as given.

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
    findings.extend(enumeration_findings(base_text, candidate))
    findings.extend(lecture_voice_findings(base_text, candidate, frame=frame))
    findings.extend(navigation_findings(base_text, candidate, frame=frame))
    return findings
