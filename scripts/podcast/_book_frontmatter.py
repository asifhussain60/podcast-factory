"""_book_frontmatter.py — the edition's introduction, short and in the book's voice.

WHAT THIS IS, AND WHAT IT REPLACED
----------------------------------
Until 2026-08-03 every Islamic edition opened on 328-460 words a model wrote ABOUT
the book, under an invented literary title (`A Threshold to the Subtle Lights`),
with the SOURCE's own opening demoted beneath it under a machine-written
subheading. A reader met the pipeline's voice before the book's. Asif retired it:
editions begin with the book. `_book_opening` now folds the source's own opening
into chapter 1, where it belongs.

Later the same day Asif asked for the other half back, and asked for it precisely
(2026-08-03): a SHORT introduction, honestly titled, saying what the book is,
what it is about, and who wrote it — "not exceeding a certain number of words",
and written "in the same articulation style as the rest of the books ... it should
not stand out as a different prose". It applies to EVERY PDF route from now on.

THE FOUR THINGS THAT MAKE THIS DIFFERENT FROM WHAT WAS RETIRED
--------------------------------------------------------------
1. HONESTLY TITLED. `## Introduction to the Book`, not a literary title a reader
   could mistake for the author's own. It is apparatus and says so.
2. SHORT. `MAX_INTRO_WORDS` is 250, down from 700. The old cap is why those texts
   read as essays — four of the five ran past 320 words.
3. UNNUMBERED, and this is structural rather than typographic. Every entry in
   `book-toc.json.chapters` carries the source lines it was translated FROM, and
   the crosswalk and gates B5/B6 are built on that mapping. An introduction has no
   source lines because nobody translated it. Numbering it would put a
   source-less section into a structure whose invariant is that every chapter has
   one, and would renumber every chapter, running head and episode map.
4. IN THE BOOK'S VOICE. The register clause is imported from
   `_book_voice_prompts.ARTICULATION_REGISTER` — the SAME text the chapters are
   articulated with, not a second copy of it — and the model is shown a real
   passage of this book's own prose to match. A register defined twice is how the
   introduction drifts into a different voice six months from now.

WHAT IT MAY CLAIM
-----------------
Every fact comes from a file (`meta.yml` doctrinal context, the source's own
attribution line, the resolved narrative frame, the chapter list, the glossary).
The two prohibitions at the top of the brief were earned by real false claims an
audit caught on 2026-07-20: a statement about the edition's own conventions the
artifact did not honour, and a statement that the book withholds something it
states plainly. Both were falsifiable by any reader with the book open.

A book with no recorded author gets an introduction that does not name one. Three
of the five Islamic editions are in that position, and for `al-anwaar-al-lateefah`
it is not a gap but the truth — it was compiled from many sources and has no single
author, which is the same fact that governs its narrative frame.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _book_fences import span_re

INTRO_OPEN = "<!-- edition-intro:begin -->"
INTRO_CLOSE = "<!-- edition-intro:end -->"
INTRO_HEADING = "## Introduction to the Book"

# Matches the bare-marker form as well — see `_book_fences`. An introduction whose
# fence a Composer save flattened must still be found, or the next run stacks a
# second introduction beside the first.
_INTRO_SPAN_RE = span_re("edition-intro", leading=r"\n*", trailing=r"\n*")

# The subheading the RETIRED injector wrote to title the source's opening beneath
# the machine preface. It normally lived inside the fence and leaves with it, but
# `the-master-and-the-disciple` was split by hand before the fence existed, so the
# label can also stand alone. It names a distinction the edition no longer draws.
_OWN_OPENING_HEADING_RE = re.compile(r"(?m)^\s*###\s+The book's own opening\s*$\n?")

_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")
_NUMBERED_HEADING_RE = re.compile(r"^##\s+[0-9٠-٩۰-۹]+\.\s")

# The whole introduction SECTION, heading included, up to the next `## ` or EOF.
# This is the primary strip, and the fence span below is the fallback for books
# still carrying the retired preface.
#
# Section-based rather than fence-based because the heading now sits OUTSIDE the
# fence, and it sits outside for a reason a reader felt immediately: the Composer
# hides any heading inside an `edition-intro` span, so an introduction fenced
# heading-and-all did not appear in the chapter list at all. Asif looked for it
# and it was not there. Stripping by section also survives a save that loses the
# fence markers — without it, the next run would find no fence, strip nothing,
# and inject a SECOND introduction above the first.
_INTRO_SECTION_RE = re.compile(
    r"(?ms)^##[ \t]+Introduction to the Book[ \t]*$.*?(?=^##[ \t]|\Z)",
)

# An introduction is front matter, not an essay. Past this it competes with the
# book for the reader's first attention, which is the one thing it must not do.
MAX_INTRO_WORDS = 250
MIN_INTRO_WORDS = 90

CACHE_NAME = "edition-introduction.md"
_INTRO_TIMEOUT = 900


def strip_introduction(book_md: str) -> str:
    """Remove a previously injected introduction, whitespace normalized.

    Three removals, and THE ORDER IS LOAD-BEARING:

      1. the whole `edition-intro` FENCE, markers included;
      2. then the whole `## Introduction to the Book` SECTION;
      3. then the invented `### The book's own opening` subheading that titled
         the source's opening beneath the retired preface.

    Section-before-fence looks equivalent and is not. Books written this morning
    carry the earlier shape, with the heading INSIDE the fence — so a section
    strip running first removes the heading down to the next `## `, taking the
    fence's CLOSING marker with it and leaving the opening marker stranded above,
    unpairable and therefore permanent. That is what the three finished books
    came back with. Fence first removes the old shape whole; on the current shape
    it takes the prose and step 2 takes the heading. Either way nothing is left.
    """
    out = _INTRO_SPAN_RE.sub("\n\n", book_md)
    out = _INTRO_SECTION_RE.sub("", out)
    return re.sub(r"\n{3,}", "\n\n", _OWN_OPENING_HEADING_RE.sub("", out))


def clear_introduction(book_dir: Path, *, log=print) -> dict[str, Any]:
    """Take the introduction out of ``book/book.md``. Report-shaped.

    Runs BEFORE the opening fold, and that order is load-bearing: the front-matter
    section is what the fold moves into chapter 1, and an introduction still
    inside it would be carried in with the author's words.
    """
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return {"removed": False, "reason": "no book.md"}
    before = book_md.read_text(encoding="utf-8")
    after = strip_introduction(before)
    if after == before:
        return {"removed": False}
    book_md.write_text(after, encoding="utf-8")
    return {"removed": True, "words": len(before.split()) - len(after.split())}


def facts_for_introduction(book_dir: Path) -> dict[str, Any]:
    """Everything an introduction may assert, each item read from a file.

    Returns only what was found. A missing field is omitted rather than guessed,
    and the brief tells the author to write around absences instead of inventing
    them — an introduction that states an attribution the repo does not record is
    the exact failure this module exists to prevent.
    """
    book_dir = Path(book_dir)
    facts: dict[str, Any] = {"slug": book_dir.name}

    meta = book_dir / "meta.yml"
    if meta.exists():
        try:
            import yaml

            data = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
        if isinstance(data, dict):
            facts["title"] = str(data.get("title") or "")
            facts["original_title"] = str(data.get("original_title") or "")
            ctx = data.get("doctrinal_context")
            if isinstance(ctx, dict):
                found = {k: str(v) for k, v in ctx.items() if k in ("author", "school", "period", "genre") and v}
                if found:
                    facts["doctrinal_context"] = found

    # The source's OWN attribution, if it prints one. Stronger evidence than
    # meta.yml, because it is the artifact rather than a note about it.
    source = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if source.exists():
        for line in source.read_text(encoding="utf-8").splitlines()[:12]:
            if re.match(r"^\s*Author\s*:", line, re.I):
                facts["source_attribution_line"] = line.strip()
                break

    try:
        from _pipeline_flags import book_augmentation, book_voice, narrative_frame

        facts["narrative_frame"] = narrative_frame(book_dir)
        facts["book_voice"] = book_voice(book_dir)
        facts["book_augmentation"] = book_augmentation(book_dir)
    except Exception:
        pass

    toc = book_dir / "book" / "book-toc.json"
    if toc.exists():
        try:
            data = json.loads(toc.read_text(encoding="utf-8"))
            facts["chapters"] = [
                {"index": c.get("bk_index") or c.get("index"), "title": c.get("title")}
                for c in data.get("chapters", [])
            ]
        except Exception:
            pass

    glossary = book_dir / "_system" / "glossary.yml"
    if glossary.exists():
        try:
            import yaml

            entries = (yaml.safe_load(glossary.read_text(encoding="utf-8")) or {}).get("entries") or []
            facts["glossary_terms"] = [str(e.get("phonetic")) for e in entries if e.get("phonetic")][:40]
        except Exception:
            pass

    return facts


def style_exemplar(book_dir: Path, *, words: int = 220) -> str:
    """A real passage of THIS book's articulated prose, to match the voice against.

    The register clause says what the voice is; this shows it. Asif's rule is that
    the introduction must not stand out as different prose, and a rule stated in
    the abstract is weaker evidence of a house voice than a page of the house
    voice. Taken from the first numbered chapter, whose text has been through the
    same articulation pass every other chapter has.
    """
    book_md = Path(book_dir) / "book" / "book.md"
    if not book_md.exists():
        return ""
    parts = _HEADING_RE.split(book_md.read_text(encoding="utf-8"))
    for i in range(1, len(parts), 2):
        if not _NUMBERED_HEADING_RE.match(parts[i].strip()):
            continue
        prose = [
            p.strip()
            for p in (parts[i + 1] if i + 1 < len(parts) else "").split("\n\n")
            if p.strip() and not p.lstrip().startswith((">", "#", "<"))
        ]
        return " ".join(" ".join(prose).split()[:words])
    return ""


def gate_introduction(text: str) -> tuple[bool, list[str]]:
    """Refuse the shapes an introduction is never allowed to take.

    Cannot check whether a claim is TRUE — that is the challenger's job, and it
    caught two false ones in a hand-written introduction. What it CAN refuse is
    the wrong size, a missing body, and the one phrasing that produced a false
    claim both times: telling the reader what the book never says. An introduction
    that asserts an absence is asserting something it did not read the whole book
    to verify.
    """
    reasons: list[str] = []
    body = " ".join((text or "").split())
    words = body.split()
    if len(words) < MIN_INTRO_WORDS:
        reasons.append(f"too short to orient anyone ({len(words)}<{MIN_INTRO_WORDS} words)")
    elif len(words) > MAX_INTRO_WORDS:
        reasons.append(f"an introduction is front matter, not an essay ({len(words)}>{MAX_INTRO_WORDS} words)")
    if re.search(r"\b(never says|does not say|nowhere (?:says|states)|fails to (?:say|state)|withholds)\b", body, re.I):
        reasons.append("asserts what the book does NOT say — an absence it cannot have verified")
    if re.search(r"\bas an ai\b|\bI (?:cannot|can't) \b|\bhere is the\b", body, re.I):
        reasons.append("process chatter")
    if re.search(r"(?m)^\s*[-*#]|\bin this introduction\b", body, re.I):
        reasons.append("headings, bullets or throat-clearing")
    return (not reasons), reasons


def introduction_prompt(facts: dict[str, Any], *, exemplar: str = "", draft: str = "") -> str:
    """The brief. Every prohibition in it was earned by a real defect."""
    from _book_voice_prompts import ARTICULATION_REGISTER

    voice = (
        f"\nTHIS BOOK'S OWN VOICE — match it\nThe passage below is real prose from this edition, already articulated. Your\n"
        f"introduction must read as though the same hand wrote it. Do not imitate its\nsubject; imitate its register, "
        f"its sentence rhythm, and its plainness.\n\n{exemplar}\n"
        if exemplar
        else ""
    )
    raw = (
        f"\nRAW MATERIAL — an earlier, longer introduction to this same book\nUse what is accurate in it. It ran well "
        f"past the limit and was written to a different\nbrief, so compress rather than copy, and drop anything the "
        f"FACTS above do not support.\n\n{draft}\n"
        if draft
        else ""
    )
    return f"""You are writing the INTRODUCTION to a reading edition — the editor's own front
matter, not a translation of anything. It is printed under the heading
"Introduction to the Book", before chapter 1.

Your reader is intelligent and knows nothing about this text. In UNDER {MAX_INTRO_WORDS} WORDS they
should learn what it is, what it is about, and who wrote it.

FACTS YOU MAY USE — this list is exhaustive. Every one was read from a file in this book.
{json.dumps(facts, ensure_ascii=False, indent=2)}
{voice}{raw}
ABSOLUTE PROHIBITIONS
1. Do NOT invent an author, a date, a school, a place or a scholarly judgment that is not
   in the FACTS. If no author is recorded, write about the book without naming one — an
   introduction that names an attribution nobody recorded is worse than one that is silent
   about attribution. Some of these books genuinely have no single author.
2. Do NOT describe the edition's conventions unless the facts state them. Claims like "the
   Arabic is left unvowelled wherever the scan is" are checkable by any reader and were
   FALSE the last time an introduction asserted one.
3. Do NOT tell the reader what the book never says, withholds, or fails to state. You have
   not read the whole book; you cannot verify an absence. Say what the book DOES do.
4. Do NOT quote or paraphrase the book's opening. The book begins immediately after you.

WHAT TO COVER, in flowing prose with no headings and no lists
- What kind of text this is and what shape it takes (a dialogue, a treatise, a letter).
- What it is about — the argument or the journey it actually makes, from the chapter list.
- Who wrote it, exactly as strongly as the facts support and no more strongly.
- If two different people would be called by the same name or title in different parts of
  the book, SAY SO. That is the single most useful sentence an introduction can contain.

REGISTER (the Book Articulation Standard, REQ-BA-010, -070..110, -140 — the same
contract every chapter of this book was articulated under)
{ARTICULATION_REGISTER}

OUTPUT
Return ONLY the introduction prose, under {MAX_INTRO_WORDS} words. No title line, no heading, no
preamble, no bullet points, no code fences."""


def author_introduction(book_dir: Path, *, log=print, force: bool = False, author=None) -> str:
    """Author (or reuse) the edition introduction. Returns its text, "" on failure.

    Never raises and never blocks a compose: a book that fails to get an
    introduction is a book missing apparatus, which is the state every book was in
    before this existed. Losing a finished translation over it would be the worse
    trade by far.

    The cache is the idempotency marker AND the cost control — the model is asked
    once per book, ever, unless ``force``.
    """
    book_dir = Path(book_dir)
    cache = book_dir / "_system" / CACHE_NAME
    cached = cache.read_text(encoding="utf-8").strip() if cache.exists() else ""
    if not force and cached and gate_introduction(cached)[0]:
        return cached

    prompt = introduction_prompt(
        facts_for_introduction(book_dir),
        exemplar=style_exemplar(book_dir),
        draft=cached,
    )

    def ask(text_prompt: str, step: str) -> str:
        try:
            if author is not None:
                return (author(text_prompt) or "").strip()
            from _authoring._core import _run_claude_p_with_retry

            rc, out, err = _run_claude_p_with_retry(
                text_prompt,
                timeout=_INTRO_TIMEOUT,
                book_dir=book_dir,
                phase="0book-frontmatter",
                step=step,
                log=log,
            )
            if rc != 0:
                log(f"    front-matter: introduction skipped (claude -p rc={rc}): {str(err)[:120]}")
                return ""
            return (out or "").strip()
        except Exception as e:
            log(f"    front-matter: introduction skipped (non-fatal): {e}")
            return ""

    text = ask(prompt, "edition-introduction")
    ok, reasons = gate_introduction(text)
    if not ok and text:
        # ONE retry, with the ACTUAL findings named — the same shape
        # `_translation_chunk` uses, and for the same reason: a retry that repeats
        # the original brief re-runs the model against instructions it already
        # followed. The first three books written to this brief came back at 256,
        # 262 and 270 words against a 250 limit, which is a trim rather than a
        # rewrite, and refusing outright threw away a good introduction over 2%.
        log(f"    front-matter: introduction rejected — {'; '.join(reasons)} — retrying once")
        text = ask(
            prompt
            + "\n\nYour previous answer failed these checks: "
            + "; ".join(reasons)
            + f". Return the SAME introduction corrected — same facts, same voice, same order — "
            f"cut to under {MAX_INTRO_WORDS} words. Do not restart from a different angle.",
            "edition-introduction-retry",
        )
        ok, reasons = gate_introduction(text)
    if not ok:
        log(f"    front-matter: introduction rejected — {'; '.join(reasons)}")
        return cached if cached and gate_introduction(cached)[0] else ""
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text + "\n", encoding="utf-8")
    log(f"    front-matter: introduction authored ({len(text.split())} words)")
    return text


def inject_introduction(book_md: str, text: str, *, gated: bool = True) -> str:
    """Place the introduction as its own section above the first numbered chapter.

    The heading lives INSIDE the fenced span, so `strip_introduction` takes the
    whole section away. Left outside, a stripped book would keep a bare
    `## Introduction to the Book` with nothing under it.

    Idempotent: strips its own previous output first, so a convergence loop that
    re-enters compose many times never stacks introductions.
    """
    stripped = strip_introduction(book_md)
    if gated and not gate_introduction(text)[0]:
        return stripped
    if not (text or "").strip():
        return stripped
    match = next(
        (m for m in _HEADING_RE.finditer(stripped) if _NUMBERED_HEADING_RE.match(m.group(1).strip())),
        None,
    )
    if match is None:
        return stripped
    head, tail = stripped[: match.start()].rstrip(), stripped[match.start() :]
    # NO FENCE. The introduction is written as an ordinary section, because the
    # fence had exactly one job — telling `strip_introduction` what to remove —
    # and `_INTRO_SECTION_RE` does that from the heading instead.
    #
    # Keeping it cost the reader the thing the fence was supposed to protect. The
    # Composer's editor renders a machine marker as a visible label, and the
    # introduction had never been listed as a chapter before today, so nobody had
    # ever seen its own fence. The moment it became visible, the first line of the
    # book read `edition-intro:begin`.
    #
    # No prose pass can reach this text regardless of markers: the assembly
    # rebuilds book.md without an introduction and every model pass runs before
    # this step, which is the apparatus tail. `INTRO_OPEN`/`INTRO_CLOSE` stay
    # defined, and `strip_introduction` still removes a legacy fence, because five
    # books carried one this morning.
    block = f"{INTRO_HEADING}\n\n{text.strip()}"
    return (head + "\n\n" if head else "") + block + "\n\n" + tail


def apply_introduction(book_dir: Path, *, log=print, force: bool = False, author=None) -> dict[str, Any]:
    """Author and inject in one step. Report-shaped, like the other compose steps."""
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return {"applied": False, "reason": "no book.md"}

    # THE HUMAN'S INTRODUCTION WINS, and nothing here may overwrite it. The
    # Composer is the singular path for anything bound for the PDF, and the
    # introduction is now a section a reader can open there. Without this check
    # the sequence would discard their work in silence every single run: the
    # replay restores their text at step 5a, `clear_introduction` strips it at
    # 5c, and this step writes the cached machine text back at 5e.
    #
    # Not gated, deliberately. The word cap and the shape rules exist to hold a
    # MODEL to a brief; a human who writes three hundred words has decided
    # something, and refusing it would be this pipeline overruling its author.
    from _book_edits import anchor_key, edited_body

    authored = edited_body(book_dir, anchor_key(INTRO_HEADING))
    if authored:
        before = book_md.read_text(encoding="utf-8")
        after = inject_introduction(before, authored, gated=False)
        if after != before:
            book_md.write_text(after, encoding="utf-8")
        log(f"    front-matter: introduction is the author's own ({len(authored.split())} words), not re-written")
        return {"applied": True, "words": len(authored.split()), "authored": True}

    text = author_introduction(book_dir, log=log, force=force, author=author)
    if not text:
        return {"applied": False, "reason": "no introduction"}
    before = book_md.read_text(encoding="utf-8")
    after = inject_introduction(before, text)
    if after != before:
        book_md.write_text(after, encoding="utf-8")
    return {"applied": True, "words": len(text.split())}
