"""_book_frontmatter.py — the edition's introduction, as apparatus not translation.

Front matter is TWO things and the pipeline conflated them:

  the source's own opening   content. Whatever the work itself says first — a
                             dedication, a question that prompted it, a doxology.
                             It is translated, faithfully, like every other page.
  the edition's introduction apparatus. Who wrote this, what kind of text it is,
                             who is speaking in it, what its technical vocabulary
                             is doing. The source cannot supply this; only an
                             editor can.

Both routes ran the source's opening through the faithful composer and called the
result a preface. `_book_compose` even instructs it to "orient today's reader to
the work that follows: who is speaking, to whom, and why it still matters" — and
then hands that instruction to a translator bound by fidelity rules, which can
only render the source it was given. `the-master-and-the-disciple` shipped a
preface a reader finished knowing about the three thanks and nothing about the
book, and the sharpest cost was invisible: its opening addresses "a Master among
them", the frame teacher, while every page after chapter 3 calls the Persian
convert "the Master". A reader carrying the first one forward was quietly wrong
for a hundred pages.

So this module authors the introduction SEPARATELY, from the book's own recorded
facts, and the source's opening keeps its place beneath it. Nothing is reordered
and nothing is demoted to an appendix — a source's first words teach, and burying
them costs a reader something real.

WHAT IT MAY CLAIM
-----------------
Every fact handed to the model comes from a file (`meta.yml` doctrinal context,
the source's own attribution line, the resolved narrative frame, the chapter list,
the glossary's technical terms, the route knobs). The brief forbids the two
failure modes an audit caught in a hand-written introduction on 2026-07-20: a
claim about the edition's own conventions that the artifact does not honour ("left
unvowelled wherever the scan leaves it unvowelled" was false of nine runs), and a
claim that the book withholds something it in fact states plainly. Both were
falsifiable by any reader with the book open, which is the worst place to be
wrong.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

INTRO_OPEN = "<!-- edition-intro:begin -->"
INTRO_CLOSE = "<!-- edition-intro:end -->"
_INTRO_SPAN_RE = re.compile(r"\n*" + re.escape(INTRO_OPEN) + r".*?" + re.escape(INTRO_CLOSE) + r"\n*", re.S)
_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")

# An introduction is front matter, not an essay. Past this it competes with the
# book for the reader's first attention, which is the one thing it must not do.
_MAX_INTRO_WORDS = 700
_MIN_INTRO_WORDS = 120


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
                facts["doctrinal_context"] = {
                    k: str(v) for k, v in ctx.items() if k in ("author", "school", "period", "genre")
                }

    # The source's OWN attribution, if it prints one. Stronger evidence than
    # meta.yml, because it is the artifact rather than a note about it.
    source = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if source.exists():
        head = source.read_text(encoding="utf-8").splitlines()[:12]
        for line in head:
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


def gate_introduction(text: str) -> tuple[bool, list[str]]:
    """Refuse the shapes an introduction is never allowed to take.

    Cannot check whether a claim is TRUE — that is the challenger's job, and it
    caught two false ones in a hand-written introduction. What it can refuse is
    the wrong size, a missing body, and the one phrasing that produced a false
    claim both times: telling the reader what the book never says. An
    introduction that asserts an absence is asserting something it did not read
    the whole book to verify.
    """
    reasons: list[str] = []
    body = " ".join((text or "").split())
    words = body.split()
    if len(words) < _MIN_INTRO_WORDS:
        reasons.append(f"too short to orient anyone ({len(words)}<{_MIN_INTRO_WORDS} words)")
    elif len(words) > _MAX_INTRO_WORDS:
        reasons.append(f"an introduction is front matter, not an essay ({len(words)}>{_MAX_INTRO_WORDS} words)")
    if re.search(r"\b(never says|does not say|nowhere (?:says|states)|fails to (?:say|state)|withholds)\b", body, re.I):
        reasons.append("asserts what the book does NOT say — an absence it cannot have verified")
    if re.search(r"\bas an ai\b|\bI (?:cannot|can't) \b|\bhere is the\b", body, re.I):
        reasons.append("process chatter")
    return (not reasons), reasons


def strip_introduction(book_md: str) -> str:
    """Remove a previously injected introduction, whitespace normalized."""
    return _INTRO_SPAN_RE.sub("\n\n", book_md)


def format_introduction(text: str, *, source_opening_heading: str = "The book's own opening") -> str:
    """Fence the introduction and title what follows it.

    The subheading is what keeps the source's opening from reading as more
    introduction — it stays in place, directly beneath, clearly labelled as the
    book's own words rather than the edition's.
    """
    body = (text or "").strip()
    return f"{INTRO_OPEN}\n{body}\n\n### {source_opening_heading}\n{INTRO_CLOSE}"


def inject_introduction(book_md: str, text: str) -> str:
    """Place the introduction at the top of the first ``##`` section's body.

    Idempotent: strips its own previous output first, so a convergence loop that
    re-enters compose many times never stacks introductions. Returns the markdown
    unchanged when there is no section to place it in.
    """
    stripped = strip_introduction(book_md)
    ok, _ = gate_introduction(text)
    if not ok:
        return stripped
    match = _HEADING_RE.search(stripped)
    if not match:
        return stripped
    cut = stripped.find("\n", match.end())
    if cut == -1:
        return stripped
    head, tail = stripped[:cut], stripped[cut:].lstrip("\n")
    return head + "\n\n" + format_introduction(text) + ("\n\n" + tail if tail else "\n")


_INTRO_TIMEOUT = 900
CACHE_NAME = "edition-introduction.md"


def introduction_prompt(facts: dict[str, Any]) -> str:
    """The brief. Every prohibition in it was earned by a real defect.

    The two "do not" rules at the top are the false claims an audit caught in a
    hand-written introduction for `the-master-and-the-disciple`: a statement about
    the edition's own conventions that the artifact did not honour, and a
    statement that the book withholds something it states plainly in the very
    chapter the sentence pointed at. Both were falsifiable by any reader with the
    book open.
    """
    return f"""You are writing the INTRODUCTION to a reading edition — the editor's own front
matter, not a translation of anything. The source's own opening follows directly beneath what you
write and is already translated; do not paraphrase, summarize or quote it.

Your reader is intelligent and knows nothing about this text. In a few hundred words they should
learn what it is, who wrote it, who speaks in it, and what to watch for in its vocabulary.

FACTS YOU MAY USE — this list is exhaustive. Every one was read from a file in this book.
{json.dumps(facts, ensure_ascii=False, indent=2)}

ABSOLUTE PROHIBITIONS
1. Do NOT describe the edition's conventions unless the facts above state them. Claims like "the
   Arabic is left unvowelled wherever the scan is" are checkable by any reader and were FALSE the
   last time an introduction asserted one.
2. Do NOT tell the reader what the book never says, withholds, or fails to state. You have not read
   the whole book; you cannot verify an absence. Say what the book DOES do.
3. Do NOT invent an author, a date, a school, a place or a scholarly judgment that is not above. If
   a fact is missing, write around it — an introduction that names an attribution nobody recorded is
   worse than one that does not mention attribution.
4. Do NOT quote the source's opening. It is printed immediately below you.

WHAT TO COVER, in flowing prose with no headings and no lists
- What kind of text this is, and what its shape is (a dialogue, a treatise, a commentary).
- Its attribution and tradition, exactly as strongly as the facts support and no more strongly. If
  the attribution comes from the manuscript itself, say so in those terms.
- How it narrates: the narrative frame above governs whether a first person belongs to a speaker or
  to a narrator. A reader who mistakes one for the other misreads the book.
- Who the figures are, from the chapter list. If two different people would be called by the same
  name or title in different parts of the book, SAY SO — that is the single most useful sentence an
  introduction can contain.
- What the recurring technical terms are doing, if the glossary shows a cluster of them.

STYLE
Contemporary, plain, unhurried. No throat-clearing, no "in this introduction", no headings, no
bullet points, no invitation to enjoy the book. Between 200 and 500 words.

OUTPUT
Return ONLY the introduction prose. No title line, no preamble, no code fences."""


def author_introduction(book_dir: Path, *, log=print, force: bool = False, author=None) -> str:
    """Author (or reuse) the edition introduction. Returns its text, "" on failure.

    Never raises and never blocks a compose: a book that fails to get an
    introduction is a book missing apparatus, which is the state every book was in
    before this existed. Losing a finished translation over it would be the worse
    trade by far.
    """
    book_dir = Path(book_dir)
    cache = book_dir / "_system" / CACHE_NAME
    if not force and cache.exists():
        cached = cache.read_text(encoding="utf-8").strip()
        if gate_introduction(cached)[0]:
            return cached

    facts = facts_for_introduction(book_dir)
    prompt = introduction_prompt(facts)
    try:
        if author is not None:
            text = author(prompt)
        else:
            from _authoring._core import _run_claude_p_with_retry

            rc, out, err = _run_claude_p_with_retry(
                prompt,
                timeout=_INTRO_TIMEOUT,
                book_dir=book_dir,
                phase="0book-frontmatter",
                step="edition-introduction",
                log=log,
            )
            if rc != 0:
                log(f"    front-matter: introduction skipped (claude -p rc={rc}): {str(err)[:120]}")
                return ""
            text = out
    except Exception as e:
        log(f"    front-matter: introduction skipped (non-fatal): {e}")
        return ""

    text = (text or "").strip()
    ok, reasons = gate_introduction(text)
    if not ok:
        log(f"    front-matter: introduction rejected — {'; '.join(reasons)}")
        return ""
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text + "\n", encoding="utf-8")
    log(f"    front-matter: introduction authored ({len(text.split())} words)")
    return text


def apply_introduction(book_dir: Path, *, log=print, force: bool = False, author=None) -> dict[str, Any]:
    """Author and inject in one step. Report-shaped, like the other compose steps."""
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return {"applied": False, "reason": "no book.md"}
    before = book_md.read_text(encoding="utf-8")
    # Already split by hand. `the-master-and-the-disciple` was given its
    # introduction manually before this step existed, stored as a Composer edit
    # and replayed on every compose — so authoring another one would print two,
    # one of them a stranger's. The marker is the subheading the split creates:
    # if the front matter already names the source's own opening, the human's
    # version stands and this step leaves it alone.
    if INTRO_OPEN not in before and re.search(r"(?m)^###\s+The book's own opening\s*$", before):
        return {"applied": False, "reason": "front matter already split by hand"}
    text = author_introduction(book_dir, log=log, force=force, author=author)
    if not text:
        return {"applied": False, "reason": "no introduction"}
    after = inject_introduction(before, text)
    if after != before:
        book_md.write_text(after, encoding="utf-8")
    return {"applied": True, "words": len(text.split())}
