"""Tests for the classical-lexicon ETL framework (lexicon_ingest.py).

Sources are injected as tmp drop folders + fake parsers; the live
lexicon.jsonl and morphology.db are never touched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

import lexicon_ingest as lx  # noqa: E402

CORPUS_ROOTS = [
    {"root_skel": "رحم", "root_bw": "rHm", "root_ar": "رحم"},
    {"root_skel": "سكن", "root_bw": "skn", "root_ar": "سكن"},
    {"root_skel": "عون", "root_bw": "Ewn", "root_ar": "عون"},
]


def test_all_sources_soft_skip_when_no_files(tmp_path: Path, capsys) -> None:
    report = lx.ingest_all(
        lexicon_path=tmp_path / "lexicon.jsonl",
        source_root=tmp_path / "source",
        corpus_roots=CORPUS_ROOTS,
        dry_run=True,
    )
    out = capsys.readouterr().out
    assert out.count("soft-skipped") == 3
    assert report["corpus_roots"] == 3
    for cov in report["sources"].values():
        assert cov["matched"] == 0 and cov["unmatched"] == 3
        assert set(cov["unmatched_roots"]) == {"رحم", "سكن", "عون"}


def test_seeds_full_root_inventory_even_without_sources(tmp_path: Path) -> None:
    path = tmp_path / "lexicon.jsonl"
    lx.ingest_all(
        lexicon_path=path,
        source_root=tmp_path / "source",
        coverage_path=tmp_path / "coverage.json",
        corpus_roots=CORPUS_ROOTS,
    )
    records = lx.load_lexicon(path)
    assert set(records) == {"رحم", "سكن", "عون"}
    assert records["رحم"]["root_bw"] == "rHm"
    assert records["رحم"]["sources"] == []


def test_present_but_unparsed_files_raise_not_skip(tmp_path: Path, monkeypatch) -> None:
    lane_dir = tmp_path / "source" / "lane"
    lane_dir.mkdir(parents=True)
    (lane_dir / "lane.txt").write_text("whatever", encoding="utf-8")
    with pytest.raises(lx.LexiconSourceUnparsed, match="lane"):
        lx.ingest_all(
            lexicon_path=tmp_path / "lexicon.jsonl",
            source_root=tmp_path / "source",
            corpus_roots=CORPUS_ROOTS,
            dry_run=True,
        )


def test_fake_parser_merges_additively_and_reports_coverage(tmp_path: Path, monkeypatch) -> None:
    lane_dir = tmp_path / "source" / "lane"
    lane_dir.mkdir(parents=True)
    (lane_dir / "lane.txt").write_text("data", encoding="utf-8")
    # Parser yields mixed notations — both must land on the same skeleton keys.
    monkeypatch.setitem(
        lx._SOURCES,
        "lane",
        ("lane_en", lambda d: iter([("rHm", "had mercy; tenderness of heart"), ("سكن", "was still")])),
    )
    path = tmp_path / "lexicon.jsonl"

    report = lx.ingest_all(
        lexicon_path=path,
        source_root=tmp_path / "source",
        coverage_path=tmp_path / "coverage.json",
        corpus_roots=CORPUS_ROOTS,
    )
    assert report["sources"]["lane"]["matched"] == 2
    assert report["sources"]["lane"]["unmatched_roots"] == ["عون"]

    records = lx.load_lexicon(path)
    assert records["رحم"]["lane_en"].startswith("had mercy")
    assert records["رحم"]["sources"] == ["lane"]

    # Second run with a corrected gloss: same source may overwrite its own field;
    # other fields and roots are untouched (additive, never clobbering).
    monkeypatch.setitem(lx._SOURCES, "lane", ("lane_en", lambda d: iter([("rHm", "corrected gloss")])))
    lx.ingest_all(
        lexicon_path=path,
        source_root=tmp_path / "source",
        coverage_path=tmp_path / "coverage.json",
        corpus_roots=CORPUS_ROOTS,
    )
    records = lx.load_lexicon(path)
    assert records["رحم"]["lane_en"] == "corrected gloss"
    assert records["سكن"]["lane_en"] == "was still"
    assert records["رحم"]["sources"] == ["lane"]


def test_lane_parser_reads_the_root_keyed_dataset(tmp_path: Path) -> None:
    # Mini file in the real aliozdenisik/quran-arabic-roots-lane-lexicon shape.
    lane_dir = tmp_path / "source" / "lane"
    lane_dir.mkdir(parents=True)
    long_article = "He was patient. " * 60  # forces the definitional-head trim
    payload = {
        "metadata": {"total_roots": 3},
        "roots": [
            {
                "root": "رحم",
                "root_buckwalter": "rHm",
                "definition_en": long_article,
                "summary_en": "MODEL-GENERATED — must be ignored",
            },
            {"root": "سكن", "root_buckwalter": "skn", "definition_en": "He was still."},
            {"root": "عون", "root_buckwalter": "Ewn", "definition_en": ""},  # no Lane match
        ],
    }
    (lane_dir / "lane.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    path = tmp_path / "lexicon.jsonl"
    report = lx.ingest_all(
        lexicon_path=path,
        source_root=tmp_path / "source",
        coverage_path=tmp_path / "coverage.json",
        corpus_roots=CORPUS_ROOTS,
    )
    assert report["sources"]["lane"]["matched"] == 2
    assert report["sources"]["lane"]["unmatched_roots"] == ["عون"]
    records = lx.load_lexicon(path)
    assert records["سكن"]["lane_en"] == "He was still."
    trimmed = records["رحم"]["lane_en"]
    assert len(trimmed) <= 600 and trimmed.endswith(".")  # head-trimmed at a sentence
    assert "MODEL-GENERATED" not in json.dumps(records, ensure_ascii=False)


def test_lane_dir_with_wrong_files_raises(tmp_path: Path) -> None:
    lane_dir = tmp_path / "source" / "lane"
    lane_dir.mkdir(parents=True)
    (lane_dir / "notes.txt").write_text("not the dataset", encoding="utf-8")
    with pytest.raises(lx.LexiconSourceUnparsed, match="lane"):
        lx.ingest_all(
            lexicon_path=tmp_path / "lexicon.jsonl",
            source_root=tmp_path / "source",
            corpus_roots=CORPUS_ROOTS,
            dry_run=True,
        )


def test_lookup_accepts_any_notation(tmp_path: Path) -> None:
    records = {"رحم": {"root_skel": "رحم", "lane_en": "mercy"}}
    assert lx.lookup("rHm", records)["lane_en"] == "mercy"
    assert lx.lookup("r-H-m", records)["lane_en"] == "mercy"
    assert lx.lookup("رحم", records)["lane_en"] == "mercy"
    assert lx.lookup("xyz", records) is None


def test_written_jsonl_is_sorted_and_valid(tmp_path: Path) -> None:
    path = tmp_path / "lexicon.jsonl"
    lx.ingest_all(
        lexicon_path=path,
        source_root=tmp_path / "source",
        coverage_path=tmp_path / "coverage.json",
        corpus_roots=CORPUS_ROOTS,
    )
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    keys = [json.loads(ln)["root_skel"] for ln in lines]
    assert keys == sorted(keys)
