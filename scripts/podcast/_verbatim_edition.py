"""Assemble a verbatim book's reading edition from the chapters it already has.

WHAT WAS WRONG (2026-08-31, found by Asif asking "isn't the chapters the same as
the final reading edition?"). On the orchestrated route they are not, and for a
recorded session that is a defect rather than a design.

`compose_book_v2` builds `book/book.md` from `_system/source/text/
refined-english.md` — the raw transcript — by asking a model to author it. The
Podcast Factory Library then publishes `book/book.md`, split on its `##`
headings, and never opens `chapters/*.txt`.

For a BOOK that is right: chapter files are podcast upload sources and the
reading edition is a separately composed print deliverable — two products from
one source. For a SESSION there is one product. Phase 0d had already produced
twenty-four chapters that were proofread, Arabic-restored and never rewritten,
and the compose step would have thrown them away and had a model write fresh
prose off the transcript. The verbatim guarantee would have died one phase after
it was enforced, and the run would have reported success.

WHAT THIS DOES INSTEAD is a mechanical join: each chapter's own title as a `##`
heading, its prose beneath, in plan order. No model, nothing rewritten, nothing
summarised. The structure it emits is exactly what `_listener_book.split_chapters`
already reads, so the thing reviewed in the Composer is the thing that ships.

THE TITLE COMES FROM THE CONTRACT, not the filename. The contract's `title:` is
the SOURCE's own chapter name ("Love of the World"); the filename carries a slug
phase 0d chose for itself ("the-bridge-not-the-dwelling"). A reading edition of
somebody's book uses that book's chapter names.
"""

from __future__ import annotations

from pathlib import Path


def _chapter_order(book_dir: Path) -> list[tuple[int, str, Path]]:
    """(source-chapter index, title, chapter file) in the plan's order.

    Ordered by `source_chapter_ref` rather than by filename: the file numbers
    follow EPISODE numbers, which for a verbatim book are non-contiguous (this
    book's run produced ch01…ch28 for twenty-four chapters). Sorting the names
    would put chapter 10 before chapter 2 anyway.
    """
    import yaml

    contracts = book_dir / "chapter-contracts"
    chapters = book_dir / "chapters"
    if not contracts.is_dir() or not chapters.is_dir():
        return []

    out: list[tuple[int, str, Path]] = []
    for cf in sorted(contracts.glob("*.yml")):
        try:
            c = yaml.safe_load(cf.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        ref = c.get("chapter_ref")
        if not ref:
            continue
        f = chapters / f"{ref}.txt"
        if not f.is_file():
            continue
        idx = c.get("source_chapter_ref")
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            idx = len(out) + 1
        title = str(c.get("title") or "").strip() or cf.stem.replace("-", " ").title()
        out.append((idx, title, f))
    out.sort(key=lambda t: t[0])
    return out


def assemble(book_dir: Path, *, book_title: str = "", log=print) -> Path | None:
    """Write `book/book.md` from the chapter files. Returns it, or None.

    Returns None rather than raising when there is nothing to assemble, so the
    caller can fall through to the ordinary composer: a verbatim book whose
    chapters have not been written yet is not an error, it is a book at an
    earlier phase.
    """
    book_dir = Path(book_dir)
    parts = _chapter_order(book_dir)
    if not parts:
        return None

    title = book_title.strip()
    if not title:
        try:
            import yaml

            meta = yaml.safe_load((book_dir / "meta.yml").read_text(encoding="utf-8")) or {}
            title = str(meta.get("title") or "").strip()
        except Exception:
            title = ""
    title = title or book_dir.name.replace("-", " ").title()

    body = [f"# {title}", ""]
    for _idx, chapter_title, path in parts:
        prose = path.read_text(encoding="utf-8").strip()
        if not prose:
            continue
        body.append(f"## {chapter_title}")
        body.append("")
        body.append(prose)
        body.append("")

    out = book_dir / "book" / "book.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
    words = sum(len(p.read_text(encoding="utf-8").split()) for _i, _t, p in parts)
    log(f"    0book-compose: assembled {len(parts)} verbatim chapter(s) into book.md ({words:,} words, no model call)")
    return out
