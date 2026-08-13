"""The prompt half of the narrative contract — what a model is ASKED to produce.

Split out of `_narrative.py` on 2026-08-11 (DR-005). That module is the GUARDS:
pure functions that read a rewrite and report what is wrong with it. This one is
the instructions that make a model produce prose those guards will accept.

They are two halves of one contract and must stay worded together — a rule stated
to the model but not policed is a suggestion, and a rule policed but not stated
just reverts every window. So both halves read the SAME predicates
(`addresses_reader_for`, `narrative_person_for`) rather than each deciding for
itself which books a rule applies to.
"""

from __future__ import annotations

from _rules import DEFAULT_NARRATIVE_FRAME, NARRATIVE_FRAMES, addresses_reader_for

#: REQ-BA-125 and REQ-BA-126, worded once and appended to whichever frame does not
#: address a reader. They used to live inside the third-person branch below, which
#: is why a first-person lecture never received them: the blocks are about whether
#: the prose turns to an audience, and that is not the same question as who narrates.
_NO_AUDIENCE_DIRECTIVE = """
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

#: Appended for a book made from recordings. The division scheme of a lecture
#: series is its sessions, and "in the last session I talked about" locates the
#: prose in a delivery schedule the edition does not print — the same defect as
#: "the fourth gate of the first canopy", in the vocabulary a speaker uses.
#: Deliberately prompt-only: `navigation_findings` is DIFFERENTIAL (it stops a
#: pass ADDING apparatus, it does not drive removal), and teaching it these words
#: would mean threading `source_medium` through every gate signature to keep the
#: published third-person books from matching on an ordinary sentence about a week.
_NO_SESSION_LOCATOR_DIRECTIVE = """
This book was spoken as a series of sessions, and the edition does not print them.
Drop every locator that points at the delivery schedule, and keep what it teaches:
  "In the last session I talked about the word X"  -> "The word X carries..."
  "we'll study this over the next few sessions"    -> drop entirely
  "We have gathered today for this final session"  -> drop entirely
  "as I mentioned last week"                       -> drop the locator, keep the point
A recap that TEACHES is not a locator: keep the substance, lose the timestamp.
"""


def frame_prompt_directive(frame: str, narrator_subject: str = "") -> str:
    """The instruction block that makes a model PRODUCE what the guards enforce.

    Gates alone would simply revert every chapter: a model told to write an
    intimate first-person companion and then failed for doing so burns a pass and
    ships the base. The prompt and the gate must state the same rule, so this is
    the single place that rule is worded for both.

    The no-audience blocks are appended by ``addresses_reader_for``, the SAME
    predicate ``lecture_voice_findings`` and ``navigation_findings`` consult, so a
    frame can never be asked for prose its gates would then revert.
    """
    spec = NARRATIVE_FRAMES.get(frame) or NARRATIVE_FRAMES[DEFAULT_NARRATIVE_FRAME]
    tail = "" if addresses_reader_for(frame) else _NO_AUDIENCE_DIRECTIVE
    if spec["person"] == "third":
        who = (
            "an anonymous transmitter reporting what passed between other people"
            if frame == "transmitted_report"
            else "a narrator outside the story who never appears in it"
        )
        return (
            f"""
NARRATIVE FRAME (binding — this is the source's structure, not a style preference)
Narrate in the THIRD PERSON. The narrator is {who}, and is NOT a character.
Write "The Master said", "The boy said", "he asked" — never "my Master", "he told
me", "I said to him", or "the boy came to me". First person appears ONLY inside a
character's own quoted speech, where it belongs.
Do NOT add, remove, or re-point a speech tag. If the source attributes a passage
to a speaker, keep that attribution; if the source leaves a paragraph untagged,
leave it untagged. An invented tag hands one person's words to another.
"""
            + tail
        )
    named = f" You are {narrator_subject}." if narrator_subject else ""
    # The "I" is the speaker's and it stays. What goes is the room: an expository
    # first-person frame keeps every "I said" and loses every "you will notice".
    kept = (
        ""
        if addresses_reader_for(frame)
        else "\nKeep your own \"I\" — it is the author's and the source's. What must go is the\n"
        "AUDIENCE, not the narrator: never address a reader, never direct a room.\n"
    )
    return (
        f"""
NARRATIVE FRAME (binding — this is the source's structure, not a style preference)
Narrate in the FIRST PERSON throughout, consistently, from the opening word.{named}
Never lapse into reporting yourself from outside{f' as "{narrator_subject} said"' if narrator_subject else ""}.
Do NOT add, remove, or re-point a speech tag. If the source attributes a passage
to a speaker, keep that attribution; if the source leaves a paragraph untagged,
leave it untagged. An invented tag hands one person's words to another.{kept}"""
        + tail
        + (_NO_SESSION_LOCATOR_DIRECTIVE if tail else "")
    )


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
