"""_vowelling.py — the admissibility gate for supplied Arabic vowelling.

PYTHON HALF OF A MIRROR PAIR. The JavaScript half is
``plan-dashboard/scripts/lib/vowelling.mjs``, which serves the Composer's
Diacritics button; this half serves the compose-time pass
(``vowel_book.py``). Both are pinned to the SAME fixtures at
``plan-dashboard/scripts/lib/vowelling.fixtures.json`` — a change to either
implementation that is not matched in the other fails a test rather than letting
the button and the pipeline disagree about what counts as an admissible
vowelling. Same contract as the repo's three other mirror pairs.

WHAT THIS GATE IS, AND WHAT IT IS NOT (Asif, 2026-07-29). It is NOT a rule about
whether Arabic should be vowelled. That question is settled: it always should be.
Asif does not read Arabic, so a bare run is not "unverified" to him, it is
unreadable, and the earlier contract — a model proposes, a human accepts, and
only then does a mark reach the page — was reversed for exactly that reason.

What survives is narrower and load-bearing: a vowelling may differ from its
source in MARKS ONLY. ``skeleton()`` strips every combining mark and tatweel, and
a candidate is refused unless its skeleton is byte-identical to the source run's.
A model that adds marks passes. A model that "corrects" a letter, drops a word,
normalises a hamza form, or quietly substitutes the mushaf's Uthmani spelling
fails and never reaches ``book.md``. On an Arabic verb a wrong vowel is a reading
choice; a changed letter is a different word, and this book is largely reported
speech. Relaxing the policy on marks was Asif's call; letting letters move under
cover of it never was.
"""

from __future__ import annotations

import re

from _arabic_coverage import ARABIC_RE as _ARABIC_RE

# Combining marks: tashkeel, superscript alif, Quranic annotation signs. Tatweel
# is included because it stretches a letter rather than being one, and two
# otherwise-identical skeletons must not differ over it.
#
# WRITTEN AS ESCAPES, and the ranges are exact for a reason. The literal class
# this replaced spelled the second range `ٓ-ٰ` — U+0653 to U+0670 — which also
# contains U+0660-U+0669, the Arabic-Indic DIGITS, and U+066E/U+066F, the dotless
# beh and qaf, which are LETTERS. Treating those as marks meant `skeleton()`
# deleted them, so a vowelling that dropped every footnote and verse number was
# admitted by `rejection_reason` as "marks only": on a real OCR line,
# `تأليف ١ سيدنا جعفر بن منصور ٢ اليمن٣`, mark_count returned 3 for a completely
# bare run and a candidate with all three digits gone passed the gate. The
# inflated count also skewed `mark_density`, so a digit-bearing bare run could
# read as already vowelled and be skipped. Both directions are closed here.
# U+06D6-U+06ED (the Qur'anic annotation signs) were in the JS half of this pair
# and not in this one; unified rather than left to diverge silently.
# The class BODY is exported so a second reader interpolates it rather than retyping it.
# `_book_defects` needs the same set to match a honorific however it happens to be
# vowelled \u2014 the marks-only gate and the honorific matcher have to agree about what a
# mark IS, or one of them is wrong about a phrase the other accepted.
MARKS_BODY = "\u064b-\u065f\u0670\u06d6-\u06ed\u0640"
MARKS_RE = re.compile(f"[{MARKS_BODY}]")

# Arabic script, for asking whether a string contains Arabic at all.
ARABIC_RE = _ARABIC_RE  # the one definition — see _arabic_coverage

# Marks per Arabic letter above which a run counts as already vowelled. The bare
# source averages ~0.02; a fully vowelled text runs an order of magnitude higher.
# Deliberately generous: a run the scanner left with two disambiguating marks is
# still bare for this purpose. Used only to CHOOSE runs, never to judge one.
VOWELLED_DENSITY = 0.15

# Shortest run worth vowelling, in skeleton characters excluding whitespace. Below
# this a "run" is a stray word inside English prose, where the surrounding sense a
# vocalisation depends on is not in the run at all.
MIN_RUN_CHARS = 8


def skeleton(text: str) -> str:
    """The consonantal skeleton: every mark and tatweel gone, whitespace collapsed.

    Two strings with the same skeleton differ ONLY in vocalisation, which is the
    entire permitted delta.
    """
    return re.sub(r"\s+", " ", MARKS_RE.sub("", text or "")).strip()


def mark_count(text: str) -> int:
    """How many combining marks a run carries."""
    return len(MARKS_RE.findall(text or ""))


def mark_density(text: str) -> float:
    """Marks per Arabic letter. Zero for a run with no Arabic letters at all."""
    letters = [c for c in (text or "") if ARABIC_RE.match(c) and not MARKS_RE.match(c)]
    return (mark_count(text) / len(letters)) if letters else 0.0


def rejection_reason(source: str, candidate: str) -> str | None:
    """Why this vowelling is inadmissible, or ``None`` when it may be applied.

    The reason is returned rather than swallowed: a passage the model keeps
    failing on is a passage a human should look at directly.
    """
    if not candidate or not candidate.strip():
        return "empty"
    if not ARABIC_RE.search(candidate):
        return "no Arabic script in the candidate"
    a, b = skeleton(source), skeleton(candidate)
    if a != b:
        # Report the first divergence — "differs at character 12" lets a reader
        # see instantly whether a word was rewritten or a clause dropped.
        i = 0
        while i < len(a) and i < len(b) and a[i] == b[i]:
            i += 1
        return (
            f"letters changed, not just marks (first difference at character {i + 1}: "
            f'source "{a[i : i + 12]}" vs proposal "{b[i : i + 12]}")'
        )
    if mark_count(candidate) <= mark_count(source):
        return "adds no vowel marks"
    return None


# Letters the model rewrites into "correct" Arabic while vowelling, and the form
# the books actually print. Each entry is one LETTER in two shapes, never two
# letters: the fold is what makes a mark transferable onto the source's own
# character, so a pair that is a genuine spelling difference must not be here.
#
# EVERY PAIR IS EVIDENCE, counted across the seven composed books' recorded
# refusals: alif carrying a hamza it does not have in the source (33), the
# Perso-Arabic yeh, kaf, heh and teh marbuta the Urdu-set passages use (28), and
# the yeh whose hamza seat the model drops (1). Four refusals in that corpus are
# NOT in any family — a lam read as an alif, a noon as an alif — and they stay
# refused, which is the whole reason this is a table and not a rule about hamzas.
#
# `ه` and `ة` are deliberately NOT one family. In Urdu orthography they overlap,
# and one refusal in the corpus is exactly that; in Arabic they are a real
# spelling distinction, and admitting the swap would let a mark transfer change
# what a word means. That one run stays bare and is reported.
#
# RELATED BUT NOT THE SAME as `_book_romanization._PERSO_ARABIC_FOLD`, which
# folds letters in order to MATCH two spellings of one saying. This decides what
# a mark may be carried across, which is a stricter question, so the two tables
# are written separately and neither imports the other.
LETTER_FAMILY = {
    "أ": "ا",  # alef with hamza above -> alef
    "إ": "ا",  # alef with hamza below -> alef
    "آ": "ا",  # alef with madda      -> alef
    "ٱ": "ا",  # alef wasla           -> alef
    "ؤ": "و",  # waw with hamza above -> waw
    "ی": "ي",  # farsi yeh            -> yeh
    "ى": "ي",  # alef maksura         -> yeh
    "ئ": "ي",  # yeh with hamza above -> yeh
    "ک": "ك",  # keheh                -> kaf
    "ہ": "ه",  # heh goal             -> heh
    "ھ": "ه",  # heh doachashmee      -> heh
    "ۃ": "ة",  # teh marbuta goal     -> teh marbuta
}


def _same_letter(a: str, b: str) -> bool:
    """One letter in two shapes — the difference a mark may be carried across."""
    return a == b or LETTER_FAMILY.get(a, a) == LETTER_FAMILY.get(b, b)


def transfer_marks(source: str, candidate: str) -> str | None:
    """``source``'s letters wearing ``candidate``'s marks, or None if they disagree.

    THE CURE FOR THE ONLY REFUSAL THAT EVER HAPPENS (Asif, 2026-08-11). Across the
    seven composed books, 71 of 75 recorded refusals are a model normalising ONE
    letter into another form of the same letter while vowelling correctly around
    it — `ا` into `إ`, the Urdu `ی` into `ي` — and `rejection_reason` then discards
    the whole answer, marks and all. The salvage pass in `vowel_book` re-asks the
    same model, which normalises the same letter again, which is why `recovered`
    stands at 0 in every book. Asking differently was never going to fix it.

    So the marks are taken and the letters are not. Walking both sides letter by
    letter, this emits the SOURCE's character with the CANDIDATE's marks attached,
    which makes the result's skeleton byte-identical to the source BY
    CONSTRUCTION rather than by a check that could be wrong. The guarantee the
    gate exists to give is therefore strengthened here, not relaxed: after this,
    no letter a model chose can reach `book.md` even by accident.

    None when the two cannot be aligned: a different letter count (a dropped
    clause, an added word), or a difference outside `LETTER_FAMILY` (a lam read as
    an alif). Those still fail the gate and are still reported, because a mark
    placed on a word the model misread is a wrong reading printed confidently.

    The source's own whitespace is emitted verbatim, so this doubles as the reflow
    `reflow_to_source_whitespace` performs for the candidates that do align.
    """
    if not source or not candidate:
        return None
    src = [c for c in source if not MARKS_RE.match(c) and not c.isspace()]
    cand: list[tuple[str, str]] = []  # (letter, its trailing marks)
    for ch in candidate:
        if ch.isspace():
            continue
        if MARKS_RE.match(ch):
            if cand:
                cand[-1] = (cand[-1][0], cand[-1][1] + ch)
            continue
        cand.append((ch, ""))
    if len(src) != len(cand) or not src:
        return None
    if any(not _same_letter(s, c) for s, (c, _) in zip(src, cand)):
        return None
    out: list[str] = []
    i = 0
    for ch in source:
        if MARKS_RE.match(ch):
            continue  # the candidate re-supplies every mark
        if ch.isspace():
            out.append(ch)
            continue
        out.append(ch + cand[i][1])
        i += 1
    return "".join(out)


def reflow_to_source_whitespace(source: str, candidate: str) -> str:
    """``candidate``'s letters and marks, carrying ``source``'s exact whitespace.

    A model asked to vowel one passage hands back one line however many lines the
    passage occupied — ``vowel_book.SYSTEM`` even asks for that. ``skeleton()``
    normalises whitespace before comparing, deliberately, so that collapse is
    INVISIBLE to the gate and a vowelling that silently joined the lines of an OCR
    page would be admitted as "marks only". Line structure is not cosmetic here:
    ``produce_bilingual`` slices the Arabic source by line range, and 886 of the
    1,395 distinct runs in one book's OCR span more than one line.

    The repair is exact rather than heuristic. Once the skeletons agree the
    non-whitespace characters correspond one for one, so walking both — taking
    whitespace from the source and letters-with-their-marks from the candidate —
    restores the original shape without moving a single mark. Marks already in the
    source are skipped, since the candidate re-supplies them.

    ORPHAN MARKS are why the candidate scan skips marks as well as whitespace. A
    scan can leave a combining mark with no letter under it — one run in the
    Master-and-Disciple OCR literally begins with a bare sukun — and the first
    version consumed that orphan AS a letter. Every later letter was then off by
    one, the walk ran off the end of the candidate, and reflow bailed by returning
    the model's collapsed single line. `rejection_reason` cannot catch that, since
    `skeleton` had already normalised the whitespace away, so the collapse was
    ADMITTED and the file lost lines. Orphans are carried into the output rather
    than dropped, so no mark is lost repairing the shape.

    Returns ``candidate`` untouched when the two do not align, leaving
    ``rejection_reason`` to refuse it and report why.
    """
    if skeleton(source) != skeleton(candidate):
        return candidate
    out: list[str] = []
    i = 0
    for ch in source:
        if MARKS_RE.match(ch):
            continue
        if ch.isspace():
            out.append(ch)
            continue
        # Advance to the candidate's next LETTER, keeping any orphan marks.
        while i < len(candidate) and (candidate[i].isspace() or MARKS_RE.match(candidate[i])):
            if not candidate[i].isspace():
                out.append(candidate[i])
            i += 1
        if i >= len(candidate):
            return candidate
        out.append(candidate[i])
        i += 1
        while i < len(candidate) and MARKS_RE.match(candidate[i]):
            out.append(candidate[i])
            i += 1
    while i < len(candidate):
        if candidate[i].isspace():
            i += 1
        elif MARKS_RE.match(candidate[i]):
            out.append(candidate[i])
            i += 1
        else:
            return candidate  # real letters left over — the two do not align
    return "".join(out)


def reflow_words_to_source_whitespace(source: str, candidate: str) -> str:
    """``candidate``'s words laid back onto ``source``'s whitespace, word for word.

    The companion to `reflow_to_source_whitespace`, for the ONE case that function
    cannot serve: a Qur'anic run replaced by the canonical mushaf text. That
    substitution changes LETTERS — the mushaf is Uthmani — so the skeletons
    legitimately differ and the character-level walk correctly refuses to align
    them. But `mushaf_vocalisation` joins the verse's words with single spaces, so
    a verse the book prints across two lines came back as one and the file lost a
    line. Aligning by WORD works precisely because the mushaf lookup is itself
    word-aligned: it only returns a vocalisation when the word counts match.

    Falls back to ``candidate`` unchanged if the word counts disagree, so a
    mismatch shows up as the caller's own structural check rather than as text
    silently reshaped to fit.
    """
    src_words = (source or "").split()
    cand_words = (candidate or "").split()
    if not src_words or len(src_words) != len(cand_words):
        return candidate
    # Walk the source, emitting its whitespace verbatim and swapping each word.
    out: list[str] = []
    idx = 0
    for piece in re.split(r"(\s+)", source):
        if not piece:
            continue
        if piece.isspace():
            out.append(piece)
        else:
            out.append(cand_words[idx])
            idx += 1
    return "".join(out)


def is_vowelling_candidate(text: str) -> bool:
    """A run worth vowelling: Arabic, long enough to be a passage, still bare."""
    t = (text or "").strip()
    if not ARABIC_RE.search(t):
        return False
    if len(skeleton(t).replace(" ", "")) < MIN_RUN_CHARS:
        return False
    return mark_density(t) < VOWELLED_DENSITY


def is_arabic_passage(text: str) -> bool:
    """Predominantly Arabic, not merely containing some.

    An English paragraph quoting three Arabic words is not a passage to vowel:
    sending it would ask the model to hand back English it must not touch, and the
    skeleton check would then refuse whatever came back. Same ratio the Composer's
    button and the vowelling route apply on their own selections.
    """
    latin = len(re.findall(r"[A-Za-z]", text or ""))
    arabic = len(ARABIC_RE.findall(text or ""))
    return not (latin > 2 or arabic < latin * 4)
