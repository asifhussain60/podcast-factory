"""_sessions_prose_format.py — bring a Sessions-lane chapter's markup up to the
book's own presentation conventions, WITHOUT touching a single word of prose.

WHY THIS EXISTS. A Sessions-lane book's raw material is a lecture transcript
Asif marked up himself, written before this site's four-card quotation design
(`_quote_cards.py`, 2026-08-09) and before the house citation form
(`_book_citations.py`, 2026-08-01) existed. `sessions/articulate.py` is
correctly forbidden from restructuring content (REQ-BA-020/030 — rewording
only, never reorganizing), so it faithfully carries the transcript's own
legacy conventions straight through into book.md:

  1. A bare `81:22` on its own line, immediately above a scripture quotation —
     a note-to-self citation, not the house form `(At-Takwir: 22)`, and not
     even inside the parentheses `_book_citations.py`'s own pattern requires.
     Left alone it just sits as noise; once the verse below it is confirmed
     Qur'anic (`_mushaf.is_quranic`, canonical-mushaf-first, never guessed)
     and the Arabic audit re-runs, the quotation card generates its OWN gold
     citation header from the very same resolution — so the bare line is
     pure duplication once a card can draw itself.
  2. `### Trustworthy Friend ولیجۃ` followed on the next line by `WALEEJA` — a
     transcript author's own transliteration written before the heading
     carried the Arabic at all. Once the Arabic sits in the heading, the
     bare-caps line under it says nothing new.

WHAT THIS DOES NOT TOUCH. A verse whose Arabic does not resolve against the
canonical mushaf is left completely alone, citation line and all — the same
"never guess, never silently drop" discipline `_mushaf.is_quranic` was built
for. A heading with no trailing Arabic is untouched. A heading with trailing
Arabic but no bare-caps line under it (most of them — this is conditional,
not assumed) loses nothing extra.

WHERE THIS RUNS. Both `compose_articulate.py` (a hand-off chapter) and
`sessions/articulate.py` (the automated pass) call `normalize_sessions_prose`
on a chapter body before it is ever written or gated, so the fix lands for
every future chapter the same way. `retrofit_book` in `compose_articulate.py`
applies it to a book already on disk.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _arabic_coverage import ARABIC_BODY  # noqa: E402
from _mushaf import is_quranic  # noqa: E402

_ARABIC_RANGE = ARABIC_BODY
_ARABIC_CHAR_RE = re.compile(f"[{_ARABIC_RANGE}]")
_LATIN_LETTER_RE = re.compile(r"[A-Za-z]")

#: `## Title Arabic-term` — trailing Arabic run with no parenthesis around it yet.
_HEADING_ARABIC_RE = re.compile(rf"(?m)^(#{{2,6}})[ \t]+(.+?)[ \t]+([{_ARABIC_RANGE}][^\n]*?)[ \t]*$")

#: A now-reformatted heading (ends `(Arabic)`) directly above a bare ALL-CAPS line.
_TRANSLIT_AFTER_HEADING_RE = re.compile(
    rf"(?m)(^#{{2,6}}[ \t]+.+\([{_ARABIC_RANGE}][^\n]*\)[ \t]*$)\n\n([A-Z][A-Z' \-]{{1,29}})\n\n"
)

#: A bare `81:22` or `26:99-101` reference, alone on its own line.
_BARE_CITE_RE = re.compile(r"^[ \t]*\d{1,3}:\d{1,3}(?:-\d{1,3})?[ \t]*$")
_NAMED_CITE_RE = re.compile(r"^[ \t]*(?:The\s+)?[A-Z][A-Za-z'’\- ]{2,30}\s+\[\d{1,3}:\d{1,3}(?:-\d{1,3})?\][ \t]*$")
_ARABIC_MARK_RE = re.compile(r"[\u0610-\u061a\u0640\u064b-\u065f\u0670\u06d6-\u06ed]")
_ARABIC_FOLD = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ی": "ي",
        "ئ": "ي",
        "ؤ": "و",
        "ة": "ه",
        "ۃ": "ه",
        "ہ": "ه",
        "ھ": "ه",
        "ك": "ک",
    }
)


def _arabic_skeleton(text: str) -> str:
    folded = _ARABIC_MARK_RE.sub("", text).translate(_ARABIC_FOLD)
    return re.sub(f"[^{_ARABIC_RANGE}]", "", folded)


def _is_prophetic_opener(text: str) -> bool:
    skel = _arabic_skeleton(text)
    return skel.startswith("قالرسولاللهصلياللهعليه") or skel.startswith("قالرسولاللهصلىاللهعليه")


def _is_markdown_structure(text: str) -> bool:
    stripped = text.strip()
    return bool(
        not stripped
        or stripped.startswith((">", "#", "!", "|", "<!--", "```"))
        or re.match(r"^[-*+]\s+", stripped)
        or re.match(r"^\d+\.\s+", stripped)
    )


def _is_arabic_only(text: str) -> bool:
    """Every character is script or punctuation — no Latin letters at all.

    The distinction that keeps this from ever wrapping ordinary prose: this
    book's English sentences constantly carry an inline Arabic word (`the
    names Allah gives... is صاحب:`), and those have Latin letters throughout.
    A bare verse line never does.
    """
    return bool(_ARABIC_CHAR_RE.search(text)) and not _LATIN_LETTER_RE.search(text)


def normalize_headings(body: str) -> tuple[str, list[dict]]:
    """`## Title ﺱ` -> `## Title (ﺱ)`; drop a now-redundant ALL-CAPS translit line."""
    changes: list[dict] = []

    def _sub(m: re.Match[str]) -> str:
        hashes, title, arabic = m.group(1), m.group(2).strip(), m.group(3).strip()
        new = f"{hashes} {title} ({arabic})"
        changes.append({"kind": "heading-parenthesized", "before": m.group(0).strip(), "after": new})
        return new

    body = _HEADING_ARABIC_RE.sub(_sub, body)

    def _strip(m: re.Match[str]) -> str:
        changes.append({"kind": "transliteration-removed", "under": m.group(1).strip(), "line": m.group(2)})
        return f"{m.group(1)}\n\n"

    body = _TRANSLIT_AFTER_HEADING_RE.sub(_strip, body)
    return body, changes


def normalize_bare_citations(body: str) -> tuple[str, list[dict]]:
    """Drop a bare `NN:NN` reference line once the card below it can name
    itself — wrapping a not-yet-carded verse in `>` first when needed.

    Three shapes, in the order a reader actually wrote them:
      - `81:22` above an existing `>` blockquote whose Arabic is confirmed
        Qur'anic: the reference line is deleted, nothing else changes.
      - `26:99-101` above a BARE (non-blockquote) Qur'anic line: that one
        line is wrapped in `>` and the reference is deleted. Only the single
        Arabic line — never a guess at which following prose is its
        translation, since a range citation's fragments are often followed
        by discursive commentary, not a literal rendering.
      - Anything that does not resolve against the canonical mushaf: left
        completely untouched, reference line included.
    """
    lines = body.split("\n")
    out: list[str] = []
    changes: list[dict] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not _BARE_CITE_RE.match(line):
            out.append(line)
            i += 1
            continue
        ref = line.strip()
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        if j >= n:
            out.append(line)
            i += 1
            continue
        if lines[j].lstrip().startswith(">"):
            k, arabic = j, None
            while k < n and lines[k].lstrip().startswith(">"):
                text = lines[k].lstrip(">").strip()
                if text and _ARABIC_CHAR_RE.search(text):
                    arabic = text
                    break
                k += 1
            if arabic and is_quranic(arabic):
                changes.append({"kind": "citation-line-removed", "ref": ref, "reason": "already carded"})
                i += 1
                continue
            out.append(line)
            i += 1
            continue
        candidate = lines[j].strip()
        if _is_arabic_only(candidate) and is_quranic(candidate):
            changes.append({"kind": "citation-wrapped", "ref": ref, "arabic": candidate})
            out.append(f"> {candidate}")
            i = j + 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out), changes


def normalize_named_quran_card_refs(body: str) -> tuple[str, list[dict]]:
    """Drop a standalone named reference once the Qur'an card below can head itself."""
    lines = body.split("\n")
    out: list[str] = []
    changes: list[dict] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not _NAMED_CITE_RE.match(line):
            out.append(line)
            i += 1
            continue
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        if j >= n or not lines[j].lstrip().startswith(">"):
            out.append(line)
            i += 1
            continue
        k, arabic = j, None
        while k < n and lines[k].lstrip().startswith(">"):
            text = lines[k].lstrip(">").strip()
            if text and _ARABIC_CHAR_RE.search(text):
                arabic = text
                break
            k += 1
        if arabic and is_quranic(arabic):
            changes.append({"kind": "named-citation-line-removed", "ref": line.strip()})
            i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out), changes


def normalize_hadith_cards(body: str) -> tuple[str, list[dict]]:
    """Remove formulaic hadith openers and keep the hadith with its translation.

    The Arabic line "قَالَ رَسُولُ..." is template chrome: the card already says
    "Prophetic tradition." When a paste leaves it as its own blockquote, the page
    draws two panels and no single hadith card. This pass only fires when that
    opener is immediately followed by another Arabic blockquote.
    """
    lines = body.split("\n")
    out: list[str] = []
    changes: list[dict] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.lstrip().startswith(">") or not _is_prophetic_opener(line.lstrip(">").strip()):
            out.append(line)
            i += 1
            continue

        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        if j >= n or not lines[j].lstrip().startswith(">"):
            out.append(line)
            i += 1
            continue

        quote_lines: list[str] = []
        k = j
        first_arabic = ""
        while k < n and lines[k].lstrip().startswith(">"):
            text = lines[k].lstrip(">").strip()
            quote_lines.append(text)
            if not first_arabic and _is_arabic_only(text):
                first_arabic = text
            k += 1
        if not first_arabic:
            out.append(line)
            i += 1
            continue

        m = k
        while m < n and not lines[m].strip():
            m += 1
        translation = ""
        if m < n and not _is_markdown_structure(lines[m]) and not _is_arabic_only(lines[m]):
            translation = lines[m].strip()

        emitted_lines = [text for text in quote_lines if text]
        for text in emitted_lines:
            out.append(f"> {text}")
        if translation:
            out.extend([">", f"> {translation}"])
            m += 1
        changes.append(
            {
                "kind": "hadith-card-normalized",
                "removed": line.lstrip(">").strip(),
                "first_line": first_arabic,
                "quote_kind": {"first_line": first_arabic, "kind": "hadith"},
            }
        )
        i = m if translation else k
    return "\n".join(out), changes


def strip_prophetic_openers(body: str) -> str:
    """Gate helper: remove only the boilerplate opener from comparison text."""
    kept = []
    for line in body.splitlines():
        if line.lstrip().startswith(">") and _is_prophetic_opener(line.lstrip(">").strip()):
            continue
        kept.append(line)
    return "\n".join(kept)


#: A run of ALL-CAPS words. Recognised so it can be REPORTED, never rewritten —
#: see `spoken_lane/prose_review.py` and the warning in `strip_echoed_heading`.
CAPS_RUN = re.compile(r"\b(?:[A-Z][A-Z'’]+[ ,]+){2,}[A-Z][A-Z'’]+\b")

#: Spacing an ASR leaves behind, repaired ONLY between ASCII letters.
#:
#: EVERY CHARACTER CLASS HERE IS SPELLED OUT, and that is the whole safety of the
#: rule. The first version used `\w` and `\s+`, both of which Python treats as
#: Unicode-aware, and running it over the shipped Sessions books changed 18
#: places — every one of them a space before a comma that follows ARABIC SCRIPT,
#: including inside a Qur'anic blockquote in `surah-al-fateha`
#: (`> And He taught Adam all the names , then He showed them`). A "spacing
#: repair" that edits Arabic in a religious quotation is not a repair; the
#: spacing around RTL script is not ours to normalise, and a rule that reaches
#: it silently is worse than no rule.
#:
#: `\s+` was the second half of the same mistake: it matches newlines, so a
#: comma opening a line would have been pulled up onto the previous one and a
#: paragraph break lost. A literal space, never a whitespace class.
_ASCII = "A-Za-z0-9"
_SPACING_REPAIRS: tuple[tuple[re.Pattern, str], ...] = (
    # A hyphen orphaned from the word it joins: `dark -haired`, `twenty -four`.
    # Both sides ASCII, so an em dash and a parenthetical ` - ` are untouched.
    (re.compile(rf"([{_ASCII}]) -([{_ASCII}])"), r"\1-\2"),
    (re.compile(rf"([{_ASCII}])- ([{_ASCII}])"), r"\1-\2"),
)

#: A space before a comma, which LOOKS like a typo and in these books is not.
#:
#: Reported by `spoken_lane/prose_review.py`, never repaired. Restricting the
#: rule to ASCII (above) took it from 18 hits on the shipped Sessions books to
#: 11, and reading those 11 is what retired it: they are the residue of a
#: MISSING ARABIC TERM, not loose spacing —
#:
#:     The word  , which is also used in Urdu
#:     the root word  , which means to create
#:     And He taught Adam all the names  , then He showed them   (a Qur'anic quote)
#:
#: Closing the space would make a sentence with a real content gap read as
#: though nothing were missing, which is the worst thing a cleanup can do: it
#: does not fix the defect, it hides it. The gap belongs in a report where
#: somebody can put the term back.
#: `?` and `!` included since 2026-09-01: the first version checked only `,`
#: and `;`, and `book-editor` found a fourth instance of the same shape before
#: a question mark that this therefore never reported.
SPACE_BEFORE_COMMA = re.compile(r"([A-Za-z0-9]) +([,;?!])")


def repair_spacing(body: str) -> tuple[str, list[dict]]:
    """Fix spacing an ASR produced. Deterministic, bounded, no model.

    Every repair here is one nobody could intend the other way round. Anything
    arguable — sentence spacing, quote style, the em dashes and the é in
    "cliché" — is deliberately left alone: a normalizer that also expresses
    preferences is one nobody can safely re-run.
    """
    changes: list[dict] = []
    for pattern, repl in _SPACING_REPAIRS:
        body, n = pattern.subn(repl, body)
        if n:
            changes.append({"rule": "spacing", "pattern": pattern.pattern, "count": n})
    return body, changes


def strip_echoed_heading(body: str, heading: str) -> tuple[str, list[dict]]:
    """Drop a chapter's own title where the narrator read it aloud.

    A recorded chapter opens with the reader saying its title, so the
    transcription begins with words the heading above it already carries:
    `## First Night` followed by "First Night It was a beautiful night".
    Six of White Nights' eight chapters do this, two of them in capitals
    ("SECOND NIGHT"), which is what put a shout in the middle of the prose.

    NARROW ON PURPOSE, and this is the whole reason the rule is safe. It removes
    a leading repeat of THIS chapter's own heading and nothing else. It does not
    touch capitals anywhere else in the body, and it is not a general
    "ALL-CAPS becomes a heading" rule — that rule was considered and rejected,
    because `surah-al-fateha` carries `AM YOUR KING` and `BOW DOWN BEFORE ME` as
    emphatic speech inside a quotation, and promoting those to section headings
    would put a divine utterance in a heading. Ambiguous capitals are REPORTED
    by `spoken_lane/prose_review.py` for a person to judge; only this
    unambiguous case is applied. Across all three shipped Sessions books the
    echoed heading occurs zero times, so no book on disk can regress on it.
    """
    heading = (heading or "").strip()
    if not heading:
        return body, []
    stripped = body.lstrip()
    lead = len(body) - len(stripped)
    # The heading, then optional trailing punctuation the narrator's inflection
    # produced ("Morning?"), then whitespace before the prose proper.
    pattern = re.compile(rf"^{re.escape(heading)}\s*[.,:;!?—-]*\s+", re.IGNORECASE)
    m = pattern.match(stripped)
    if not m:
        return body, []
    return body[:lead] + stripped[m.end() :], [
        {"rule": "echoed_heading", "heading": heading, "removed": stripped[: m.end()].strip()}
    ]


def normalize_sessions_prose(body: str, heading: str | None = None) -> tuple[str, list[dict]]:
    """Both passes, combined — the one entry point every caller uses.

    `heading` is optional and defaults to None, which is what keeps every
    existing caller byte-identical: without it the echoed-heading rule cannot
    fire, so a Sessions book normalized today produces exactly what it produced
    yesterday. Callers that know which chapter they are holding pass it.
    """
    body, heading_changes = normalize_headings(body)
    body, citation_changes = normalize_bare_citations(body)
    body, named_citation_changes = normalize_named_quran_card_refs(body)
    body, hadith_changes = normalize_hadith_cards(body)
    body, echo_changes = strip_echoed_heading(body, heading) if heading else (body, [])
    body, spacing_changes = repair_spacing(body)
    return body, (
        heading_changes + citation_changes + named_citation_changes + hadith_changes + echo_changes + spacing_changes
    )
