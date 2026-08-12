"""_book_romanization.py — put an Arabic saying printed in English letters back into Arabic.

Asif's rule of 2026-08-02 is that `book.md` carries zero English transliteration of Arabic
"terms, words, paragraphs, sentences, etc.". `_book_substitution` implements it for
glossary TERMS, gated on a human having classed the term `teach`. A whole SAYING matches
no glossary term, so nothing reached fourteen of them across two shipped editions —
`(Ana madinatul-ilm wa 'Ali babuha; Fa-man aradal-ilm fal-yatil-bab)` among them.

THE LADDER (Asif, 2026-08-09). Find the saying; failing that, render it.

  1. THE LIBRARY   the book's own scanned Arabic, the canonical mushaf, and the hadith
                   and topic collections in `content/knowledge-base/mirror.db`. Free,
                   and it returns the source's OWN vowelled wording rather than anyone's
                   reconstruction of it.
  2. THE OPEN WEB  `_scholar_bridge.research` — Gemini with Google-Search grounding,
                   the one paid path this repo already trusts for a passage the library
                   cannot ground. It refuses when the search stood on nothing. It is a
                   CROSS-CHECK, never an authority: an answer counts only when its Arabic
                   agrees with what the book's own transliteration spells. Measured on
                   2026-08-09, the grounding cited facebook.com and reddit.com beside two
                   real Islamic sites, so its citation is worth having and its wording is
                   not worth trusting on its own.
  3. RECONSTRUCTION
                   render the transliteration into Classical Arabic with diacritics.

WHY RUNG 3 IS NOT "A MODEL RECALLING SCRIPTURE", which is the thing this repo forbids.
The romanization already fixes the consonants: `Ana madinatul-ilm` can only be
أنا مدينة العلم. What the model supplies is the letters that transliteration implies and
the vowel marks over them — the same job `vowel_book` does over a bare run, in the same
direction. It is not asked what the saying says; it is told, in Latin letters.

The distinction is kept HONEST rather than assumed: every resolution records which rung
answered it, and a reconstruction is never reported as a citation. Rung 1 and rung 2 are
tried in full before rung 3 is reached, and the rendering rung 3 would return is computed
FIRST only because it is what rung 1 searches the library with — a skeleton to match, not
an answer to prefer.

Nothing here writes to a book. `compose_fix.py` applies what this resolves, through the
Composer's own save path.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _arabic_coverage import ARABIC_BODY, normalize_arabic
from _paths import REPO_ROOT

#: Where the cross-book library lives. Absent on a fresh clone that has not pulled it;
#: rung 1 then finds nothing and the ladder carries on, which is the conservative
#: direction — never a silently wrong answer.
MIRROR_DB = REPO_ROOT / "content" / "knowledge-base" / "mirror.db"

#: The tables holding Arabic worth matching against, and the column it lives in.
_LIBRARY_TABLES = (("fts_quran", "arabic"), ("fts_hadith", "arabic"), ("fts_topics", "arabic"))

#: How much of a rendered saying's skeleton a library run must carry to be its source.
#: Below this the two are different sayings that share an opening formula, which is
#: common — a great many begin `قال رسول الله`.
MIN_LIBRARY_OVERLAP = 0.7

#: A rendered saying shorter than this has too little to match on: two or three words
#: overlap by accident across a corpus of six thousand verses.
MIN_MATCH_WORDS = 4

_ARABIC_RUN_RE = re.compile(f"[{ARABIC_BODY}][{ARABIC_BODY}\\s،؛.:!?]*")

#: Where each resolution came from. Recorded per saying and never inferred later.
LIBRARY = "library"
RESEARCHED = "researched"
RECONSTRUCTED = "reconstructed"


@dataclass
class Resolution:
    """One romanized saying, and the Arabic that should stand in its place."""

    romanization: str
    arabic: str
    provenance: str
    sources: list[str] = field(default_factory=list)
    detail: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.arabic.strip())

    def as_record(self) -> dict:
        return {
            "romanization": self.romanization,
            "arabic": self.arabic,
            "provenance": self.provenance,
            "sources": self.sources,
            "detail": self.detail,
        }


# ── rung 3's machinery, used by rung 1 as a search key ───────────────────────

_RENDER_PROMPT = """You are transcribing, not translating and not recalling.

Below is a sentence of Arabic that a book printed in the English character set. Write it
back in the Arabic script.

RULES
- The transliteration fixes the consonants. Write the letters it spells, nothing else.
- Do NOT substitute a different wording you may recognise, even if you believe the
  printed transliteration is imperfect. Transcribe what is in front of you.
- WORD BOUNDARIES IN THE TRANSLITERATION ARE NOT RELIABLE. A trailing `-an`, `-un`,
  `-in`, or `'an` is usually a case ending (tanwin) on the word before it, not a separate
  word: `jila 'an lil-qulub` is `جِلَاءً لِلْقُلُوبِ`, never `جِلاءٌ عَنْ لِلْقُلُوبِ`.
  Read the whole phrase as Arabic and let its grammar decide where the words divide.
- Add full Classical Arabic diacritics (tashkeel) to every word.
- Output the Arabic sentence ALONE. No translation, no commentary, no quotation marks,
  no brackets, no transliteration.

TRANSLITERATION:
{run}
{context}"""


def render_from_transliteration(run: str, *, book_dir: Path, context: str = "", log=print) -> str:
    """The Arabic the transliteration spells, vowelled. `claude -p`, so no metered cost.

    Deliberately a TRANSCRIPTION prompt: the model is told the consonants and asked for
    the script and the marks. It is never asked what the saying is, which is the request
    that would invite recall.
    """
    from _authoring._core import _run_claude_p_with_retry, pure_text_call_options

    prompt = _RENDER_PROMPT.format(
        run=run.strip(),
        context=f"\nThe English rendering beside it, for disambiguation only:\n{context.strip()}" if context else "",
    )
    rc, out, err = _run_claude_p_with_retry(
        prompt,
        timeout=180,
        book_dir=book_dir,
        phase="romanization",
        step="render",
        log=log,
        **pure_text_call_options(effort="low"),
    )
    if rc != 0:
        raise RuntimeError(f"render failed rc={rc}: {(err or '')[:200]}")
    return _only_arabic(out or "")


def _arabic_runs(text: str) -> list[str]:
    return [r for r in (m.strip(" \n،؛.:") for m in _ARABIC_RUN_RE.findall(text or "")) if r]


def _only_arabic(text: str) -> str:
    """The longest Arabic run in a reply, so a stray preamble cannot reach the page.

    Correct for the RENDER call, whose reply is one sentence. Never use it on a research
    card — see `_best_matching_arabic`.
    """
    runs = _arabic_runs(text)
    return max(runs, key=len) if runs else ""


def _best_matching_arabic(text: str, rendered: str) -> str:
    """The Arabic run in a prose reply that best AGREES with what the page already spells.

    Not the longest, which is what this took first and it put the wrong saying into three
    passages on 2026-08-09: a research card explaining "I am the city of knowledge" also
    quotes neighbouring traditions, and for `inna Ali minni wa ana minhu` the longest run
    in the card was `مَا تُرِيدُونَ مِنْ عَلِيٍّ؟` — a different hadith entirely, which the
    agreement check then never saw because it was applied to the wrong candidate.
    """
    needle = _skeleton_words(rendered)
    if not needle:
        return ""
    best, best_score = "", 0.0
    for run in _arabic_runs(text):
        score = _overlap(needle, set(_skeleton_words(run)))
        if score > best_score:
            best, best_score = run, score
    return best if best_score >= MIN_LIBRARY_OVERLAP else ""


# ── rung 1: the library ──────────────────────────────────────────────────────


def _skeleton_words(arabic: str) -> list[str]:
    """Each WORD's skeleton, separately.

    `normalize_arabic` drops whitespace along with the marks — it exists to make one
    continuous join key — so normalising the whole run first and splitting after yields
    exactly one token, and every overlap score came out as nothing-or-everything. Split
    first, normalise each word.
    """
    return [s for s in (normalize_arabic(w) for w in arabic.split()) if len(s) > 1]


def _overlap(needle: list[str], haystack_words: set[str]) -> float:
    if not needle:
        return 0.0
    return sum(1 for w in needle if w in haystack_words) / len(needle)


#: How far a candidate's length may differ from the saying's before it is a DIFFERENT
#: thing — the passage that CONTAINS the saying rather than the saying. Verse 65:2 holds
#: `وَمَن يَتَّقِ ٱللَّهَ يَجْعَل لَّهُۥ مَخْرَجًا` inside forty words of surrounding law, and
#: matching on overlap alone put the whole verse where the book had quoted six words.
MIN_EXTENT_RATIO = 0.6
MAX_EXTENT_RATIO = 1.6


def same_extent(rendered: str, candidate: str) -> bool:
    """Is the candidate the SAME SPAN as the saying, not the passage around it?

    Overlap answers "does this contain the saying". It cannot answer "is this the
    saying", and on a corpus of whole verses those are very different questions.
    """
    want = len(_skeleton_words(rendered))
    got = len(_skeleton_words(candidate))
    if not want or not got:
        return False
    return MIN_EXTENT_RATIO <= got / want <= MAX_EXTENT_RATIO


def _candidates_from_book(book_dir: Path) -> list[tuple[str, str]]:
    """(where, run) for every Arabic run in the book's own scanned source."""
    out: list[tuple[str, str]] = []
    source = book_dir / "_system" / "source" / "text"
    for name in ("raw-extract.md", "raw-extract.faithful.md", "refined-english.md"):
        path = source / name
        if not path.is_file():
            continue
        for run in _ARABIC_RUN_RE.findall(path.read_text(encoding="utf-8")):
            run = run.strip()
            if len(run.split()) >= MIN_MATCH_WORDS:
                out.append((f"the book's own scan ({name})", run))
    return out


def _candidates_from_mirror() -> list[tuple[str, str]]:
    """(where, run) from the cross-book library. Empty when the mirror is absent."""
    if not MIRROR_DB.is_file():
        return []
    out: list[tuple[str, str]] = []
    try:
        conn = sqlite3.connect(f"file:{MIRROR_DB}?mode=ro", uri=True)
    except sqlite3.Error:
        return []
    try:
        for table, column in _LIBRARY_TABLES:
            try:
                rows = conn.execute(f"SELECT {column} FROM {table}").fetchall()  # noqa: S608 - fixed names
            except sqlite3.Error:
                continue
            for (value,) in rows:
                text = str(value or "").strip()
                if len(text.split()) >= MIN_MATCH_WORDS:
                    out.append((table.replace("fts_", "the ") + " collection", text))
    finally:
        conn.close()
    return out


def find_in_library(rendered: str, *, book_dir: Path) -> tuple[str, str] | None:
    """(where, the source's own wording) for a run the library already holds.

    Matched on the consonantal SKELETON, so a difference of vowelling — which is exactly
    what differs between two printings of the same saying — never hides a match. The
    library's text is returned rather than the rendering, because a source that holds the
    saying holds it better than any reconstruction of it.
    """
    needle = _skeleton_words(rendered)
    if len(needle) < MIN_MATCH_WORDS:
        return None
    best: tuple[float, str, str] | None = None
    for where, candidate in _candidates_from_book(book_dir) + _candidates_from_mirror():
        if not same_extent(rendered, candidate):
            continue
        score = _overlap(needle, set(_skeleton_words(candidate)))
        if score >= MIN_LIBRARY_OVERLAP and (best is None or score > best[0]):
            best = (score, where, candidate)
    return (best[1], best[2]) if best else None


# ── rung 2: the open web, sourced or not at all ──────────────────────────────


def find_by_research(
    run: str, *, rendered: str = "", context: str = "", book_title: str = ""
) -> tuple[str, list[str]] | None:
    """(the source's wording, source names) from grounded search, or None.

    THE WEB IS A CROSS-CHECK HERE, NEVER AN AUTHORITY, and that is not caution — it is
    what the sources turned out to be. Asked for this corpus's first saying on 2026-08-09,
    the grounded search came back citing facebook.com, reddit.com, wiktionary.org and
    parentingpatch.com alongside two real Islamic sites. An Arabic wording of a hadith
    filed on the strength of a Reddit link is worse than one reconstructed from the
    transliteration, because the reconstruction at least claims no source.

    So an answer is accepted ONLY when its Arabic agrees with the skeleton the book's own
    transliteration spells. Agreement means the web is confirming what the page already
    said, and its value is the vowelling and the citation rather than the wording. A
    disagreement means it has found a DIFFERENT saying, or the better-known variant of
    this one, and substituting that would be the recall this whole ladder exists to avoid.

    Returns None for every failure a caller should simply step past — an unsourced answer,
    a bridge error, no Arabic in the reply, or a disagreement. Each has the same meaning:
    the web could not confirm a wording, and the ladder continues to reconstruction.
    """
    from _scholar_bridge import ScholarBridgeError, research

    # WITHOUT A RENDERING THERE IS NOTHING TO CHECK AGAINST, so there is no safe way to
    # accept a wording off the web. Refusing here is what makes the agreement rule an
    # invariant rather than a best effort — it was written as `if rendered and …`, and a
    # failed render silently turned the check off.
    if not _skeleton_words(rendered):
        return None

    question = (
        "In Islamic and Ismaili scholarly sources, what is the original Arabic wording of "
        f'the saying transliterated as "{run.strip()}", and where is it narrated? '
        "Quote the Arabic itself, fully vowelled."
    )
    try:
        answer = research(concept=run.strip(), context=context, book_title=book_title, question=question)
    except ScholarBridgeError:
        return None
    if not answer.get("ok", True):
        return None
    sources = [str(s) for s in (answer.get("sources") or []) if s]
    arabic = _best_matching_arabic(str(answer.get("body") or ""), rendered)
    if not arabic or len(arabic.split()) < MIN_MATCH_WORDS or not sources:
        return None
    if not same_extent(rendered, arabic):
        return None
    return arabic, sources


# ── the ladder ───────────────────────────────────────────────────────────────


def resolve(
    run: str,
    *,
    book_dir: Path,
    context: str = "",
    book_title: str = "",
    allow_research: bool = True,
    log=print,
) -> Resolution:
    """Walk the three rungs for one romanized saying. Never raises for a miss.

    ``allow_research=False`` skips the one metered rung, for a run that should cost
    nothing — the library and the reconstruction are both free.
    """
    rendered = ""
    try:
        rendered = render_from_transliteration(run, book_dir=book_dir, context=context, log=log)
    except Exception as e:  # noqa: BLE001 - a failed render still leaves rungs 1 and 2
        log(f"      render failed for {run[:40]!r}: {e}")

    if rendered:
        found = find_in_library(rendered, book_dir=book_dir)
        if found:
            where, text = found
            return Resolution(run, text, LIBRARY, detail=where)

    if allow_research:
        researched = find_by_research(run, rendered=rendered, context=context, book_title=book_title)
        if researched:
            arabic, sources = researched
            return Resolution(run, arabic, RESEARCHED, sources=sources)

    return Resolution(run, rendered, RECONSTRUCTED, detail="rendered from the transliteration")


RECORD_NAME = "book-romanization.json"


# ---------------------------------------------------------------------------
# Is the repair a substitution, or a deletion?
#
# The ladder above answers "what is this saying in Arabic". These two answer the
# question that comes first: whether the page ALREADY prints it, in which case the
# romanization is a duplicate and substituting would set the Arabic twice.
# ---------------------------------------------------------------------------


def already_in_script(section: str, run: str, arabic: str) -> bool:
    """Does this saying's OWN Arabic already print beside the romanization?

    Compared by consonantal skeleton, because the two copies genuinely differ: the same
    saying appears in Spiritual Ethos once as `أَنَا` and once as `أِنَا`, and a book that
    prints a saying twice may vowel it twice differently. The skeleton is the thing that
    identifies a wording; the marks are not.

    "Beside" is the paragraph the bracket sits in and its two neighbours — the same window
    `_book_defects.romanized_arabic` uses to decide the run is a saying at all, and where
    a display quotation actually goes. It must NOT be the whole chapter: nine of the
    eleven findings in Spiritual Ethos have Arabic within a line or two that belongs to a
    DIFFERENT saying, and treating those as duplicates would delete the only record of
    the wording that romanization carries.
    """
    from _book_defects import ARABIC_ONLY_RE

    skeleton = _skeleton(arabic)
    if not skeleton:
        return False
    paragraphs = section.split("\n\n")
    index = next((i for i, p in enumerate(paragraphs) if f"({run})" in p or run in p), None)
    if index is None:
        return False
    window = "\n\n".join(paragraphs[i] for i in (index - 1, index, index + 1) if 0 <= i < len(paragraphs))
    return any(_skeleton(found.group(0)) == skeleton for found in ARABIC_ONLY_RE.finditer(window))


#: Perso-Arabic letters folded to the Arabic they stand for, BEFORE the shared skeleton
#: is taken. `_arabic_coverage.normalize_arabic` keeps only U+0621–U+064A, so it does not
#: fold these — it DROPS them, and a dropped letter is worse than an unfolded one because
#: the two spellings then differ in length as well as in content.
#:
#: This is not hypothetical and it is not rare: Spiritual Ethos prints the same saying of
#: the Prophet twice, once in Arabic letters and once in Persian ones — `أَنْتَ مِنِّي وَأَنَا
#: مِنْكَ` beside `أنْتَ مِنِّی وَ أِنَا مِنْکَ` — and without this fold the first run of the repair
#: read them as different sayings and printed the Arabic twice on one line.
#:
#: Folded HERE rather than in `normalize_arabic`, deliberately. That function is what the
#: mushaf matcher and the fabricated-Arabic gate compare with, and widening what it keeps
#: changes two answers that have nothing to do with this repair. That it silently drops
#: Persian letters is worth fixing on its own terms, with those gates in front of it.
_PERSO_ARABIC_FOLD = str.maketrans({"ی": "ي", "ک": "ك", "ھ": "ه", "ہ": "ه"})


def _skeleton(text: str) -> str:
    """The consonantal skeleton, with Perso-Arabic letters folded in first."""
    from _arabic_coverage import normalize_arabic

    return normalize_arabic((text or "").translate(_PERSO_ARABIC_FOLD))


def drop_romanization(section: str, run: str) -> tuple[str, bool]:
    """Remove one bracketed romanization, and the space that introduced it.

    Returns the section and whether anything was removed, so a caller never records a
    repair that did not happen. Only the bracket goes: the author's sentence and the
    English rendering beside it are untouched, which is the whole reason deleting is
    safe where the script is already on the page.
    """
    for pattern in (f" ({run})", f"({run})"):
        if pattern in section:
            return section.replace(pattern, "", 1), True
    return section, False


def write_record(book_dir: Path, resolutions: list[Resolution]) -> Path:
    """Persist where every saying's Arabic came from. The audit trail, not a gate."""
    path = Path(book_dir) / "_system" / RECORD_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "book.romanization/v1",
        "counts": {
            key: sum(1 for r in resolutions if r.provenance == key) for key in (LIBRARY, RESEARCHED, RECONSTRUCTED)
        },
        "resolutions": [r.as_record() for r in resolutions],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
