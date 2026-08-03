"""_book_substitution.py — the third operation: romanization OUT, script IN.

`_book_inline_arabic` names two operations and implements both:

    CONVERSION   the author wrote `(hudud)`; the bracket's contents become
                 `(حُدُود)`. No apparatus added, so it is unconditional.
    ANNOTATION   the pipeline ADDS a bracket beside a term the prose used
                 plainly. That IS apparatus, so it happens once per book under
                 the annotation policy.

Neither reaches the case Asif read on the page (2026-08-03): a term the prose
simply uses in romanization — `the *mawaddah*`, `what the grammarians call *nafi
al-jins*` — with no bracket anywhere near it. Nor does either collapse the
APPENDED shape it produced itself, `amal (عَمَل)`, down to `عَمَل`.

This is SUBSTITUTION, and it completes a rule already locked. Asif, 2026-08-02,
quoted in `_book_inline_arabic._annotate_chapter`: "there should be zero English
transliteration of Arabic terms, words, paragraphs, sentences, etc. in book.md.
All Arabic should be in the Arabic script, not in the English character set."
What makes that readable rather than hostile is the other locked rule — the
Arabic on this page is ALWAYS vowelled (`vowel_book.py`), and the romanization
keeps its home in the podcast lane, where pronunciation is the whole point.
`chapters/*.txt` is untouched by any of this.

REVERSIBILITY, and why it needs a sidecar
-----------------------------------------
`_normalize_annotations` can invert an annotation because the romanization is
still on the page to anchor it: it reads what precedes the bracket and decides
whether the bracket was appended or replaced a gloss. Substitution removes that
anchor. Afterwards nothing in the text distinguishes script this pass wrote from
script the SOURCE printed, so the inverse cannot be inferred at all — and a pass
that cannot invert itself can only ever add, which is the exact fossilisation
`_normalize_annotations` exists to prevent. Reclassify a term to `familiar` and
its English could never come back.

So the pre-substitution body is stored per chapter in
`_system/book-substitutions.json`, exactly as the Composer stores `body_md`, and
each run RESTORES before it re-derives. The stored body is trusted only when the
current text still fingerprints as this pass's own output; anything else means a
human or a later pass has been through, and the current text is left alone.

That fingerprint is stamped from the FINISHED page by `restamp_from_final_book`,
the last thing `apply_book_apparatus` does, and not by this pass at the moment it
runs — four apparatus steps rewrite book.md afterwards, so a number stamped here
names a chapter that never reaches disk. And an unverified record is now KEPT
rather than dropped: `before_md` is the only copy of the English anywhere, and
losing it is the one failure this whole mechanism exists to prevent.

WHAT IS SUBSTITUTED, AND WHAT IS NEVER
--------------------------------------
Two POSITIVE conditions, both required, because everything else on this list is
a denylist and no denylist is ever finished (`_book_substitution` shipped with
one and it passed the English word `approach`):

  the skeleton fits  the romanization must be a possible transliteration of the
                     script beside it — `hudud` of `حدود`. `_translit_skeleton`.
  class `teach`      a human has classified the term as one this book teaches.
                     `legacy` is an unreviewed harvest, and destructive
                     replacement across a whole book is not a thing to do on one.

And then, still:

  familiar/silent   `_glossary_terms` already gives these style "none". The
                    English form IS the word (Quran, Mount Sinai) or the term is
                    curated silent.
  name / a person   a name's romanization is the running prose. "Jafar ibn
                    Mansur al-Yaman" set in script makes the sentence unreadable,
                    and `_book_inline_arabic` already excludes names from
                    gloss-replacement for the same reason.
  letters-as-letters `كُنْ (kun)` — where a passage discusses Arabic AS LETTERS,
                    `book-challenger` BK-N4 REQUIRES both forms. Guarded by
                    `_script_already_precedes`, the same guard the overlay uses.
  quotations        blockquotes, headings, fences, tables — `_SKIP_LINE`.
  English in italics  `*blind*`, `*Path*` — emphasis, not a term. The harvester
                    now refuses to write one into the glossary and this pass
                    refuses to act on one already there.

A REVERSED gloss — `*Qutb* (pole)`, the bracket holding the English TRANSLATION —
is deliberately NOT excluded, unlike in the overlay. The overlay must not
overwrite that bracket; this pass never touches it, and replacing the
romanization in front of it gives `قُطْب (pole)`: translation kept, romanization
gone. Guarding it (the first version did) left romanization on the page, which is
the one thing the rule forbids.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _arabic_coverage import normalize_arabic
from _book_edits import anchor_key, fingerprint
from _book_gloss import _is_person, _script_already_precedes
from _book_inline_arabic import _ARABIC, _SKIP_LINE, _glossary_terms
from _gloss_terms import _TITLE_HEADS, _looks_english, absorbed_english
from _substitution_record import (
    _HEADING_RE,
    _chapters,
    _save_record,
    load_record,
    record_path,
    restamp_from_final_book,
    revert_ineligible,
)
from _translit_skeleton import romanizes

__all__ = [
    "apply_arabic_substitution",
    "load_record",
    "record_path",
    "restamp_from_final_book",
    "revert_ineligible",
    "substitutable_terms",
    "substitute_body",
    "substitute_text",
]

#: Read once — the file behind it never changes inside a run.
_ABSORBED = absorbed_english()


#: `term (script)` — the shape ANNOTATION produced. Collapsing it to the script
#: alone is the `amal (عَمَل)` -> `عَمَل` case, and it must run BEFORE the bare
#: pass or that pass would substitute the romanization and strand the bracket.
def _appended_re(phonetic: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![\w*_-])([*_]?)({re.escape(phonetic)})\1(?![\w'’-])[ \t]*\(([^)\n]*[{_ARABIC}][^)\n]*)\)",
        re.IGNORECASE,
    )


def substitutable_terms(book_dir: Path) -> list[dict[str, str]]:
    """Glossary terms this pass may put on the page, longest phonetic first.

    Built on `_glossary_terms`, so the honorific-formula, name-particle and
    empty-script exclusions are inherited rather than restated.

    TWO GATES, and the order of them is the point. Everything below the first is
    a denylist — a list of things this pass must not do — and no denylist is ever
    finished. The first gate is the opposite shape: POSITIVE evidence that the
    Latin string on the page is a romanization of the script standing beside it
    in the glossary. `mukhtasar-ul-asar-1` holds an entry whose phonetic is the
    English word `approach`, and every denylist here passed it: it is not in the
    ninety-word seed, not a loanword, not a title, not a person. The skeleton
    does not fit `المباشرة` and cannot fit any Arabic word, so it never gets that
    far now. See `_translit_skeleton`.

    The second gate is the annotation policy. Only `teach` — a term a human has
    classified as one this book teaches — is substitutable. `legacy` means the
    glossary was harvested and nobody has looked at it yet, and full-book
    destructive replacement is not a thing to do on an unreviewed list:
    `kunooz-al-hikmah` has 266 such entries, among them `surah` paired with
    `صُورَة`, which is *picture*. Structure cannot catch a wrong word spelled like
    the right one. A reviewer can.
    """
    return [
        t
        for t in _glossary_terms(book_dir)
        if t["style"] == "teach"
        and romanizes(t["phonetic"], t["script"])
        and not _is_person(t["phonetic"])
        # Words English has ADOPTED — Allah, imam, shaykh, Quran, Islam, hadith,
        # the prophet exonyms. `absorbed_english` exists for precisely this
        # question and its own docstring scopes it to "a term doing an ordinary
        # English job in running prose", which is exactly what this pass rewrites.
        # It also settles REQ-BA-070, which follows LAL 6.2.10 rule 15 in
        # requiring the Merriam-Webster English form where one exists: without
        # this, `*Shaykh*` became شَيْخ and `Allah` became اللَّه.
        and t["phonetic"].strip().lower() not in _ABSORBED
        # Defence in depth against a polluted glossary. The harvester now refuses
        # to write an English word, but three books already carried 21 of them
        # (`water`, `blind`, `Curse`, `Path`) harvested before that guard existed
        # — and this pass turned every one into Arabic in the running prose.
        and not _looks_english(t["phonetic"])
        # A WORK'S TITLE is not a term. `*Kitab ithbat al-imama*` became
        # `كتاب إثبات الإمامة` mid-sentence on the first live run — and unvowelled,
        # because a title harvested into the glossary never went through
        # `vowel_glossary`, so it printed in a different convention from every
        # other Arabic word on the page. Same head-word list `bare_term_findings`
        # uses, so the two agree about what a title is.
        and t["phonetic"].strip().split()[0].lower() not in _TITLE_HEADS
    ]


#: The last Arabic run before a position, and whether any Latin letter separates
#: it from that position.
_ARABIC_RUN = re.compile(rf"[{_ARABIC}]+(?:[ \t][{_ARABIC}]+)*")
_LATIN = re.compile(r"[A-Za-z]")


def _letters_as_letters(line: str, start: int, script: str) -> bool:
    """Does this script stand IMMEDIATELY before the match — `كُنْ (kun)`?

    `_book_gloss._script_already_precedes` answers the same question for the
    overlay and is reused everywhere else here, but it cannot be reused for a
    BARE term: it normalises the window first, and `normalize_arabic` drops Latin
    characters, so "…which is ذَوْق. Love and Zauq" reads as though the script
    were touching the term. It blocked a legitimate substitution in
    `ayyuhal-walad` from twenty characters away.

    The discriminator is that nothing WORDLIKE may come between. Punctuation and
    space may; a Latin letter may not.
    """
    head = line[:start]
    runs = list(_ARABIC_RUN.finditer(head))
    if not runs:
        return False
    last = runs[-1]
    if _LATIN.search(head[last.end() :]):
        return False
    return normalize_arabic(last.group(0)) == normalize_arabic(script)


#: A whole emphasis run: `*...*`, not `**bold**`.
_EMPHASIS_RUN = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")


def _inside_longer_romanization(line: str, start: int, end: int) -> bool:
    """True when the match is only PART of a longer romanized phrase.

    THE SHREDDING GUARD, and the reason it exists. `asaas-al-taveel` prints the
    shahada as `*La ilaha illa Allah*`. The glossary holds `La ilaha` and it also
    holds `illa`, so two separate terms matched inside one formula and the first
    live run produced `لَا إِلَهَ إِلَّا Allah*` — half script, half romanization, with
    the closing emphasis marker orphaned. Another line came out
    `*la ilaha إِلَّا Allah*`: one Arabic word dropped into the middle of an
    English-lettered formula.

    The signal is structural, not semantic. A term set in emphasis is a term; a
    term that is only PART of an emphasis run is a fragment of a phrase this pass
    does not know the whole of. Leave it intact for a human or for a longer
    glossary entry — a half-converted formula is worse than an unconverted one.

    Text outside emphasis is not judged here: ordinary English words surround
    every term, so adjacency there proves nothing.
    """
    for run in _EMPHASIS_RUN.finditer(line):
        if run.start(1) <= start and end <= run.end(1):
            return run.group(1).strip() != line[start:end].strip("*_ ")
    return False


def substitute_body(body: str, terms: list[dict[str, str]]) -> tuple[str, int]:
    """Replace romanized terms with their script. Returns (body, replacements)."""
    # keepends, and join with "" — `"\n".join(splitlines())` silently eats the
    # trailing newline of every chapter body, which on the first live run
    # collapsed nine blank lines out of `ayyuhal-walad` and glued paragraphs
    # together. This pass swaps words; it must not touch a single line break.
    lines = body.splitlines(keepends=True)
    replaced = 0
    for i, raw in enumerate(lines):
        line, nl = raw.rstrip("\r\n"), raw[len(raw.rstrip("\r\n")) :]
        if not line.strip() or _SKIP_LINE.search(line):
            continue
        for t in terms:
            phonetic, script = t["phonetic"], t["script"]

            # 1. The APPENDED shape first — `amal (عَمَل)` -> `عَمَل`. Running the
            #    bare pass first would rewrite the romanization and leave the
            #    bracket behind as `عَمَل (عَمَل)`.
            def _collapse(m: re.Match[str], _s: str = script) -> str:
                nonlocal replaced
                if _script_already_precedes(line, m.start(), _s):
                    return m.group(0)  # BK-N4: letters-as-letters keeps both
                # The shredding guard belongs on THIS path too, and its absence
                # cost the book's own title: `*Asas al-Tawil* (أُسَاسُ التَّأْوِيلِ)` has
                # a glossary entry for `al-Tawil` alone, so the collapse ate
                # `al-Tawil* (…)` and left `*Asas ` hanging open.
                if _inside_longer_romanization(line, m.start(2), m.end(2)):
                    return m.group(0)
                replaced += 1
                return _s

            line = _appended_re(phonetic).sub(_collapse, line)

            # 2. The bare romanization, with or without emphasis markers.
            # A REVERSED gloss is deliberately NOT guarded here, unlike in the
            # overlay. `*Qutb* (pole)` holds the English TRANSLATION in its
            # bracket; the overlay must not overwrite that bracket, but this pass
            # never touches it — it replaces the romanization standing in front,
            # giving `قُطْب (pole)`, which keeps the translation and removes the
            # romanization. Guarding it here left the romanization on the page,
            # which is the one thing the rule forbids.
            def _swap(m: re.Match[str], _p: str = phonetic, _s: str = script) -> str:
                nonlocal replaced
                if _letters_as_letters(line, m.start(), _s):
                    return m.group(0)
                # Group 2 is the bare phonetic; the match itself includes the
                # emphasis markers, and using its span put the start OUTSIDE the
                # run it was being tested against — so the guard never fired on
                # a term sitting at the head of a phrase, which is exactly where
                # `La ilaha illa Allah` shreds.
                if _inside_longer_romanization(line, m.start(2), m.end(2)):
                    return m.group(0)
                replaced += 1
                return _s

            # CASE-INSENSITIVE, and safely so: the replacement is Arabic script,
            # which has no case, and the term list is already filtered of English
            # words and absorbed loanwords. `simplify_transliteration` lowercases
            # the glossary's phonetic, so this had to be case-blind or it could
            # never see the page's own `*Natiq*` — which is why sixteen asaas
            # terms carried script in the glossary and still printed romanized.
            line = re.sub(
                # The emphasis markers must BALANCE (`\1`), and a bare match may
                # not sit directly after one. Consuming them asymmetrically turned
                # `*Natiq*'s age` into `اَلنَّاطِق*'s age`: the possessive apostrophe
                # blocked the closing marker, the engine backtracked to consume
                # none, and the opening `*` was stranded mid-sentence.
                rf"(?<![\w*_-])([*_]?)({re.escape(phonetic)})\1(?![\w'’-])",
                _swap,
                line,
                flags=re.IGNORECASE,
            )
        lines[i] = line + nl
    return "".join(lines), replaced


def substitute_text(book_dir: Path, text: str) -> dict[str, Any]:
    """Substitute one passage and report what could not be done. Writes nothing.

    THE COMPOSER BUTTON'S PATH, and deliberately a pure transform rather than a
    file write: the button applies the result to the live editor and lets the
    Composer's own autosave persist it, exactly as the Diacritics action does.
    Writing `book.md` underneath a live editor and then reloading the page is the
    RCA-002 shape, and it is also what made the button feel broken — the page
    bounced and, on a book whose glossary cannot reach the words on screen,
    nothing changed.

    ``unavailable`` is why. It lists the terms the passage sets as foreign that
    this book has NO Arabic for, so "nothing happened" can say so instead of
    looking like a failure. On `al-anwaar-al-lateefah` that is most of the page:
    the glossary holds 27 usable terms and the book italicises about 250, because
    it has no Arabic scan to fill them from.
    """
    from _gloss_terms import bare_term_findings

    terms = substitutable_terms(book_dir)
    new_text, replaced = substitute_body(text, terms)
    entries = []
    glossary = Path(book_dir) / "_system" / "glossary.yml"
    if glossary.exists():
        from _glossary_io import load_glossary

        entries = load_glossary(glossary)[0]
    unavailable = [r["term"] for r in bare_term_findings(new_text, "", entries)]
    return {"text": new_text, "replaced": replaced, "unavailable": unavailable[:12]}


def apply_arabic_substitution(
    book_dir: Path,
    *,
    chapter_key: str | None = None,
    log=lambda _m: None,
) -> int:
    """Substitute across the book, or one chapter when ``chapter_key`` is given.

    Restores each chapter's pre-substitution body first, so a term reclassified
    since the last run gets its English back rather than staying fossilised in
    script. Returns the number of replacements written.
    """
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return 0
    terms = substitutable_terms(book_dir)
    text = book_md.read_text(encoding="utf-8")
    stored = {c.get("chapter_key"): c for c in load_record(book_dir)["chapters"]}
    # An empty term list is NOT an early return when there is something recorded.
    # Restoring is the other half of this pass, and bailing here fossilised the
    # exact case the sidecar exists for: reclassify the last substitutable term
    # to `familiar` and its English would never come back.
    if not terms and not stored:
        log("arabic-substitution: no glossary terms carry script — nothing to substitute")
        return 0
    kept: dict[str, dict[str, Any]] = {}
    out: list[str] = [_HEADING_RE.split(text)[0]]
    total = 0
    touched = 0

    for head, body in _chapters(text):
        key = anchor_key(head)
        prior = stored.get(key)
        if chapter_key is not None and key != chapter_key:
            out.append(head + body)
            if prior:
                kept[key] = prior
            continue

        # Restore before re-deriving — but ONLY when the text on disk is still
        # this pass's own output. A different fingerprint means a human or a
        # later pass has been through it, and their words outrank the fold.
        source = body
        restored = False
        took_back = 0
        if prior and fingerprint(body.strip()) == str(prior.get("after_fingerprint") or ""):
            source = str(prior.get("before_md") or body)
            restored = True
        elif prior:
            # No wholesale restore — a later apparatus step has been through, so
            # the stored body is not this page. The narrow move still works: take
            # back the terms the gate no longer allows, leaving everything those
            # later steps did intact.
            source, took_back = revert_ineligible(
                body, str(prior.get("before_md") or ""), terms, _glossary_terms(book_dir)
            )
            if took_back:
                log(f"arabic-substitution: {took_back} no-longer-eligible term(s) given their English back")

        new_body, n = substitute_body(source, terms)
        if n:
            touched += 1
            total += n
            kept[key] = {
                "chapter_key": key,
                "before_md": source,
                "after_fingerprint": fingerprint(new_body.strip()),
                "replacements": n,
            }
        elif restored:
            # The fold restored English and nothing replaced it — the term was
            # reclassified. Keep the restored text and drop the stale record.
            new_body = source
        elif prior:
            # UNVERIFIED, AND SO KEPT. The text is not this pass's own output, so
            # nothing was restored and nothing was replaced — and dropping the
            # record here deleted `before_md`, the only surviving copy of this
            # chapter's English, permanently. That was the normal path, not an
            # edge case: `after_fingerprint` was stamped at 5a-substitute, and
            # four apparatus steps rewrite the page after it (spelling, bridges,
            # honorifics, the paragraph mirror), so the very next compose read a
            # mismatch and threw the record away. `restamp_from_final_book` below
            # ends the staleness; this keeps the English safe whatever else
            # stales it. A kept record can never restore wrongly — restoration
            # still requires the fingerprint to match.
            kept[key] = prior
        out.append(head + new_body)

    if not total and not any(k in stored for k in kept):
        log("arabic-substitution: nothing to substitute")
    book_md.write_text("".join(out), encoding="utf-8")
    _save_record(book_dir, list(kept.values()))
    log(f"arabic-substitution: {total} romanized term(s) replaced with Arabic script across {touched} chapter(s)")
    return total


def main() -> int:
    """CLI for the Book Composer's "Replace with Arabic" button. Emits JSON.

    Deterministic and fast — no model, no spend — so the route calls it
    IN-REQUEST through `runPythonJson` rather than detaching it the way
    Rearticulate must. One code path with the pipeline step above, so the button
    and the automatic pass can never drift.
    """
    import argparse
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _paths import find_content

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug")
    ap.add_argument("--chapter-key", default="", help="one chapter; omit for the whole book")
    ap.add_argument(
        "--stdin",
        action="store_true",
        help="transform the passage on stdin and print it back; writes no files (the Composer button)",
    )
    args = ap.parse_args()

    found = find_content(args.slug)
    if not found:
        print(json.dumps({"ok": False, "error": f"book not found: {args.slug}"}))
        return 1
    book_dir = found[2]
    if args.stdin:
        print(json.dumps({"ok": True, **substitute_text(book_dir, sys.stdin.read())}, ensure_ascii=False))
        return 0
    notes: list[str] = []
    replaced = apply_arabic_substitution(
        book_dir,
        chapter_key=(args.chapter_key.strip().lower() or None),
        log=notes.append,
    )
    eligible = len(substitutable_terms(book_dir))
    print(json.dumps({"ok": True, "replaced": replaced, "terms": eligible, "notes": notes}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
