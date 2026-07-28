#!/usr/bin/env python3
"""lexicon_ingest.py — classical-lexicon ETL: root-keyed meanings for the morphology layer.

Joins the Quranic Arabic Corpus root list (``morphology.db``) to classical
lexica, producing ``content/knowledge-base/lexicon.jsonl`` — one record per
root — plus a join-coverage report at
``content/knowledge-base/_index/lexicon-coverage.json`` (matched counts per
source AND the unmatched list; gaps are visible, never silently dropped).

Record shape (additive across runs, keyed by ``root_skel``)::

    {"root_skel": "رحم", "root_bw": "rHm", "root_ar": "رحم",
     "lane_en": "...",        # Lane's Lexicon — machine-join English gloss
     "maqayis_ar": "...",     # Ibn Faris, Maqayis al-Lugha — the asl (core sense), Arabic
     "mufradat_ar": "...",    # al-Raghib, al-Mufradat — Quranic nuance, Arabic
     "sources": ["lane", ...]}

Source registry: each lexicon has a drop folder under
``content/knowledge-base/lexicon/source/<name>/`` and a parser that yields
``(root_key, text)`` pairs. A source whose folder is empty or missing is
SOFT-SKIPPED with a printed note (the mirror-absent convention) — parsers are
written against the ACTUAL files as they are acquired, never against an
imagined format, so an unacquired source's parser raises
``LexiconSourceUnparsed`` if files appear before its parser lands.

Merge discipline: additive + root-keyed — an existing record gains fields, a
field already present is only overwritten by the SAME source re-running (so a
better parse propagates), and nothing is ever clobbered wholesale (the
``corpus_sync`` export-hazard rule).

The classical texts are public domain; the digitizations' own notes ship in the
drop folders. Attribution lives in content/knowledge-base/README.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterator

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _arabic_coverage import normalize_arabic  # noqa: E402
from _buckwalter import bw_skeleton  # noqa: E402

REPO_ROOT = _HERE.parents[1]
KB_DIR = REPO_ROOT / "content" / "knowledge-base"
LEXICON_JSONL = KB_DIR / "lexicon.jsonl"
LEXICON_SOURCE_DIR = KB_DIR / "lexicon" / "source"
COVERAGE_REPORT = KB_DIR / "_index" / "lexicon-coverage.json"


class LexiconSourceUnparsed(RuntimeError):
    """Files are present for a source whose parser has not been written yet.

    Raised instead of guessing at a format: the parser for each lexicon is
    authored against the actual acquired files (plan W4), and silently skipping
    present-but-unparsed files would read as "ingested" when nothing was.
    """


def _root_key(raw: str) -> str:
    """Any notation (Arabic, Buckwalter, dashed) -> the repo-wide skeleton key."""
    raw = (raw or "").strip()
    if any("؀" <= c <= "ۿ" for c in raw):
        return normalize_arabic(raw)
    return bw_skeleton(raw.replace("-", "").replace(" ", ""))


# ─── Per-source parsers (written against the real files as acquired) ─────────
def _parse_lane(source_dir: Path) -> Iterator[tuple[str, str]]:
    """Lane's Lexicon via the root-keyed dataset (aliozdenisik/quran-arabic-
    roots-lane-lexicon, GPL-3.0): ``{metadata, roots:[{root, root_buckwalter,
    definition_en, ...}]}``.

    Only ``definition_en`` is used — it is the digitized text of Lane's actual
    article for the root (present for 1,337 of 1,651 roots). The dataset's
    ``summary_en``/``summary_tr`` fields are model-generated and are NOT Lane;
    presenting them as Lane would violate the no-model-recall doctrine, so they
    are ignored entirely. The article is trimmed to its definitional head —
    Lane's opening senses — because the full article can run to pages of
    philological apparatus no prompt or print block needs.
    """
    files = sorted(source_dir.glob("*.json"))
    if not files:
        raise LexiconSourceUnparsed(f"lane: files present in {source_dir} but none is the expected root-keyed *.json")
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        roots = data.get("roots")
        if not isinstance(roots, list):
            raise LexiconSourceUnparsed(f"lane: {path.name} has no 'roots' list — unexpected format")
        for rec in roots:
            definition = str(rec.get("definition_en") or "").strip()
            root = str(rec.get("root") or rec.get("root_buckwalter") or "").strip()
            if root and definition:
                yield root, _definitional_head(definition)


def _definitional_head(article: str, *, min_chars: int = 200, max_chars: int = 600) -> str:
    """The opening senses of a lexicon article, trimmed at a sentence boundary.

    Deterministic: accumulate sentences until ``min_chars`` is reached, hard-cap
    at ``max_chars`` (cutting at the last sentence end inside the cap, else at a
    word boundary with an ellipsis).
    """
    import re as _re

    text = " ".join(article.split())
    if len(text) <= max_chars:
        return text
    ends = [m.end() for m in _re.finditer(r"[.!?؟](?=\s)", text[:max_chars])]
    for end in ends:
        if end >= min_chars:
            return text[:end].strip()
    if ends:
        return text[: ends[-1]].strip()
    return text[:max_chars].rsplit(" ", 1)[0].strip() + " …"


def _parse_maqayis(source_dir: Path) -> Iterator[tuple[str, str]]:
    raise LexiconSourceUnparsed(
        f"maqayis: files present in {source_dir} but the Maqayis parser has not "
        "been written against them yet — author it from the actual file format"
    )


def _parse_mufradat(source_dir: Path) -> Iterator[tuple[str, str]]:
    raise LexiconSourceUnparsed(
        f"mufradat: files present in {source_dir} but the Mufradat parser has "
        "not been written against them yet — author it from the actual file format"
    )


# name -> (record field, parser). Adding a lexicon = one line here + one parser.
_SOURCES: dict[str, tuple[str, Callable[[Path], Iterator[tuple[str, str]]]]] = {
    "lane": ("lane_en", _parse_lane),
    "maqayis": ("maqayis_ar", _parse_maqayis),
    "mufradat": ("mufradat_ar", _parse_mufradat),
}


# ─── Store ───────────────────────────────────────────────────────────────────
def load_lexicon(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """``{root_skel: record}`` from the committed JSONL; empty when absent."""
    p = Path(path or LEXICON_JSONL)
    out: dict[str, dict[str, Any]] = {}
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = str(rec.get("root_skel") or "")
        if key:
            out[key] = rec
    return out


def _write_lexicon(records: dict[str, dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(records[k], ensure_ascii=False, sort_keys=True) for k in sorted(records)]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


# ─── Ingest + coverage ───────────────────────────────────────────────────────
def ingest_all(
    *,
    lexicon_path: Path | None = None,
    source_root: Path | None = None,
    coverage_path: Path | None = None,
    corpus_roots: list[dict[str, Any]] | None = None,
    dry_run: bool = False,
    log=print,
) -> dict[str, Any]:
    """Run every acquirable source, merge additively, report coverage.

    ``corpus_roots`` defaults to the live morphology.db root list; tests inject
    a small list. Returns the coverage report dict.
    """
    if corpus_roots is None:
        import quranic_morphology

        corpus_roots = quranic_morphology.list_roots()
    if not corpus_roots:
        log(
            "  ! morphology.db absent or empty — build it first "
            "(python3 scripts/podcast/quranic_morphology.py); coverage cannot be computed"
        )

    records = load_lexicon(lexicon_path)
    # Seed/refresh a record per corpus root so lexicon.jsonl always carries the
    # full root inventory with script + Buckwalter, even before any source lands.
    for r in corpus_roots:
        rec = records.setdefault(r["root_skel"], {"root_skel": r["root_skel"], "sources": []})
        rec.setdefault("root_bw", r["root_bw"])
        rec.setdefault("root_ar", r["root_ar"])

    src_root = Path(source_root or LEXICON_SOURCE_DIR)
    ran: dict[str, int] = {}
    for name, (field, parser) in _SOURCES.items():
        source_dir = src_root / name
        files = [p for p in source_dir.rglob("*") if p.is_file()] if source_dir.is_dir() else []
        if not files:
            log(f"  · {name}: no files in {source_dir} — soft-skipped")
            continue
        matched = 0
        for raw_root, text in parser(source_dir):
            key = _root_key(raw_root)
            text = (text or "").strip()
            if not key or not text:
                continue
            rec = records.setdefault(key, {"root_skel": key, "sources": []})
            rec[field] = text
            if name not in rec["sources"]:
                rec["sources"].append(name)
            matched += 1
        ran[name] = matched
        log(f"  · {name}: {matched} root entries ingested")

    report = _coverage(records, corpus_roots, ran)
    if not dry_run:
        _write_lexicon(records, Path(lexicon_path or LEXICON_JSONL))
        cov_path = Path(coverage_path or COVERAGE_REPORT)
        cov_path.parent.mkdir(parents=True, exist_ok=True)
        cov_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def _coverage(
    records: dict[str, dict[str, Any]],
    corpus_roots: list[dict[str, Any]],
    ran: dict[str, int],
) -> dict[str, Any]:
    corpus_keys = [r["root_skel"] for r in corpus_roots]
    per_source: dict[str, Any] = {}
    for name, (field, _parser) in _SOURCES.items():
        matched = [k for k in corpus_keys if records.get(k, {}).get(field)]
        unmatched = [k for k in corpus_keys if not records.get(k, {}).get(field)]
        per_source[name] = {
            "ran_this_time": name in ran,
            "matched": len(matched),
            "unmatched": len(unmatched),
            "unmatched_roots": unmatched,
        }
    return {
        "schema": "kb.lexicon-coverage/v1",
        "corpus_roots": len(corpus_keys),
        "sources": per_source,
    }


def lookup(root: str, records: dict[str, dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """The lexicon record for a root in any notation; None when unknown."""
    recs = records if records is not None else load_lexicon()
    return recs.get(_root_key(root))


def _cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="parse + report, write nothing")
    args = ap.parse_args()
    try:
        report = ingest_all(dry_run=args.dry_run)
    except LexiconSourceUnparsed as e:
        print(f"ERROR: {e}")
        return 1
    print(f"lexicon coverage over {report['corpus_roots']} corpus roots:")
    for name, cov in report["sources"].items():
        print(f"  {name:>9}: {cov['matched']} matched, {cov['unmatched']} unmatched")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
