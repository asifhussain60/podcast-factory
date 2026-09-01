"""A verbatim book's chapters ARE its reading edition.

Asif, 2026-08-31: "Isn't the chapters the same as the final reading edition?"
On the orchestrated route they were not. `compose_book_v2` authors `book/book.md`
from the raw transcript with a model, and the Podcast Factory Library publishes
`book/book.md` — never `chapters/*.txt`. So a recorded session's twenty-four
proofread, Arabic-restored chapters would have been discarded and replaced by
freshly authored prose: the verbatim guarantee dying one phase after it was
enforced, with the run reporting success.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _verbatim_edition import assemble  # noqa: E402


def _book(tmp_path: Path, chapters: list[tuple[int, str, str, str]], *, title="A Series") -> Path:
    """chapters: (source_chapter_ref, contract title, chapter_ref, prose)."""
    d = tmp_path / "bk"
    (d / "_system").mkdir(parents=True)
    (d / "chapters").mkdir()
    (d / "chapter-contracts").mkdir()
    (d / "meta.yml").write_text(yaml.safe_dump({"title": title}), encoding="utf-8")
    for ref, ctitle, cref, prose in chapters:
        (d / "chapters" / f"{cref}.txt").write_text(prose, encoding="utf-8")
        (d / "chapter-contracts" / f"{cref.split('-', 1)[-1]}.yml").write_text(
            yaml.safe_dump({"chapter_ref": cref, "title": ctitle, "source_chapter_ref": ref}),
            encoding="utf-8",
        )
    return d


def test_the_chapters_become_the_edition_verbatim(tmp_path):
    d = _book(tmp_path, [(1, "Love of the World", "ch01-the-bridge", "The world is a bridge.")])
    out = assemble(d, log=lambda m: None)
    md = out.read_text(encoding="utf-8")
    assert "## Love of the World" in md
    assert "The world is a bridge." in md


def test_the_title_comes_from_the_contract_not_the_filename(tmp_path):
    """The filename carries a slug phase 0d chose for itself; the contract
    carries the SOURCE's own chapter name. A reading edition of somebody's book
    uses that book's chapter names."""
    d = _book(tmp_path, [(1, "Love of the World", "ch01-the-bridge-not-the-dwelling", "x")])
    md = assemble(d, log=lambda m: None).read_text(encoding="utf-8")
    assert "## Love of the World" in md
    assert "bridge-not-the-dwelling" not in md


def test_chapters_are_ordered_by_the_plan_not_the_filename(tmp_path):
    """File numbers follow EPISODE numbers, which are non-contiguous for a
    verbatim book — sorting names would put chapter 10 before chapter 2."""
    d = _book(
        tmp_path,
        [
            (2, "Envy", "ch02-b", "envy prose"),
            (10, "False Hopes", "ch11-j", "hopes prose"),
            (1, "Love of the World", "ch01-a", "world prose"),
        ],
    )
    md = assemble(d, log=lambda m: None).read_text(encoding="utf-8")
    assert md.index("Love of the World") < md.index("Envy") < md.index("False Hopes")


def test_no_word_of_the_speaker_is_lost(tmp_path):
    d = _book(
        tmp_path,
        [(1, "One", "ch01-a", "alpha beta gamma"), (2, "Two", "ch02-b", "delta epsilon")],
    )
    md = assemble(d, log=lambda m: None).read_text(encoding="utf-8")
    for w in ("alpha", "beta", "gamma", "delta", "epsilon"):
        assert w in md


def test_the_book_title_heads_the_edition(tmp_path):
    d = _book(tmp_path, [(1, "One", "ch01-a", "x")], title="Purification of the Heart")
    md = assemble(d, log=lambda m: None).read_text(encoding="utf-8")
    assert md.startswith("# Purification of the Heart")


def test_the_library_s_own_splitter_reads_every_chapter_back(tmp_path):
    """The structure emitted must be the structure the publisher already parses —
    otherwise this produces a file nothing downstream can use."""
    from _listener_book import split_chapters

    d = _book(tmp_path, [(1, "Love of the World", "ch01-a", "p"), (2, "Envy", "ch02-b", "q")])
    md = assemble(d, log=lambda m: None).read_text(encoding="utf-8")
    got = split_chapters(md)
    assert len(got) == 2
    assert [c.title for c in got] == ["Love of the World", "Envy"]


def test_an_empty_chapter_is_dropped_rather_than_titled(tmp_path):
    """A heading with nothing under it would publish as an empty chapter."""
    d = _book(tmp_path, [(1, "Real", "ch01-a", "prose"), (2, "Hollow", "ch02-b", "   ")])
    md = assemble(d, log=lambda m: None).read_text(encoding="utf-8")
    assert "## Real" in md
    assert "## Hollow" not in md


def test_a_book_with_no_chapters_yet_returns_none(tmp_path):
    """Not an error — a verbatim book at an earlier phase. The caller falls
    through to the ordinary composer rather than failing the run."""
    d = tmp_path / "empty"
    (d / "_system").mkdir(parents=True)
    assert assemble(d, log=lambda m: None) is None


def test_a_contract_whose_chapter_file_is_missing_is_skipped(tmp_path):
    d = _book(tmp_path, [(1, "Real", "ch01-a", "prose")])
    (d / "chapter-contracts" / "ghost.yml").write_text(
        yaml.safe_dump({"chapter_ref": "ch99-ghost", "title": "Ghost", "source_chapter_ref": 99}),
        encoding="utf-8",
    )
    md = assemble(d, log=lambda m: None).read_text(encoding="utf-8")
    assert "Ghost" not in md


def test_only_verbatim_books_take_this_path():
    """An authored book must still be composed. The branch is keyed on
    episode_voice, never on a bucket or a slug."""
    import inspect

    import _book_pipeline_v2

    src = inspect.getsource(_book_pipeline_v2.compose_book_v2)
    assert "EPISODE_VOICE_VERBATIM" in src
    assert "author_translation_edition_compose" in src
    assert "Sessions" not in src


def test_the_two_lane_gate_excludes_verbatim_books_by_voice(tmp_path):
    """`test_compose_lanes_distinct` asserts two INDEPENDENTLY produced lanes
    are not copies of each other. A verbatim book has one lane by design, so it
    is out of scope there — excluded by its declared voice, never by name."""
    import inspect

    from tests import test_compose_lanes_distinct as gate

    src = inspect.getsource(gate)
    assert "_is_verbatim" in src
    assert "purification" not in src.lower()
