"""_book_comprehension.py — can a reader actually follow this book?

The book lane already has two reviewers and neither asks the reader's question.
The semantic challenger judges the book against its SOURCE — nothing lost, nothing
added, Arabic intact, voice steady. The render challenger judges the printed page
— no blank pages, no split figures. Both can pass a book that is faithful,
beautifully set, and quietly impossible to follow.

This module is the deterministic backbone of the third reviewer. It reads the
FINISHED PDF, as a reader receives it, and measures the things that do not need
judgment:

  * PREREQUISITE GAPS — a term the book leans on pages before it explains it. This
    is the central defect in a faithful edition: the source's order is preserved by
    design, and the source was written for readers who already had the vocabulary.
    Found by comparing each term's first USE against its first EXPLANATION.
  * NAMING DRIFT — the same term spelled two ways across the book, which makes one
    idea read as two.
  * DENSITY — sentence and paragraph length, and how many unexplained terms land in
    a single page, so a reviewer can point at the passages that are hardest rather
    than assert that some exist.

The fix it enables is a BRIDGE, never a reorder: a sentence of orientation where
the term first lands. Faithful order is the thing the rest of the pipeline works
hardest to protect, and no readability finding is worth breaking it.

Pure and deterministic — no LLM, no network, no mutation. The agent that consumes
this supplies the judgment; this supplies the evidence.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from _book_render_checks import _extract_pages_text
from _translit import simplify_transliteration

# A term counts as EXPLAINED when it appears within this many characters of a
# defining cue. Generous, because an author explains in a clause, not a formula.
_DEFINITION_WINDOW = 160
# A "name was X" reveal explains by preceding the term, not following it. This
# window is deliberately short — the same clause, not the same paragraph — so it
# cannot pick up an unrelated cue from the prior sentence the way the old
# unbounded ±160 window did (the exact bug this module was built to avoid).
_NAME_REVEAL_WINDOW = 30
# Cues that mark prose as explaining rather than merely using a term. Deliberately
# ordinary language — an authored book defines by apposition, not by "X is defined
# as Y". The em dash and comma-apposition cases are handled by the window alone.
_DEFINITION_CUES = (
    "means",
    "meaning",
    "is the",
    "are the",
    "is a",
    "are a",
    "refers to",
    "called",
    "known as",
    "that is",
    "in other words",
    "the word",
    "the term",
    "literally",
    "root",
    "name was",  # a character reveal ("the boy's name was Salih") IS an explanation
    "named",
)
# Below this many uses a term is incidental — a proper name mentioned once needs no
# explanation, and flagging it would bury the real gaps.
_MIN_USES_TO_MATTER = 3
# A gap only matters when the reader has to carry the term for a while. One page is
# an author explaining a beat later; several pages is a reader lost.
_MIN_PAGE_GAP = 2
# Readability proxies. Not verdicts — the passages a reviewer should look at first.
_LONG_SENTENCE_WORDS = 45
_DENSE_PAGE_TERMS = 6


def _normalize(text: str) -> str:
    """Lower-cased, whitespace-flat, and folded to PLAIN transliteration.

    The fold is what makes the comparison work at all: the glossary stores
    scholarly diacritics (``nāṭiq``, ``ḥujaj``) while the printed book carries
    plain transliteration (``natiq``, ``hujaj``) by rule. Without folding both
    sides through the same normalizer the book's real concepts match NOTHING and
    the reviewer silently reports on character names instead.
    """
    flat = " ".join((text or "").replace("­", "").split())
    return simplify_transliteration(flat).lower()


def glossary_terms(book_dir: Path) -> list[str]:
    """The book's own vocabulary — the terms a reader is expected to acquire.

    Sourced from the generated glossary, which already holds every Arabic-derived
    term the book teaches. Terms are what this reviewer tracks; ordinary English
    needs no first-use analysis.
    """
    path = Path(book_dir) / "_system" / "glossary.yml"
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    terms: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        term = str(entry.get("phonetic") or "").strip()
        if _is_concept(term):
            terms.append(term)
    return terms


# Name particles and honorifics are not concepts. Tracked, they crowd out the real
# gaps: "ibn" appears on page 1 and is "never explained" because there is nothing
# to explain. A reader acquires ideas, not the connective tissue of Arabic names.
_NOT_CONCEPTS = frozenset(
    {"ibn", "bin", "abu", "abi", "umm", "banu", "bani", "al", "allah", "quran", "qur'an", "islam", "muslim"}
)


def _is_concept(term: str) -> bool:
    """True when a glossary entry is an idea a reader must acquire, not a name.

    A multi-word entry is a person or a place ("Ja'far ibn Mansur al-Yaman"); a
    particle is grammar. What remains is the book's actual vocabulary.
    """
    term = (term or "").strip()
    if len(term) < 3 or " " in term:
        return False
    return _normalize(term) not in _NOT_CONCEPTS


def _term_pattern(term: str) -> re.Pattern[str]:
    return re.compile(r"\b" + re.escape(_normalize(term)) + r"\b")


def term_pages(pages: list[str], term: str) -> list[int]:
    """1-indexed pages where the term appears."""
    pattern = _term_pattern(term)
    return [i for i, page in enumerate(pages, start=1) if pattern.search(_normalize(page))]


def explanation_page(pages: list[str], term: str) -> int | None:
    """The first page that EXPLAINS the term, or None if the book never does.

    Explanation is proximity to a defining cue, not a grammatical form — an
    authored book says "the Natiq, the speaking prophet of an age", never "Natiq is
    defined as".
    """
    pattern = _term_pattern(term)
    for index, page in enumerate(pages, start=1):
        flat = _normalize(page)
        for match in pattern.finditer(flat):
            # The cue usually FOLLOWS the term ("the Natiq, the speaking prophet of
            # an age") — a generous window catches that apposition. But a name
            # reveal runs the other way ("his father's name was al-Bakhtari"), so a
            # SHORT window immediately before the term is checked too — short
            # enough (unlike the old ±160 bug) that it cannot reach into an
            # unrelated preceding sentence, only the same clause.
            after = flat[match.end() : match.end() + _DEFINITION_WINDOW]
            before = flat[max(0, match.start() - _NAME_REVEAL_WINDOW) : match.start()]
            window = before + " " + after
            if any(cue in window for cue in _DEFINITION_CUES):
                return index
    return None


def prerequisite_gaps(pages: list[str], terms: list[str]) -> list[dict[str, Any]]:
    """Terms the book leans on before it explains them — the reader's real obstacle.

    Reported with the page a bridge belongs on (the first use) and the page that
    currently carries the explanation, so the fix is a sentence, never a reorder.
    """
    gaps: list[dict[str, Any]] = []
    for term in terms:
        used = term_pages(pages, term)
        if len(used) < _MIN_USES_TO_MATTER:
            continue
        first_use = used[0]
        explained = explanation_page(pages, term)
        if explained is None:
            gaps.append(
                {
                    "term": term,
                    "first_use_page": first_use,
                    "explained_page": None,
                    "pages_carried": len(used),
                    "kind": "never-explained",
                }
            )
        elif explained - first_use >= _MIN_PAGE_GAP:
            gaps.append(
                {
                    "term": term,
                    "first_use_page": first_use,
                    "explained_page": explained,
                    "pages_carried": explained - first_use,
                    "kind": "explained-late",
                }
            )
    return sorted(gaps, key=lambda g: (-(g["pages_carried"] or 0), g["term"]))


def naming_drift(pages: list[str], terms: list[str]) -> list[dict[str, Any]]:
    """One idea spelled two ways IN PRINT — the compose pass disagreeing with itself.

    Candidates are grouped by normalized skeleton (glossary entries that fold to
    the same concept). Presence is then checked against each variant's PLAIN-
    TRANSLITERATED form (folded through the same ``simplify_transliteration`` the
    print pipeline itself applies before anything reaches the page — BK-A4), not
    the glossary's own raw spelling. That fold is what makes this catch the real
    case it was blind to: a glossary entry stored as ``Shariʿa`` (scholarly ayn)
    never literally appears anywhere in the PRINTED book, which only ever shows
    plain transliteration — searching for the raw glossary spelling found nothing,
    so a second entry drifting from the first went undetected. Folding both sides
    the same way is what the print pipeline already guarantees is equivalent; this
    check now trusts that guarantee instead of re-deriving a stricter one.

    Residual scope limit, left open on purpose: this still only compares spellings
    that exist as GLOSSARY entries. An ad hoc spelling a single augment note
    introduces, with no glossary entry of its own at all, is invisible here — that
    needs either a written bridge from a human review or a fuzzy near-neighbor
    scan across the raw page text, which is real new infrastructure, not a fold.
    """
    flat = " ".join("\n".join(pages).split()).lower()
    skeleton_to_surfaces: dict[str, set[str]] = {}
    for term in terms:
        skeleton = re.sub(r"[^a-z]", "", _normalize(term))
        if not skeleton:
            continue
        surface = simplify_transliteration(" ".join(term.split())).lower()
        if re.search(r"\b" + re.escape(surface) + r"\b", flat):
            skeleton_to_surfaces.setdefault(skeleton, set()).add(surface)
    return [{"variants": sorted(surfaces)} for surfaces in skeleton_to_surfaces.values() if len(surfaces) > 1]


def dense_pages(pages: list[str], terms: list[str]) -> list[dict[str, Any]]:
    """Pages carrying an unusual number of the book's terms at once."""
    out: list[dict[str, Any]] = []
    for index, page in enumerate(pages, start=1):
        flat = _normalize(page)
        hits = sorted({t for t in terms if _term_pattern(t).search(flat)})
        if len(hits) >= _DENSE_PAGE_TERMS:
            out.append({"page": index, "term_count": len(hits), "terms": hits[:10]})
    return out


def long_sentences(pages: list[str]) -> list[dict[str, Any]]:
    """Sentences long enough that a reader loses the thread before the full stop."""
    out: list[dict[str, Any]] = []
    for index, page in enumerate(pages, start=1):
        for sentence in re.split(r"(?<=[.!?])\s+", " ".join(page.split())):
            words = sentence.split()
            if len(words) >= _LONG_SENTENCE_WORDS:
                out.append({"page": index, "words": len(words), "text": sentence[:160]})
    return sorted(out, key=lambda s: -s["words"])[:20]


def analyze(pages: list[str], terms: list[str]) -> dict[str, Any]:
    """Every deterministic reader-facing measurement, in one report."""
    gaps = prerequisite_gaps(pages, terms)
    return {
        "schema": "book.comprehension/v1",
        "pages": len(pages),
        "terms_tracked": len(terms),
        "prerequisite_gaps": gaps,
        "naming_drift": naming_drift(pages, terms),
        "dense_pages": dense_pages(pages, terms),
        "long_sentences": long_sentences(pages),
        "summary": {
            "never_explained": sum(1 for g in gaps if g["kind"] == "never-explained"),
            "explained_late": sum(1 for g in gaps if g["kind"] == "explained-late"),
        },
    }


def run_comprehension_checks(book_dir: Path, *, log=print, pdf: Path | None = None) -> dict[str, Any]:
    """Read the finished PDF and record what a reader would struggle with.

    ``pdf`` names the artifact when a route does not resolve through the book
    lane's own titled PDF — the supplication lane writes ``book/<slug>.pdf``.
    Every PDF route calls this as its LAST step, so the review always judges the
    file that was actually produced.

    Evidence only — the verdict belongs to the reviewing agent, which reads this
    alongside the pages themselves.
    """
    book_dir = Path(book_dir).resolve()
    if pdf is None:
        from deliver_book import _find_pdf

        pdf = _find_pdf(book_dir)
    else:
        pdf = Path(pdf)
    if pdf is None or not pdf.exists():
        log("    comprehension: no rendered PDF yet — render the book first")
        return {}
    pages = _extract_pages_text(pdf)
    if pages is None:
        log("    comprehension: could not read the PDF (pdftotext unavailable?)")
        return {}
    report = analyze(pages, glossary_terms(book_dir))
    out = book_dir / "_system" / "book-comprehension.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = report["summary"]
    log(
        f"    comprehension: {report['pages']} pages · {report['terms_tracked']} terms tracked · "
        f"{summary['explained_late']} explained late · {summary['never_explained']} never explained"
    )
    for gap in report["prerequisite_gaps"][:5]:
        where = f"p{gap['explained_page']}" if gap["explained_page"] else "never"
        log(f"      ! {gap['term']}: first used p{gap['first_use_page']}, explained {where}")
    return report


if __name__ == "__main__":  # pragma: no cover - thin CLI
    import sys

    if len(sys.argv) != 2:
        print("usage: _book_comprehension.py <BOOK_DIR>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(0 if run_comprehension_checks(Path(sys.argv[1])) else 1)
