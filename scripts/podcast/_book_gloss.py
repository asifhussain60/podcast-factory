"""_book_gloss.py — the AUTHOR'S OWN gloss brackets, and what may be done to them.

Split out of `_book_inline_arabic.py` (2026-08-02), which crossed the repo's
600-line module ceiling. The split is not arbitrary: everything here is about one
question — is this bracket the author's romanisation gloss, and which way round
does it run — while the parent module is about WHERE a term's script belongs in a
chapter. They were tangled because both reach for a parenthesis.

The distinction that earns this its own file:

    CONVERSION   `the ranks (hudud)` -> `the ranks (حُدُود)`. The author already
                 wrote the bracket; changing its contents adds no apparatus, so
                 it is unconditional and applies to EVERY occurrence.
    ANNOTATION   opening a NEW bracket beside a plainly-used term. That IS
                 apparatus and stays rationed by the annotation policy. It lives
                 in the parent module.

And the trap that makes both dangerous — the book brackets BOTH ways round:

    the ranks (hudud)     the bracket holds the transliteration -> convert
    *Qutb* (pole)         the bracket holds the MEANING         -> leave alone
"""

from __future__ import annotations

import re

from _arabic_coverage import normalize_arabic
from _translit import simplify_transliteration

# Name connectors and the article. Grammatical glue inside a name, never a term a
# reader needs glossed: annotating them split "Jafar ibn Mansur al-Yaman" into
# "Jafar ibn (بن) Mansur…" the first time this ran.
_NAME_PARTICLES = frozenset({"ibn", "bin", "ibn.", "bint", "abu", "abi", "umm", "al", "aal"})


def _is_person(phonetic: str) -> bool:
    """True for a personal name, where the transliteration IS the English.

    A reader needs "Jafar ibn Mansur al-Yaman" romanised; they do not need
    "bab" romanised once the script is beside it. Detected by a standalone name
    particle, so "al-Imam al-Natiq" (a title, hyphen-prefixed) is NOT a person
    while "Jafar ibn Mansur al-Yaman" is.
    """
    return any(w.lower() in _NAME_PARTICLES for w in phonetic.split())


def _gloss_paren_re(phonetic: str) -> str:
    """`(term)` exactly — the author's own gloss bracket, with optional emphasis.

    Anchored to the parentheses on both sides so it can only ever match a
    parenthesis whose WHOLE content is this term. A term appearing in running
    prose, or inside a longer parenthetical phrase, is not a gloss site and is
    left to the annotation path.
    """
    return r"\(\s*[*_]?" + re.escape(phonetic) + r"[*_]?\s*\)"


def _convert_glosses(line: str, terms: list[dict[str, str]], pending: dict[str, dict[str, str]]) -> tuple[str, int]:
    """Swap the romanisation inside the AUTHOR'S OWN gloss brackets for the script.

    CONVERSION, which is not ANNOTATION (Asif, 2026-08-02). The two wear the same
    shape and were folded through the same once-per-book budget, so the second
    time the author glossed a term it kept its romanisation — one page reading
    `governance (سِيَاسَة)` and the next `governance (siyasa)`.

    They are different acts. Changing what is inside a bracket the author already
    wrote adds no apparatus: the page carries exactly as many brackets
    afterwards. So it is unconditional and applies to EVERY occurrence, which is
    what "zero English transliteration of Arabic terms in book.md" asks for.
    Adding a NEW bracket beside a plainly-used term IS apparatus, and stays
    rationed by the annotation policy.

    A converted mention still CONSUMES the term's annotation budget: the reader
    has met the script, in the author's own place, so opening a second bracket
    elsewhere would be the repetition the policy exists to prevent.

    `familiar` and `silent` terms CONVERT — they only decline ANNOTATION. Their
    class says "the English form is the word, so do not open a bracket for this";
    it says nothing about a bracket the author opened himself. Leaving them was
    the difference between 31 romanised brackets and none, and it printed
    `the alms-tax (zakat)` on a page where every other term had its script.

    A personal name is skipped — its romanisation is how an English reader says
    it, and the script is appended beside rather than swapped in.

    So is a bracket whose script is ALREADY the word in front of it — see
    ``_glosses_script_already_there``.
    """
    n = 0
    by_phonetic = {t["phonetic"] for t in terms}
    for t in terms:
        phonetic, script = t["phonetic"], t["script"]
        if t["style"] == "name" or _is_person(phonetic):
            continue
        matches = [
            m
            for m in re.finditer(_gloss_paren_re(phonetic), line)
            if not _is_reversed_gloss(line, m.start(), by_phonetic)
            and not _script_already_precedes(line, m.start(), script)
        ]
        if not matches:
            continue
        for m in reversed(matches):  # right-to-left: no earlier offset shifts
            line = line[: m.start()] + f"({script})" + line[m.end() :]
            n += 1
        pending.pop(phonetic, None)
    return line, n


def _script_already_precedes(line: str, start: int, script: str) -> bool:
    """Is the Arabic in front of this bracket already the script we would insert?

    The letters-as-letters case, and the ONE place a romanisation beside script is
    the correct printed form rather than a defect. When the book discusses a word
    AS A WORD it prints the script and glosses it for a reader who cannot sound it
    out — `from them is derived كُن (Kun), which is two letters`. Converting that
    bracket produces `كُن (كُن)`: the script said twice, the pronunciation gone,
    and a sentence about two letters that no longer shows the reader which two.

    It is also a P0 in the challenger spec (BK-N4: keep the script and set the
    transliteration beside it, `كُنْ (kun)`), and it is the carve-out Asif kept on
    2026-08-02 when he scoped the zero-transliteration rule to Arabic VOCABULARY.

    Compared by consonantal skeleton, so the vowelling on either side — the book's
    own on one, `vowel_book`'s on the other — cannot hide the match.
    """
    head = line[:start].rstrip()
    if not head:
        return False
    tail = normalize_arabic(head[-len(script) - 12 :])
    needle = normalize_arabic(script)
    return bool(needle) and tail.endswith(needle)


def _is_reversed_gloss(line: str, start: int, phonetics: set[str]) -> bool:
    """Is this bracket holding the ENGLISH rather than the transliteration?

    The book uses the convention BOTH WAYS round:

        english (translit)   `the ranks (hudud)`   -> convert the bracket
        *Translit* (english) `*Qutb* (pole)`       -> the bracket is the MEANING

    Converting the second destroys the translation and leaves the Arabic term
    glossed by itself: `*Qutb* (قُطْب)`. Caught live on this book, because
    `pole` reached the glossary as a term — it sits inside a parenthesis exactly
    where a transliteration would, and the OCR has قطب nearby, so the fill gave
    it script.

    The tell is what PRECEDES the bracket: an emphasised word that is itself a
    glossary term means the Arabic has already been named and the bracket is
    explaining it. Deliberately narrow — it requires the emphasis AND a known
    term, so an ordinary `the ranks (hudud)` is untouched.
    """
    before = line[:start].rstrip()
    tail = re.search(r"[*_]([A-Za-z'’\- ]{2,45})[*_]$", before)
    if not tail:
        return False
    # Case-insensitive: the prose capitalises a term at the head of a clause
    # (`*Qutb*`) while the glossary anchor is lower-case (`qutb`).
    named = simplify_transliteration(tail.group(1)).strip().lower()
    return named in {p.lower() for p in phonetics}


def _gloss_span(line: str, start: int, end: int) -> tuple[int, int] | None:
    """If the term at [start,end) IS a parenthetical transliteration gloss, return
    the span of the whole `(*term*)`.

    The author's convention puts the romanisation in brackets after the English:
    `his gate (*bab*)`. The term therefore sits INSIDE the parentheses, not
    before them — so the script must REPLACE that bracket, not open a second one
    inside it.
    """
    a = start
    while a > 0 and line[a - 1] in "*_":
        a -= 1
    if a == 0 or line[a - 1] != "(":
        return None
    b = end
    while b < len(line) and line[b] in "*_":
        b += 1
    if b >= len(line) or line[b] != ")":
        return None
    # Absorb one leading space so "gate (bab)" -> "gate (script)", not "gate  (…)".
    open_at = a - 1
    if open_at > 0 and line[open_at - 1] == " ":
        open_at -= 1
    return (open_at, b + 1)
