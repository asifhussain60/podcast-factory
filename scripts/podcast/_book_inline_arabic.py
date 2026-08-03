"""_book_inline_arabic.py — put the Arabic script back beside inline terms.

The problem this solves. The composer reads ``_system/source/text/refined-english.md``,
which carries no Arabic at all, so a term the source names in Arabic reaches
``book/book.md`` as bare transliteration — "Bayt al-Mamur" where the book means
البيت المعمور. Block quotations keep their script (they are transcribed from the
OCR ground-truth pages that the compose prompt is given); inline terms had no
such channel. R-ARABIC-SCRIPT-RETAINED says transliteration sits BESIDE the
script, never in place of it, so the edition was quietly breaking the rule its
own preface states.

Why this is deterministic and not a model pass. Every script it writes comes from
the curated ``arabic_script`` field in ``_system/glossary.yml``. Nothing is
recalled, so this cannot fabricate a spelling or invent vowel marks — the failure
mode that ``_book_arabic_audit`` exists to catch. It costs nothing to run.

House style is ``Transliteration (عربي)``, matching ``_narrative.ARABIC_DIRECTIVE``
("keep the script and add the transliteration beside it") and the skip-guard that
``plan-dashboard/src/lib/reader/glossary.ts`` already applies to the same shape.

TWO OPERATIONS, not one (Asif, 2026-08-02). They wear the same shape and were
folded together, which is why one page read ``governance (سِيَاسَة)`` and the next
``governance (siyasa)``:

    CONVERSION   the author already wrote ``(hudud)``. Replacing what is inside
                 that bracket with ``(حُدُود)`` adds no apparatus — the page has
                 exactly as many parentheses afterwards — so it is unconditional
                 and applies to EVERY occurrence. This is the rule "zero English
                 transliteration of Arabic terms in book.md".
    ANNOTATION   the pipeline ADDS a bracket beside a term the prose used
                 plainly. That IS apparatus, so it stays once per book under the
                 annotation policy — the "once and intelligently" rule.

WHICH terms and HOW OFTEN the second is done is governed by the annotation policy
(``_annotation_policy``, per-term ``annotation_class`` in the glossary):

    teach      once IN THE BOOK; where the prose glosses the term the gloss
               becomes ``(باب)`` — script alone, since the script is vowelled by
               ``vowel_glossary`` and the romanisation keeps its home in the
               podcast lane; where the prose uses the term itself the script is
               appended once.
    familiar   never annotated. Mount Sinai, Quran, famous prophets — the
               English form IS the word, and apparatus would talk down.
    name       once in the book, script appended; the romanisation stays
               because it is how an English reader says the name.
    silent     never annotated.
    (no class) legacy behaviour — first occurrence per chapter — so a book
               that predates the policy composes exactly as before.

One rule needs no class: a term is NEVER annotated when its script is already
on the page in an adjacent quotation block. "O children of Adam (آدم)" printed
directly beneath the vowelled verse that contains آدم was the reader seeing the
same script twice in two lines.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from _arabic_coverage import normalize_arabic
from _book_arabic_audit import _HONORIFIC_FORMULAS
from _book_gloss import (
    _convert_glosses,
    _gloss_span,
    _is_person,
    _is_reversed_gloss,
    _script_already_precedes,
)
from _translit import simplify_transliteration

# Name connectors and the article. They are grammatical glue inside a name, never
# a term a reader needs glossed: annotating them split "Jafar ibn Mansur al-Yaman"
# into "Jafar ibn (بن) Mansur…" the first time this ran.
_NAME_PARTICLES = frozenset({"ibn", "bin", "ibn.", "bint", "abu", "abi", "umm", "al", "aal"})

# Arabic letter ranges (presentation forms included) — the same span the audit
# and the site's overlay treat as "this is script, not transliteration".
_ARABIC = r"؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿"

# A line we must not touch: a blockquote (the Arabic quotations already carry
# their own script), a heading, a fenced/HTML block, or a machine fence.
#
# Deliberately NOT "any line containing Arabic". A prose line may already hold an
# inline run — including one this pass added on an earlier run — and skipping
# those made the pass non-idempotent: a second run found the annotated line
# invisible and re-annotated the term at its NEXT mention. Re-annotation is
# prevented by the per-match guard in _annotate_chapter instead, which is exact.
# The transliteration patterns are Latin-only, so they can never match inside an
# Arabic run anyway.
_SKIP_LINE = re.compile(r"^\s*(?:[>#]|```|<|\|)")

# How far past a term to look for its script before deciding this mention is
# already annotated. Wide enough to see past a closing quote, comma or footnote
# marker sitting between the term and its parenthetical.
_ANNOTATED_WINDOW = 12


def _term_re(phonetic: str) -> re.Pattern[str]:
    """Whole-token matcher: not inside a longer word, a hyphenated compound, or
    a possessive — "al-Quran" and "Ghazali's" must not fire."""
    return re.compile(rf"(?<![\w-]){re.escape(phonetic)}(?![\w'’-])")


def _glossary_terms(book_dir: Path) -> list[dict[str, str]]:
    """Annotatable terms with their style, longest phonetic first.

    Each record is ``{"phonetic", "script", "style"}`` where style is one of
    ``teach`` / ``name`` (once per book) or ``legacy`` (no class on the entry —
    once per chapter, the pre-policy behaviour). ``familiar`` and ``silent``
    entries are excluded here outright: they are never annotated, whatever the
    prose does.

    Longest-first so "Bayt al-Mamur" is matched before a bare "Bayt" entry could
    claim its opening word.
    """
    from _annotation_policy import load_policy

    path = Path(book_dir) / "_system" / "glossary.yml"
    if not path.exists():
        return []
    try:
        data: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    entries = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return []
    policy = load_policy(book_dir)

    out: list[dict[str, str]] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        script = str(e.get("arabic_script") or "").strip()
        raw_phonetic = str(e.get("phonetic") or "").strip()
        # The phonetic is normalised the same way the book body was, or a term
        # the body now spells "Bayt al-Mamur" would never match a glossary that
        # still says "Bayt al-Ma'mur".
        phonetic = simplify_transliteration(raw_phonetic)
        if not script or not phonetic or not re.search(rf"[{_ARABIC}]", script):
            continue
        # An honorific formula ("عليه السلام") is the author's liturgical
        # practice attached to a name, not a rendering OF that name — gluing it
        # to the name produced "Isaac (عليهم السلام)". Same set the Arabic audit
        # uses, so the two agree on what counts as a formula.
        if normalize_arabic(script) in _HONORIFIC_FORMULAS:
            continue
        # A lone honorific letter ("ع" for عليه السلام) is the same thing
        # abbreviated; it is never a term's script.
        if len(script.strip()) <= 2:
            continue
        if phonetic.lower() in _NAME_PARTICLES:
            continue
        cls = (policy.get(raw_phonetic) or policy.get(phonetic) or {}).get("class", "")
        # familiar/silent terms are carried with style "none": they are never
        # ANNOTATED, but the strip pass still needs their scripts so an
        # annotation added before the term was classified is removed rather
        # than fossilised.
        style = cls if cls in ("teach", "name", "familiar", "silent") else "legacy"
        if style in ("familiar", "silent"):
            style = "none"
        out.append({"phonetic": phonetic, "script": script, "style": style})
    out.sort(key=lambda t: len(t["phonetic"]), reverse=True)
    return out


def _script_already_near(line: str, at: int, script: str) -> bool:
    """Is this concept already carrying script in the immediate vicinity?

    Containment both ways, because the glossary holds overlapping entries: the
    bare "Imam" (\u0627\u0644\u0625\u0645\u0627\u0645) sits inside "al-Imam al-Natiq"
    (\u0627\u0644\u0625\u0645\u0627\u0645 \u0627\u0644\u0646\u0627\u0637\u0642), and annotating both
    printed the same idea twice in one breath.

    Compared by CONSONANTAL SKELETON, like `_script_in_adjacent_block` beside it.
    Byte containment was the same check with a hole in it: the book's own
    vowelling of a run is rarely the glossary's, so `\u0639\u064f\u0628\u064e\u064a\u0652\u062f\u064f \u0627\u0644\u0644\u064e\u0651\u0647\u0650` standing in
    the prose did not contain and was not contained by `\u0639\u064f\u0628\u064e\u064a\u0652\u062f\u064f \u0627\u0644\u0644\u0651\u0670\u0647` from
    `glossary.yml`, and the pass annotated a term whose script was already three
    characters away \u2014 printing `Ubayd Allah (\u0639\u064f\u0628\u064e\u064a\u0652\u062f\u064f \u0627\u0644\u0644\u0651\u0670\u0647) (\u0639\u064f\u0628\u064e\u064a\u0652\u062f\u064f \u0627\u0644\u0644\u064e\u0651\u0647\u0650,
    'little servant of Allah')`, the same name in Arabic twice in one breath, with
    the author's own translation stranded after the duplicate. The skeleton is the
    right key for the same reason it is in `_normalize_annotations`: vowelling may
    add marks, never change letters.
    """
    window = line[at : at + len(script) + _ANNOTATED_WINDOW + 24]
    needle = normalize_arabic(script)
    if not needle:
        return False
    for run in re.findall(rf"[{_ARABIC}][^()]*", window):
        run = normalize_arabic(run.strip())
        if run and (run in needle or needle in run):
            return True
    return False


def _normalize_annotations(body: str, terms: list[dict[str, str]]) -> str:
    """Fold every machine annotation back to its pre-annotation shape.

    Annotations are DERIVED state — a function of (prose, glossary, policy) — so
    each run undoes its own previous output and re-derives. Without this the pass
    could only ever ADD: a term reclassified as familiar kept the annotation it
    was given before the policy existed, fossilised in the prose forever.

    A blind strip is NOT the inverse operation, because the two machine shapes
    encode different history:

      appended    `Allah (الله)` — the term is in the running prose, the paren
                  was added after it. Inverse: remove the paren.
      gloss site  `his gate (باب)` / `his gate (bab, باب)` — the paren REPLACED
                  the author's own romanisation gloss `(*bab*)`. Inverse:
                  restore the SEED, because deleting it would delete the
                  author's gloss and with it the only anchor a re-derivation
                  can annotate.

    The two are told apart by what precedes the paren: the term itself (allowing
    a quote or emphasis between) means appended. Only exact machine shapes on
    prose lines are touched.
    """
    # Grouped BY SCRIPT, not by term: two glossary entries may share one script
    # (this book carries both "Sinai" and "Tur" for الطور), and judging the same
    # paren once per term let the second entry re-interpret an annotation the
    # first had already explained — manufacturing a spurious gloss seed beside
    # it on every run.
    # Keyed on the CONSONANTAL SKELETON, not the exact script (2026-08-02).
    #
    # This matched `script` byte for byte, which made an annotation
    # unrecognisable to its own inverse the moment the glossary's `arabic_script`
    # changed — most commonly when `5a-glossary-vowel` added tashkeel to a term
    # already annotated bare. The old paren was then neither removed nor
    # reseeded, and the pass wrote a SECOND one beside it: the measured
    # `Tur (اَلطُّور), الطور)`.
    #
    # Script-only glosses make that failure worse rather than merely untidy.
    # Under the old `(aql, العقل)` form the romanisation was still in the paren,
    # so a human could see what the annotation had been. Strip it and a stale
    # `(العقل)` beside a fresh `(الْعَقْل)` says nothing about which term it
    # belonged to — an orphan no gate can attribute.
    #
    # The skeleton is safe to key on because `_vowelling.rejection_reason`
    # guarantees a vowelling never alters it: marks may be added, letters may
    # not. That turns the 5a-glossary-vowel -> 5a-arabic ordering from a
    # correctness constraint into a mere convention.
    by_skeleton: dict[str, list[dict[str, str]]] = {}
    for t in terms:
        by_skeleton.setdefault(normalize_arabic(t["script"]), []).append(t)

    lines = body.split("\n")
    for i, line in enumerate(lines):
        if not line.strip() or _SKIP_LINE.search(line):
            continue
        for t in terms:
            # Named-gloss form first — it carries the phonetic, so it can only
            # ever have been a gloss site. Retained for books composed before the
            # script-only rule, whose prose still holds `(bab, باب)`.
            #
            # Matched by SKELETON, not by an exact string. This was
            # `line.replace(f"({phonetic}, {script})", …)`, which requires the
            # prose's vowelling of the run to equal the glossary's byte for byte —
            # and it usually does not, because the two were marked by different
            # passes at different times. So the fold hit 7 of the 13 retired
            # brackets in `the-master-and-the-disciple` and left `(Tur, اَلطُّور)`,
            # `(duat, الدُّعَاة)`, `(natiq, اَلنَّاطِق)` and three more printing the
            # romanisation the 2026-08-02 rule retired. Third instance of the same
            # root cause in this module, with `_script_already_near` and
            # `_normalize_annotations` below — vowelling may add marks, never
            # change letters, so the skeleton is the only safe key.
            needle = normalize_arabic(t["script"])
            if needle:
                pat = re.compile(rf"\(\s*{re.escape(t['phonetic'])}\s*,\s*([^()\n]*[{_ARABIC}][^()\n]*?)\s*\)")

                def _fold(m: re.Match[str], _t: dict[str, str] = t, _n: str = needle) -> str:
                    return f"(*{_t['phonetic']}*)" if normalize_arabic(m.group(1)) == _n else m.group(0)

                line = pat.sub(_fold, line)
        # Any paren holding ONLY an Arabic run is a candidate; which term it
        # belonged to is decided by its skeleton.
        for m in reversed(list(re.finditer(r"\s?\(([^()]*[؀-ۿ][^()]*)\)", line))):
            inner = m.group(1)
            # ONLY-an-Arabic-run has to be enforced, not just intended.
            # `normalize_arabic` DISCARDS every non-Arabic character, so a bracket
            # the author wrote as script-plus-translation —
            # `Ubayd Allah (عُبَيْدُ اللَّهِ, 'little servant of Allah')` — reduced to
            # the same skeleton as the bare script and was claimed as this pass's
            # own output. Rewriting it then deleted the English, in a sentence
            # whose entire subject is what the two names MEAN. The machine only
            # ever writes `(script)`, so a bracket carrying Latin words is by
            # construction not the machine's, and the one machine shape that does
            # carry Latin — the retired `(bab, باب)` — is handled by the exact
            # string replace above, before this loop ever sees the line.
            if re.search(r"[A-Za-z]", inner):
                continue
            sharers = by_skeleton.get(normalize_arabic(inner))
            if not sharers:
                continue  # not ours — a source's own Arabic, or another pass's
            before = line[max(0, m.start() - _ANNOTATED_WINDOW - 40) : m.start()]
            if any(re.search(rf"(?<![\w-]){re.escape(t['phonetic'])}['\"”’)\]*_\s]*$", before) for t in sharers):
                line = line[: m.start()] + line[m.end() :]  # appended — remove
            else:
                # A gloss site. Reseed with the longest sharer's phonetic —
                # `terms` is longest-first, so sharers[0] is deterministic.
                line = line[: m.start()] + f" (*{sharers[0]['phonetic']}*)" + line[m.end() :]
        lines[i] = line
    return "\n".join(lines)


def _script_in_adjacent_block(lines: list[str], i: int, script: str, *, reach: int = 3) -> bool:
    """Is this term's script already on the page in a nearby quotation block?

    The translation line under a vowelled Quranic block is the archetype: "O
    children of Adam (آدم)" printed two lines beneath a verse that spells آدم in
    full. The reader is looking at the script already; annotating the
    translation shows it to them twice. Compared by consonantal skeleton so the
    block's vowelling cannot hide the match.
    """
    needle = normalize_arabic(script)
    if not needle:
        return False
    for j in range(max(0, i - reach), min(len(lines), i + reach + 1)):
        if j == i or not lines[j].lstrip().startswith(">"):
            continue
        if needle in normalize_arabic(lines[j]):
            return True
    return False


def _annotate_chapter(body: str, terms: list[dict[str, str]], pending: dict[str, dict[str, str]]) -> tuple[str, int]:
    """Annotate the first prose mention of each still-pending term in one chapter.

    ``pending`` is OWNED BY THE CALLER: once-per-book terms stay consumed across
    chapters, once-per-chapter (legacy) terms are re-armed by the caller before
    each chapter. Consumption is the same act either way — deleting the term
    from the dict.

    All matching happens against the ORIGINAL line and insertions are applied
    right-to-left at the end, so no offset ever shifts under a later match. A
    match overlapping a term already claimed on that line is skipped: without
    that, the short entry "ibn" fired inside the long entry
    "Jafar ibn Mansur al-Yaman" and split a proper name in half.
    """
    lines = body.split("\n")
    added = 0
    converted = 0

    for i, line in enumerate(lines):
        if not line.strip() or _SKIP_LINE.search(line):
            continue
        # NOTE the `pending` guard is NOT here. It used to be, and it made
        # conversion impossible past the first mention: once every term had been
        # consumed the dict was empty and every remaining line was skipped whole,
        # so a second `(siyasa)` three chapters later was never even looked at.
        # Conversion is unconditional; only the ANNOTATION half below is rationed.
        line, n = _convert_glosses(line, terms, pending)
        lines[i] = line
        converted += n
        if not pending:
            continue
        # Reserve the span of EVERY glossary term present on this line, whether
        # or not it is still pending. Reserving only pending terms was not
        # enough: once "Abd Allah" had been annotated in an earlier line it left
        # `pending`, so on a later line the standalone "Allah" entry matched the
        # Allah INSIDE "son of Abd Allah" and printed "Abd Allah (الله)" — one
        # name carrying two different scripts in the same chapter.
        claimed: list[tuple[int, int]] = []
        for t in terms:
            for m in _term_re(t["phonetic"]).finditer(line):
                if not any(s < m.end() and m.start() < e for s, e in claimed):
                    claimed.append((m.start(), m.end()))
        reserved = list(claimed)

        edits: list[tuple[int, int, str]] = []
        queued: list[tuple[int, str]] = []  # (position, script) already decided
        # `terms` is longest-phonetic-first, so a compound name claims its span
        # before any of its component words can.
        for t in terms:
            phonetic, script, style = t["phonetic"], t["script"], t["style"]
            if phonetic not in pending:
                continue
            # A term may only annotate at a span reserved for ITSELF — that is,
            # one whose extent matches this term exactly. A span belonging to a
            # longer name is off limits even though the shorter term matches
            # inside it.
            m = next(
                (
                    m
                    for m in _term_re(phonetic).finditer(line)
                    if (m.start(), m.end()) in reserved
                    and not any(s < m.end() and m.start() < e for s, e in claimed if (s, e) != (m.start(), m.end()))
                ),
                None,
            )
            if not m:
                continue
            claimed.append((m.start(), m.end()))
            # Idempotent: if this mention already carries its script, claim the
            # term and leave the text alone. The window is deliberately loose —
            # the approved base wrote one as `"Kab al-Ahbar (كعب الأحبار)"` with
            # the closing quote BETWEEN the term and its parenthetical, which a
            # strict `\s*\(` check walked straight past, producing the script
            # twice eight characters apart.
            # The line still holds its ORIGINAL text while we decide, so a script
            # queued earlier in this pass is invisible to a text scan. Check both.
            near_queued = any(
                abs(pos - m.end()) < _ANNOTATED_WINDOW + 40 and (q in script or script in q) for pos, q in queued
            )
            if near_queued or _script_already_near(line, m.end(), script):
                del pending[phonetic]
                continue

            # The reader is already looking at this script in a quotation block
            # beside this line — the introduction has happened, on the page,
            # in the source's own words. Consumed, not deferred: deferring
            # would annotate the term's NEXT mention, pages from the script.
            if _script_in_adjacent_block(lines, i, script):
                del pending[phonetic]
                continue

            # Walk past any emphasis closing the term. Landing inside it put the
            # Arabic in an <em>, where a browser synthesizes a slant — a thing
            # Arabic script does not have.
            at = m.end()
            while at < len(line) and line[at] in "*_":
                at += 1

            # THE GLOSS RULE. Where the book already glosses the term with its
            # transliteration — the author's own convention, `his gate (*bab*)`
            # — the annotation REPLACES that gloss rather than nesting inside it
            # (nesting produced `his gate (*bab* (باب))`). What replaces it
            # depends on the class:
            #
            #   every class  `(باب)` — SCRIPT ONLY.
            #
            # Script only, since 2026-08-02 (Asif): "there should be zero English
            # transliteration of Arabic terms, words, paragraphs, sentences, etc.
            # in book.md. All Arabic should be in the Arabic script, not in the
            # English character set." The `teach` class used to keep the
            # romanisation beside the script — `(bab, باب)` — on the reasoning
            # that a reader without Arabic must still be able to say the word.
            # That reasoning is retired: the Arabic on this page is always
            # vowelled (`vowel_book.py`, step 5a-vowelling), which is what makes
            # it readable to the person the edition is printed for, and the
            # romanization has a home in the podcast lane where pronunciation is
            # the whole point. `chapters/*.txt` is untouched by this.
            #
            # A personal name never gloss-replaces: its transliteration is the
            # running prose, so the script is appended beside it.
            gloss = None if style == "name" or _is_person(phonetic) else _gloss_span(line, m.start(), m.end())
            # The reversed shape reaches HERE too, by its own route: `_term_re`
            # finds `pole` INSIDE `(pole)` and `_gloss_span` correctly reports a
            # gloss bracket — it just cannot know the bracket holds the English.
            # `_convert_glosses` guards its own path; this one needs the same
            # guard or `*Qutb* (pole)` still loses its translation.
            if gloss and _is_reversed_gloss(line, gloss[0], {x["phonetic"] for x in terms}):
                continue
            # And the letters-as-letters shape reaches here by the same route, for
            # the same reason: `كُن (Kun)` is a gloss bracket by structure, and
            # only the script already standing in front of it says the bracket is
            # a pronunciation rather than a romanisation to be replaced.
            if gloss and _script_already_precedes(line, gloss[0], script):
                continue
            if gloss:
                inner = f" ({script})"
                edits.append((gloss[0], gloss[1], inner))
                queued.append((gloss[0], script))
                del pending[phonetic]
                added += 1
                continue

            edits.append((at, at, f" ({script})"))
            queued.append((at, script))
            del pending[phonetic]
            added += 1
        # Right-to-left so no earlier offset shifts under a later edit.
        for start, end, text in sorted(edits, reverse=True):
            lines[i] = lines[i][:start] + text + lines[i][end:]

    return "\n".join(lines), added + converted


def apply_inline_arabic(book_dir: Path, *, log=lambda _m: None) -> int:
    """Rewrite ``book/book.md`` in place. Returns the number of terms annotated.

    Safe to run repeatedly: a term already carrying its script is left alone.
    """
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return 0
    terms = _glossary_terms(book_dir)
    if not terms:
        log("inline-arabic: no glossary terms with Arabic script — skipped")
        return 0

    original = book_md.read_text(encoding="utf-8")
    # Derived state: fold every machine annotation back to its pre-annotation
    # shape, then re-derive under the current policy. This is what lets a
    # classification CHANGE the page — a term reclassified familiar loses the
    # annotation it had, a teach term's repeats collapse to its first use —
    # instead of only ever adding.
    text = _normalize_annotations(original, terms)

    # Two scopes of "first occurrence", one pending dict. Classified terms
    # (teach/name) are armed ONCE and stay consumed across every chapter — the
    # convention is introduced once in the copy the reader holds. Legacy terms
    # (no class yet) are re-armed at each chapter boundary, exactly the
    # pre-policy behaviour, so an unclassified book composes unchanged.
    book_scoped = {t["phonetic"]: t for t in terms if t["style"] in ("teach", "name")}
    chapter_scoped = {t["phonetic"]: t for t in terms if t["style"] == "legacy"}
    pending: dict[str, dict[str, str]] = dict(book_scoped)

    parts = re.split(r"(?m)^(##\s+.+)$", text)
    rebuilt: list[str] = [parts[0]]
    total = 0
    if parts[0].strip():
        pending.update(chapter_scoped)
        annotated, n = _annotate_chapter(parts[0], terms, pending)
        rebuilt[0] = annotated
        total += n
    for i in range(1, len(parts), 2):
        heading = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        # Re-arm ONLY the chapter-scoped terms; a consumed book-scoped term is
        # deliberately absent — that is what "once" means.
        for phonetic, t in chapter_scoped.items():
            pending[phonetic] = t
        annotated, n = _annotate_chapter(body, terms, pending)
        total += n
        rebuilt.append(heading)
        rebuilt.append(annotated)

    new_text = "".join(rebuilt)
    if new_text != original:
        book_md.write_text(new_text, encoding="utf-8")
    log(f"inline-arabic: annotated {total} term mention(s)")
    return total
