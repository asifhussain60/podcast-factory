"""_book_defect_fixes.py — the repairs for what `_book_defects` finds.

Detection and repair are separate modules on purpose. The detectors are read-only and
three callers share them; these functions REWRITE prose, and prose bound for the PDF has
a single sanctioned path — the Book Composer. So nothing here is wired into a compose
step. `compose_fix.py` calls them, records the result through the Composer's own save,
and the replay carries it into every future compose.

WHAT IS REPAIRED HERE, AND WHAT IS NEVER

  duplicated-arabic         REPAIRED. The lead-in's inline copy is deleted and the
                            blockquote keeps the quotation. Deterministic: the two runs
                            are already known to be the same text.

  prophet-wrong-honorific   REPAIRED. `The Messenger of Allah (ع)` becomes
                            `The Messenger of Allah ﷺ`. His own form (Asif, 2026-08-09).

  honorific-overuse         REPAIRED. The first use in a chapter stays, the rest go.

  stray-emphasis            REPAIRED. A `**` whose partner is in another paragraph of
                            the same quotation never pairs — both renderers set each
                            paragraph separately — so both markers print. The opener
                            is closed in its own paragraph and the orphan deleted. Not
                            one word changes.

  romanized-honorific       REPAIRED. `Rasul Allah(Salallahu alayhi wa aalihee wa
                            sallam)` becomes `Rasul Allah ﷺ`, and `Allah (Subhanahu wa
                            Ta'ala)` becomes `Allah سُبْحَانَهُ وَتَعَالَى`. Split from the row
                            below because the two have OPPOSITE repairs and reporting
                            them together made 197 fixable instances read as unfixable.

  romanized-arabic          NEVER, not here. Two of the fourteen live instances have no
                            Arabic anywhere on disk — not in the book, not in the source
                            scan, not in the hadith corpus — so the only way to supply
                            their script is a model recalling scripture, which this repo
                            forbids. `proposed_romanization_deletions` returns what a
                            human could approve; nothing applies it automatically.

  english-rtl               NEVER. It was a renderer defect and it is fixed there. A
                            content repair would be a workaround for a bug that is gone.

  translation-outside-card  REPAIRED. The rendering is folded into the blockquote above
                            it, where every card on the approved specimen page carries
                            it. Nothing is reworded and nothing is deleted — the same
                            sentence moves one level in.

  translation-leads-a-      REPAIRED. The paragraph OPENS on the rendering and continues
  paragraph                 into a sentence of the author's own. The rendering joins the
                            card and the sentence stays where it is — the boundary is the
                            author's own punctuation, so nothing is decided here either.

  translation-fused-with-  NEVER. What follows the rendering is not a sentence but a
  prose                     connective the author's sentence depends on — `(Al-Araf: 156),
                            and` — or an interjection between two halves of one verse.
                            Moving the rendering out leaves prose that no longer parses, so
                            the repair would have to WRITE something. That is authorship.

Every function is idempotent: running it twice changes nothing the first run did not.
"""

from __future__ import annotations

import re

from _arabic_coverage import ARABIC_BODY, normalize_arabic
from _book_defects import (
    ARABIC_ONLY_RE,
    MIN_QUOTATION_CHARS,
    blocks,
    duplicated_arabic,
)
from _book_honorific_defects import (
    _HONORIFIC_RE,
    _PROPHET_NAME,
    _ROMANIZED_HONORIFIC_RE,
    _figure_before,
    figure_key,
    honorific_script,
    opens_a_longer_formula,
)

#: The Prophet's own honorific (U+FDFA). Set in the Arabic face at the size the rest of
#: the Arabic uses, because the renderer wraps it in the same inline-Arabic span.
PROPHET_LIGATURE = "ﷺ"

#: A parenthesised Arabic run in running prose — the shape the lead-in duplicate takes.
_INLINE_ARABIC_PAREN_RE = re.compile(f"\\s*\\(([{ARABIC_BODY}][{ARABIC_BODY}\\s،؛]*)\\)")

#: Arabic faces that DO NOT CONTAIN U+FDFA. A book set to one of these prints an empty
#: box wherever the ligature lands — and since the Prophet's honorific is mandatory on
#: every mention of him by name, that is most pages. Verified by reading the font files
#: 2026-08-09: Amiri, Scheherazade New and IBM Plex Sans Arabic carry the glyph; these
#: two do not. Both are selectable in the Composer's own font list, so this is a live
#: setting a book can already be on, not a hypothetical.
FACES_WITHOUT_LIGATURE = frozenset({"cairo", "tajawal"})

#: What a book with no style artifact reads as. Mirrors DEFAULT_ARABIC in
#: `plan-dashboard/src/pages/api/studio/citation-style.ts`; four of the seven reading
#: editions have no artifact at all and are on this face by omission.
DEFAULT_ARABIC_FACE = "scheherazade-new"


def arabic_face(book_dir) -> str:
    """The non-Qur'anic Arabic face this book prints in."""
    import json
    from pathlib import Path

    artifact = Path(book_dir) / "book" / "citation-style.json"
    if not artifact.is_file():
        return DEFAULT_ARABIC_FACE
    try:
        return str(json.loads(artifact.read_text(encoding="utf-8")).get("arabic_font") or DEFAULT_ARABIC_FACE)
    except Exception:  # noqa: BLE001 - an unreadable style file is not a font decision
        return DEFAULT_ARABIC_FACE


def ligature_is_printable(book_dir) -> tuple[bool, str]:
    """Would `ﷺ` render, or would this book print a box? Checked BEFORE writing one.

    The guard exists because the failure is silent in exactly the wrong direction: the
    write succeeds, the tests pass, the markdown is correct, and the printed page carries
    a missing-glyph box on every page. Nothing downstream reads a font file.
    """
    face = arabic_face(book_dir)
    if face.lower() in FACES_WITHOUT_LIGATURE:
        return False, (
            f"this book is set in {face}, which has no glyph for the Prophet's honorific — "
            "every mention would print an empty box. Change the Arabic face on the Compose "
            "tab first (Amiri, Scheherazade New and IBM Plex Sans Arabic all carry it)."
        )
    return True, f"{face} carries the glyph"


_PROPHET_HONORIFIC_SUB_RE = re.compile("(" + _PROPHET_NAME + r")\s*" + _HONORIFIC_RE.pattern, re.IGNORECASE)


def use_prophet_ligature(md: str) -> tuple[str, int]:
    """Give the Prophet his own honorific wherever he carries somebody else's.

    Idempotent: the pattern matches only a compact honorific, and the ligature is not
    one, so a second run finds nothing.
    """
    replaced = 0

    def _swap(match: re.Match[str]) -> str:
        nonlocal replaced
        replaced += 1
        return f"{match.group(1)} {PROPHET_LIGATURE}"

    return _PROPHET_HONORIFIC_SUB_RE.sub(_swap, md), replaced


def set_honorifics_in_script(md: str) -> tuple[str, int]:
    """Put a spelled-out devotional formula into the script it belongs in.

    `Rasul Allah(Salallahu alayhi wa aalihee wa sallam)` becomes `Rasul Allah ﷺ`;
    `Allah (Subhanahu wa Ta'ala)` becomes `Allah سُبْحَانَهُ وَتَعَالَى`.

    WHY THIS IS A REPAIR WHEN `romanized-arabic` IS NOT. That refusal is about a SAYING:
    a specific Arabic wording that is not on disk, which only a model recalling scripture
    could supply. A honorific is one fixed formula said the same way by everyone who says
    it — and this module already hardcodes one of them, `PROPHET_LIGATURE`, on exactly
    that reasoning. The two cases were being reported together, which is what made 197
    instances in Surah Al-Fateha read as unfixable when 197 of them were the easy kind.

    THE BRACKETS GO WITH THE ROMANIZATION, because a honorific in script is not
    parenthetical in this library: `the Prophet ﷺ` is how every other book sets it. The
    leading whitespace is consumed and one space written back, so `Allah(...)` — no space,
    as the transcripts often have it — does not come out as `Allahﷺ`.

    Idempotent: the pattern matches Latin letters inside brackets, and neither the
    ligature nor the vowelled Arabic is that, so a second run finds nothing.
    """
    replaced = 0

    def _swap(match: re.Match[str]) -> str:
        nonlocal replaced
        script = honorific_script(match.group(0).strip().strip("()"))
        if script is None:  # unreachable while the two regexes share one table
            return match.group(0)
        replaced += 1
        return f" {script}"

    return _ROMANIZED_HONORIFIC_RE.sub(_swap, md), replaced


def balance_paragraph_emphasis(md: str) -> tuple[str, int]:
    """Make each paragraph's `**` markers pair inside that paragraph, as they must.

    Both renderers set every paragraph of a quotation as its own `<p>`, so a marker whose
    partner is in a different paragraph never pairs and both print. The repair is decided
    by which end the orphan is:

      opens and never closes   the closer is written at the end of ITS OWN paragraph, so
                               the emphasis the author started is kept and confined
      closes and never opened  the marker is deleted — it is the orphan the quotation
                               builder appended, and there is nothing for it to close

    On the eight live blockquotes in Love Of The Prophet that keeps the bold attribution
    line the author wrote and removes the stray pair at the far end of the quotation. Two
    characters move and two are deleted; not one word changes.

    Idempotent: after one pass every paragraph's count is even.
    """
    fixed = 0
    chunks: list[str] = []
    for chunk in md.split("\n\n"):
        lines = chunk.split("\n")
        groups: list[list[int]] = []
        cur: list[int] = []
        for index, line in enumerate(lines):
            body = line[1:] if line.startswith(">") else line
            if not body.strip():
                if cur:
                    groups.append(cur)
                    cur = []
                continue
            cur.append(index)
        if cur:
            groups.append(cur)

        for group in groups:
            text = " ".join(lines[i] for i in group)
            if text.count("**") % 2 == 0:
                continue
            opens = text.lstrip().lstrip(">").lstrip().startswith("**")
            last = group[-1]
            body = lines[last].rstrip()
            trailing = lines[last][len(body) :]
            if body.endswith("**") and not opens:
                lines[last] = body[:-2].rstrip() + trailing
            else:
                lines[last] = body + "**" + trailing
            fixed += 1
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks), fixed


def cap_honorifics(md: str, *, cap: int = 1) -> tuple[str, int]:
    """Keep the first `cap` compact honorifics per figure per chapter; drop the rest.

    Asif, 2026-08-09: once per figure per chapter, used where it adds value rather than
    after every occurrence of the name. Counted per chapter because a chapter is what a
    reader sits down to, and re-introducing the convention in the next one is a courtesy
    rather than clutter.

    Runs per chapter over the whole document at once, so the ordinal a figure's honorific
    holds is its position in that chapter — which is what "the first use" means.
    """
    out: list[str] = []
    dropped = 0
    counts: dict[str, int] = {}
    for line in md.split("\n"):
        if line.startswith("## "):
            counts = {}
            out.append(line)
            continue
        rebuilt: list[str] = []
        cursor = 0
        for match in _HONORIFIC_RE.finditer(line):
            if opens_a_longer_formula(line, match.start()):
                continue
            # Keyed by `figure_key`, not by the label: "Ali" and "Ali ibn Abi Talib" are
            # one man, and counting them separately left three honorifics in the first
            # two paragraphs of a chapter capped at one.
            key = figure_key(_figure_before(line[: match.start()]))
            counts[key] = counts.get(key, 0) + 1
            if counts[key] <= cap:
                continue
            start, end = _removal_span(line, match.start(), match.end())
            if start < cursor:
                continue
            rebuilt.append(line[cursor:start])
            # Close the sentence up: a space only where two WORDS would otherwise collide.
            # Punctuation must not get one — `supplication , : O Allah` is how that reads.
            if line[start - 1 : start].strip() and line[end : end + 1] not in ("", " ") and line[end] not in _CLOSERS:
                rebuilt.append(" ")
            cursor = end
            dropped += 1
        rebuilt.append(line[cursor:])
        joined = "".join(rebuilt)
        out.append(re.sub(r" +([,.;:!?)\]])", r"\1", joined) if len(rebuilt) > 1 else joined)
    return "\n".join(out), dropped


#: Punctuation that closes what precedes it, so a removal must never leave a space before it.
_CLOSERS = ",.;:!?)]}»"


def _removal_span(line: str, start: int, end: int) -> tuple[int, int]:
    """The span to delete so the sentence still reads.

    A honorific is punctuated three ways in this corpus, and taking out only the brackets
    breaks two of them — measured on 2026-08-09 over 1,674 instances:

        `The Messenger of Allah, (ع), used to`   370x   an APPOSITIVE: both commas are
                                                       the honorific's, and leaving them
                                                       printed `Allah,, used`.
        `Muhammad, (ع) and his family`            98x   a leading comma only.
        `in his supplication, (ع): O Allah`       39x   leading comma, then a colon that
                                                       belongs to the sentence and stays.
        `Ali (ع) said`                           rest   no punctuation at all.

    So: take a leading comma when there is one, and take a trailing comma ONLY when a
    leading one was taken — that pairing is what makes it an appositive rather than the
    sentence's own comma. `He said, (ع), "…"` is the case that proves the rule: both go,
    and the quotation's own comma is the one the sentence re-supplies.
    """
    while start > 0 and line[start - 1] == " ":
        start -= 1
    had_lead = start > 0 and line[start - 1] == ","
    if had_lead:
        start -= 1
        while start > 0 and line[start - 1] == " ":
            start -= 1
    if had_lead:
        trail = end
        while trail < len(line) and line[trail] == " ":
            trail += 1
        if trail < len(line) and line[trail] == "," and not _comma_belongs_to_a_quotation(line, trail):
            end = trail + 1
    return start, end


#: What a comma introduces when it is the SENTENCE's rather than the appositive's.
_QUOTE_OPENERS = "\"“'‘«"


def _comma_belongs_to_a_quotation(line: str, comma: int) -> bool:
    """`He said, (ع), "Do not…"` — that second comma is the quotation's, not the pair's.

    Without this the appositive rule ate it and the sentence printed `He said "Do not"`.
    The test is what FOLLOWS the comma: a quotation mark means the sentence needed it
    regardless of the honorific, so it stays.
    """
    after = comma + 1
    while after < len(line) and line[after] == " ":
        after += 1
    return after < len(line) and line[after] in _QUOTE_OPENERS


def drop_duplicated_inline_arabic(md: str) -> tuple[str, int]:
    """Delete the lead-in's inline copy of Arabic the blockquote under it repeats.

    The blockquote keeps the quotation — it is the form the edition sets in the Arabic
    face, and the lead-in is English prose that should read as English. Only a
    parenthesised run is removed, and only one whose text the blockquote already gives,
    so nothing that appears once anywhere is ever touched.
    """
    if not duplicated_arabic(md):
        return md, 0

    removed = 0
    lines = md.split("\n")
    # Which Arabic runs a blockquote gives, per chapter, keyed by normalised text.
    chapter_quoted: set[str] = set()
    out: list[str] = []
    # Two passes per chapter: collect what the blockquotes hold, then clean the paras.
    sections: list[list[str]] = [[]]
    for line in lines:
        if line.startswith("## "):
            sections.append([])
        sections[-1].append(line)

    for section in sections:
        body = "\n".join(section)
        chapter_quoted = set()
        for kind, block_lines in blocks(body):
            if kind != "quote":
                continue
            for run in ARABIC_ONLY_RE.findall(" ".join(block_lines)):
                run = run.strip()
                if len(run) >= MIN_QUOTATION_CHARS:
                    chapter_quoted.add(normalize_arabic(run))
        if not chapter_quoted:
            out.extend(section)
            continue
        for line in section:
            if line.startswith(">") or not line.strip():
                out.append(line)
                continue

            def _maybe_drop(match: re.Match[str]) -> str:
                nonlocal removed
                inner = match.group(1).strip()
                if len(inner) < MIN_QUOTATION_CHARS or normalize_arabic(inner) not in chapter_quoted:
                    return match.group(0)
                removed += 1
                return ""

            cleaned = re.sub(_INLINE_ARABIC_PAREN_RE, _maybe_drop, line)
            out.append(re.sub(r" {2,}", " ", cleaned))
    return "\n".join(out), removed


def proposed_romanization_deletions(md: str) -> list[tuple[str, str]]:
    """(chapter, run) a human could approve deleting. NOTHING here applies them.

    An Arabic saying printed in the English character set breaks the rule locked
    2026-08-02, and the honest repair is to set it in Arabic — but the script has to come
    from somewhere. For two of the fourteen live instances it exists nowhere on disk, and
    a model recalling a hadith onto the page of a religious edition is not a repair.

    Deleting the romanization satisfies the rule and costs the reader nothing, because
    the English translation always sits immediately beside it. That is a judgment for
    Asif, so this only ever proposes.
    """
    from _book_defects import romanized_arabic

    return romanized_arabic(md)


def fold_translation_into_card(md: str) -> tuple[str, int]:
    """Move a stranded English rendering into the quotation card above it.

    The card is a blockquote holding only Arabic; the rendering is the paragraph under it.
    Markdown has no way to say "this paragraph belongs to that quotation" other than being
    inside it, so the repair is exactly that: the paragraph is re-emitted as a second
    paragraph of the same blockquote, separated by a bare `>`.

    NOTHING IS REWORDED AND NOTHING IS DELETED. The same sentence, character for
    character, moves one level in — which is what makes this safe to run across finished
    books, and what makes it reversible by hand if a single instance reads wrong.

    Idempotent by construction rather than by a guard: once the rendering is inside, the
    blockquote no longer holds only Arabic, so `_cards_missing_their_rendering` stops
    yielding it and a second run finds nothing.

    Only the paragraphs `translation_outside_card` accepts are moved — see
    `only_the_rendering` for why the rest are left where they are.
    """
    from _book_translation_cards import only_the_rendering

    def whole_paragraph(paragraph: list[str], text: str) -> list[str] | None:
        if not only_the_rendering(text):
            return None
        return [">"] + ["> " + line.strip() for line in paragraph]

    return _rewrite_stranded_renderings(md, whole_paragraph)


def split_translation_into_card(md: str) -> tuple[str, int]:
    """Move the rendering that OPENS a paragraph in, and leave the author's sentence out.

    The second tier (2026-08-09). Where `fold_translation_into_card` moves a paragraph that
    is nothing but the rendering, this one handles a paragraph that BEGINS with the
    rendering and continues into a sentence of the author's own:

        "…except those who stray in error?" (Al-Hijr: 56). The Quran's assurances of
        mercy come fully alive in souls that…

    The first part joins the card; the second stays exactly where it was, as its own
    paragraph. NOTHING IS REWORDED HERE EITHER — the boundary is the author's own
    punctuation, and `split_rendering_from_gloss` refuses any paragraph where the remainder
    would not stand as a sentence. Those are the ones a person has to resolve.

    The paragraph is re-emitted as two lines where it was one. Every book here writes a
    paragraph on a single line, so that is the house shape rather than a reflow.
    """
    from _book_translation_cards import split_rendering_from_gloss

    def leading_rendering(paragraph: list[str], text: str) -> list[str] | None:
        parts = split_rendering_from_gloss(text)
        if not parts:
            return None
        rendering, rest = parts
        return [">", "> " + rendering, "", rest]

    return _rewrite_stranded_renderings(md, leading_rendering)


def _rewrite_stranded_renderings(md: str, decide) -> tuple[str, int]:
    """Walk every Arabic-only blockquote and offer `decide` the paragraph beneath it.

    `decide(paragraph_lines, joined_text)` returns the lines to emit AFTER the quotation —
    which is how the two repairs above differ while sharing one reading of the markdown.
    Returning None leaves the blockquote and its paragraph exactly as they were.

    Both repairs are idempotent by construction rather than by a guard: whatever `decide`
    moves inside means the blockquote no longer holds only Arabic, so the next pass does
    not offer it again.
    """
    from _book_defects import is_arabic_quote_line, quote_paragraphs

    lines = md.split("\n")
    out: list[str] = []
    index = 0
    changed = 0

    while index < len(lines):
        if not lines[index].startswith(">"):
            out.append(lines[index])
            index += 1
            continue

        start = index
        while index < len(lines) and lines[index].startswith(">"):
            index += 1
        quote = lines[start:index]

        after = index
        while after < len(lines) and not lines[after].strip():
            after += 1
        para_start = after
        while after < len(lines) and lines[after].strip() and not lines[after].startswith((">", "#")):
            after += 1
        paragraph = lines[para_start:after]

        quoted = quote_paragraphs(quote)
        text = " ".join(line.strip() for line in paragraph).strip()
        emitted = (
            decide(paragraph, text) if quoted and paragraph and all(is_arabic_quote_line(p) for p in quoted) else None
        )
        out.extend(quote)
        if emitted is None:
            continue
        out.extend(emitted)
        changed += 1
        index = after

    return "\n".join(out), changed


#: Repairs by the defect name `_book_defects.DETECTORS` uses, so a caller can ask for a
#: fix by the same word the check reported. A defect absent from this map has no
#: automatic repair, and that is a statement rather than an omission — see the module
#: docstring for why `romanized-arabic`, `english-rtl` and `translation-fused-with-prose`
#: are not here.
FIXES = {
    "duplicated-arabic": drop_duplicated_inline_arabic,
    "prophet-wrong-honorific": use_prophet_ligature,
    "romanized-honorific": set_honorifics_in_script,
    "stray-emphasis": balance_paragraph_emphasis,
    "honorific-overuse": cap_honorifics,
    "translation-outside-card": fold_translation_into_card,
    "translation-leads-a-paragraph": split_translation_into_card,
}


def print_romanization_proposals(proposals: list[tuple[str, str]]) -> None:
    """Say why a romanized saying is proposed rather than repaired.

    Here rather than in the tool that prints it, matching `_quote_cards`,
    `_book_preface` and `_book_arabic_audit`: the module that decides what the
    defect is owns the sentence explaining it, so the rule and its explanation
    cannot drift into disagreement.
    """
    if not proposals:
        return
    print(
        f"\n  {len(proposals)} Arabic saying(s) print in the English character set. Nothing here "
        "applies a repair:\n  the honest fix is the Arabic, and where it exists nowhere on disk "
        "supplying it would mean\n  a model recalling scripture. Deleting the romanization is "
        "yours to approve — the English\n  translation always sits beside it."
    )
