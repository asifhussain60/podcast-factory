#!/usr/bin/env python3
"""Move a Composer-authored front-matter section into chapter 1, once.

WHY THIS EXISTS
---------------
From 2026-08-03 a book's opening is folded into its first numbered chapter at
assembly time (``_translation_edition``), so no edition begins with a preface.
That fold is refused for one shape, and refused deliberately: a book whose
front-matter section carries a **Composer edit**.

The reason is ordering. The assembly folds; the Composer replay then rewrites
every edited chapter from ``_system/composer-edits.json`` a step later. If
chapter 1 is itself edited, the replay restores the author's chapter and the
folded opening goes with it — and nothing reports the loss, because
``apply_composer_edits`` only reports an edit whose HEADING is gone, not prose
that vanished from a chapter it found.

So the sidecar is migrated instead: the human's front-matter body is merged into
the human's chapter-1 body, in the sidecar, and the front-matter edit is deleted.
After that there is exactly one place holding each piece of prose, and the book
takes ``preface.include: false`` because its opening now lives inside chapter 1.

WHAT IT DOES, EXACTLY
---------------------
1. Reads ``_system/composer-edits.json``.
2. Strips the retired machine preface (the ``edition-intro`` fence) from the
   front-matter body — that text is the pipeline's, not the author's, and it is
   what this whole change is removing.
3. Prepends what remains to the chapter body, separated by a blank line.
4. Deletes the front-matter edit and rewrites the sidecar atomically.
5. Sets ``preface.include: false`` in ``book/book-toc.json`` unless
   ``--keep-toc-preface``, so the assembly does not re-emit the opening a second
   time beside the copy now inside chapter 1.

Refuses rather than guesses: an absent front-matter edit, an absent chapter edit,
or an already-merged body each stop the run with a message. ``--dry-run`` prints
the plan and writes nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_edits import anchor_key, load_edits, sidecar_path  # noqa: E402
from _book_frontmatter import strip_introduction  # noqa: E402

_SENTENCE_RE = re.compile(r"(?<=[.!?:])\s+")
_FENCE_RE = re.compile(r"<!--.*?-->", re.S)
_PAREN_RE = re.compile(r"\([^)]*\)")
_NON_LATIN_RE = re.compile(r"[^a-z ]")

# Words too common to carry evidence that two passages are the same passage.
_STOPWORDS = frozenset(
    "the a an of and to in is it that this for by with as on from at be are was were "
    "his he him they them which who not or but so all its their there then than into "
    "upon has had have will shall when what who whom because also more most such".split()
)


def _sentences(text: str) -> list[str]:
    flat = " ".join(_FENCE_RE.sub("", text).split())
    return [s.strip() for s in _SENTENCE_RE.split(flat) if len(s.split()) >= 5]


def _content_words(text: str) -> list[str]:
    """The words that carry the passage's identity.

    Parentheticals are dropped from BOTH sides before anything else, and that is
    the load-bearing step rather than a tidy-up. The two renderings of one passage
    disagree about exactly what sits inside them: the front matter prints
    ``the pole (qutb)`` and the chapter prints ``the pole (قُطْب)``. Compared with
    the brackets in, the transliteration is a word the chapter never says and the
    script is a word this side cannot read, so the single most distinctive term in
    a sentence votes AGAINST a match it should have settled.
    """
    plain = _NON_LATIN_RE.sub(" ", _PAREN_RE.sub(" ", text.lower()))
    return [w for w in plain.split() if len(w) > 3 and w not in _STOPWORDS]


def coverage(front_matter: str, chapters: str, *, threshold: float = 0.70, window: int = 120) -> dict:
    """How much of a front-matter body the chapters already say, in other words.

    The question a DELETION has to answer, and neither an exact match nor a
    sentence-to-sentence similarity can answer it. A front-matter section and the
    chapter covering the same source lines are two INDEPENDENT renderings, so they
    share a passage while sharing barely a sentence — `degrees-of-excellence`
    shared exactly one of forty-five verbatim and all forty-five in substance —
    and they also punctuate differently, so one side's two sentences are the
    other's one.

    So the measure is content-word RECALL against the best-matching window of the
    chapters, which survives both differences: a sentence counts as already said
    when most of the words that make it that sentence appear together somewhere in
    the book. Everything below the floor is returned for a human to read. This
    decides whether prose is deleted, so it reports rather than concludes.
    """
    haystack = _content_words(chapters)
    windows = [set(haystack[i : i + window]) for i in range(0, max(1, len(haystack) - window // 2), window // 4)]
    found: list[str] = []
    missing: list[tuple[float, str]] = []
    for sentence in _sentences(front_matter):
        words = set(_content_words(sentence))
        if not words:
            continue
        best = max((len(words & w) / len(words) for w in windows), default=0.0)
        if best >= threshold:
            found.append(sentence)
        else:
            missing.append((round(best, 2), sentence))
    total = len(found) + len(missing)
    return {
        "sentences": total,
        "already_said": len(found),
        "ratio": (len(found) / total) if total else 0.0,
        "missing": sorted(missing, reverse=True),
    }


def plan_drop(book_dir: Path, preface_title: str) -> dict:
    """Delete a front-matter edit whose text the CHAPTERS already carry.

    The other outcome of the same investigation the fold serves. A front-matter
    section carved out of a range that its chapter still covers is not additional
    content — it is the same passage rendered twice — and folding it would print
    the passage twice inside one chapter. Deleting it loses nothing.

    Evidence-gated rather than asserted: every sentence of the front matter is
    matched against every sentence of every OTHER edited chapter, and anything
    below the coverage floor is listed for a human to read before the delete runs.
    """
    book_dir = Path(book_dir).resolve()
    pf_key = anchor_key(preface_title)
    data = load_edits(book_dir, strict=True)
    edits = {str(e.get("chapter_key")): e for e in data["edits"] if e.get("chapter_key")}
    if pf_key not in edits:
        raise SystemExit(f"no Composer edit keyed {pf_key!r} in {sidecar_path(book_dir)} — nothing to drop")

    pf_body = strip_introduction(str(edits[pf_key].get("body_md") or "")).strip()
    chapters = "\n\n".join(str(e.get("body_md") or "") for k, e in edits.items() if k != pf_key)
    return {
        "book_dir": str(book_dir),
        "preface_key": pf_key,
        "preface_words": len(pf_body.split()),
        "coverage": coverage(pf_body, chapters),
        "data": data,
    }


def apply_drop(plan: dict, *, keep_toc_preface: bool = False, log=print) -> None:
    from _book_edits import _write_json_atomic

    book_dir = Path(plan["book_dir"])
    data = plan["data"]
    data["edits"] = [e for e in data["edits"] if str(e.get("chapter_key") or "") != plan["preface_key"]]
    _write_json_atomic(sidecar_path(book_dir), data)
    cov = plan["coverage"]
    log(
        f"    sidecar: {plan['preface_key']!r} deleted ({plan['preface_words']} words) — "
        f"{cov['already_said']}/{cov['sentences']} of its sentences are already said by the chapters"
    )
    if not keep_toc_preface:
        _drop_toc_preface(book_dir, log)


def plan_fold(book_dir: Path, preface_title: str, chapter_title: str) -> dict:
    """Everything the migration would do, computed without writing anything."""
    book_dir = Path(book_dir).resolve()
    pf_key, ch_key = anchor_key(preface_title), anchor_key(chapter_title)
    data = load_edits(book_dir, strict=True)
    edits = {str(e.get("chapter_key")): e for e in data["edits"] if e.get("chapter_key")}

    if pf_key not in edits:
        raise SystemExit(f"no Composer edit keyed {pf_key!r} in {sidecar_path(book_dir)} — nothing to migrate")
    if ch_key not in edits:
        raise SystemExit(
            f"no Composer edit keyed {ch_key!r}. The fold only needs migrating when BOTH sections are "
            "authored; if chapter 1 is not, drop this book's preface entry and let the assembly fold it."
        )

    pf_body = strip_introduction(str(edits[pf_key].get("body_md") or "")).strip()
    ch_body = str(edits[ch_key].get("body_md") or "").strip()
    if not pf_body:
        raise SystemExit(f"{pf_key!r} holds nothing but a machine preface — delete the edit rather than folding it")
    if pf_body[:400] in ch_body:
        raise SystemExit(f"{ch_key!r} already opens on this text — the migration has already run")

    return {
        "book_dir": str(book_dir),
        "preface_key": pf_key,
        "chapter_key": ch_key,
        "preface_words": len(pf_body.split()),
        "chapter_words": len(ch_body.split()),
        "merged_words": len((pf_body + " " + ch_body).split()),
        "merged_body": pf_body + "\n\n" + ch_body,
        "data": data,
    }


def apply_fold(plan: dict, *, keep_toc_preface: bool = False, log=print) -> None:
    """Write the merged sidecar and, unless told otherwise, drop the toc entry."""
    from _book_edits import _write_json_atomic

    book_dir = Path(plan["book_dir"])
    data = plan["data"]
    kept = []
    for e in data["edits"]:
        key = str(e.get("chapter_key") or "")
        if key == plan["preface_key"]:
            continue
        if key == plan["chapter_key"]:
            e = {**e, "body_md": plan["merged_body"]}
        kept.append(e)
    data["edits"] = kept
    _write_json_atomic(sidecar_path(book_dir), data)
    log(
        f"    sidecar: {plan['preface_key']!r} ({plan['preface_words']} words) merged into "
        f"{plan['chapter_key']!r} — now {plan['merged_words']} words; front-matter edit deleted"
    )

    if not keep_toc_preface:
        _drop_toc_preface(book_dir, log)


def _drop_toc_preface(book_dir: Path, log) -> None:
    """Stop the assembly re-emitting an opening that now lives in a chapter."""
    toc_path = book_dir / "book" / "book-toc.json"
    toc = json.loads(toc_path.read_text(encoding="utf-8"))
    preface = toc.get("preface")
    if isinstance(preface, dict) and preface.get("include"):
        preface["include"] = False
        toc_path.write_text(json.dumps(toc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        log("    book-toc.json: preface.include -> false")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book_dir", type=Path)
    ap.add_argument("--preface-title", required=True, help="heading of the front-matter section, as it appears")
    ap.add_argument("--chapter-title", help="heading of chapter 1, without its number (the fold)")
    ap.add_argument(
        "--drop",
        action="store_true",
        help="delete the front-matter edit instead of folding it — for a section the chapters already say",
    )
    ap.add_argument("--keep-toc-preface", action="store_true", help="leave book-toc.json alone")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.drop:
        plan = plan_drop(args.book_dir, args.preface_title)
        cov = plan["coverage"]
        print(
            f"{plan['preface_key']!r}: {plan['preface_words']} words, "
            f"{cov['already_said']}/{cov['sentences']} sentences ({cov['ratio']:.0%}) already said by the chapters"
        )
        for ratio, sentence in cov["missing"]:
            print(f"  NOT MATCHED [{ratio}] {sentence[:150]}")
        if args.dry_run:
            print("--- dry run: nothing written ---")
            return 0
        apply_drop(plan, keep_toc_preface=args.keep_toc_preface)
        return 0

    if not args.chapter_title:
        raise SystemExit("--chapter-title is required unless --drop is given")
    plan = plan_fold(args.book_dir, args.preface_title, args.chapter_title)
    print(
        f"{plan['preface_key']!r} ({plan['preface_words']} words) -> {plan['chapter_key']!r} "
        f"({plan['chapter_words']} words) = {plan['merged_words']} words"
    )
    if args.dry_run:
        print("--- merged body, first 600 chars ---")
        print(plan["merged_body"][:600])
        print("--- dry run: nothing written ---")
        return 0
    apply_fold(plan, keep_toc_preface=args.keep_toc_preface)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
