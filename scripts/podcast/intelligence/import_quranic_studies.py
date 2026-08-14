#!/usr/bin/env python3
"""Import Quranic Studies teaching candidates into the knowledge corpus.

This is deliberately a dry-run-first importer.  Transcription/OCR can be messy,
but corpus insertion must be deterministic:

* Quran verses are referenced by canonical ``S:A`` ids, not duplicated.
* Teaching atoms are stored as doctrine atoms with ``source_kind=quranic_studies``.
* Exact duplicate teachings collapse onto one text-derived atom id.
* Near duplicates are reported for review instead of silently merged.
* Topic tags are written both into the atom body and ``atom_topic_tags``.

Input JSONL shape, one candidate per line::

    {
      "text_en": "A concise teaching...",
      "topic_tags": ["hamd", "surah al-fateha"],
      "quran_refs": ["1:1", "Q2:255"],
      "series": "Surah Al-Fateha",
      "session": "008 Perfection Of HAMD",
      "source_id": "surah-al-fateha/008",
      "locator": "00:12:30"
    }

CLI examples:

    python3 scripts/podcast/intelligence/import_quranic_studies.py \
      --input /tmp/quranic-studies-candidates.jsonl --dry-run

    python3 scripts/podcast/intelligence/import_quranic_studies.py \
      --input /tmp/quranic-studies-candidates.jsonl --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import _db
from _paths import REPO_ROOT

REPORT_DIR = REPO_ROOT / "_workspace" / "quran-studies-audio"
DEFAULT_JSON_REPORT = REPORT_DIR / "quranic-studies-import-report.json"
DEFAULT_MD_REPORT = REPORT_DIR / "quranic-studies-import-report.md"

SOURCE_KIND = "quranic_studies"
ATOM_PREFIX = "doctrine:quranic-studies:"
REVIEW_REASON = "quranic_studies_near_duplicate"

_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)
_QREF_RE = re.compile(r"(?:\bQ(?:uran)?\s*)?(\d{1,3})\s*[:.]\s*(\d{1,3})", re.IGNORECASE)


@dataclass
class Candidate:
    text_en: str
    topic_tags: list[str] = field(default_factory=list)
    quran_refs: list[str] = field(default_factory=list)
    series: str = ""
    session: str = ""
    source_id: str = ""
    locator: str = ""
    content_level: str | None = None
    confidence: float = 0.9

    @property
    def atom_id(self) -> str:
        digest = hashlib.sha256(_normalize(self.text_en).encode("utf-8")).hexdigest()[:16]
        return ATOM_PREFIX + digest

    @property
    def source_book(self) -> str:
        return self.source_id or _slugify("/".join(x for x in (self.series, self.session) if x)) or "quranic-studies"

    @property
    def source_chapter(self) -> str:
        return self.session or self.source_id or ""

    def body(self) -> dict[str, Any]:
        return {
            "text_en": self.text_en,
            "source_kind": SOURCE_KIND,
            "series": self.series,
            "session": self.session,
            "source_id": self.source_id,
            "locator": self.locator,
            "topic_tags": self.topic_tags,
            "quran_refs": self.quran_refs,
        }


@dataclass
class ImportSummary:
    candidates_seen: int = 0
    candidates_valid: int = 0
    invalid_lines: list[dict[str, Any]] = field(default_factory=list)
    exact_duplicates_in_input: int = 0
    already_in_corpus: int = 0
    new_atoms: int = 0
    near_duplicates: int = 0
    quran_refs: int = 0
    topic_tags: int = 0
    applied: bool = False
    new_atom_ids: list[str] = field(default_factory=list)
    duplicate_atom_ids: list[str] = field(default_factory=list)
    near_duplicate_pairs: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "podcast.quranic-studies-import/v1",
            "candidates_seen": self.candidates_seen,
            "candidates_valid": self.candidates_valid,
            "invalid_lines": self.invalid_lines,
            "exact_duplicates_in_input": self.exact_duplicates_in_input,
            "already_in_corpus": self.already_in_corpus,
            "new_atoms": self.new_atoms,
            "near_duplicates": self.near_duplicates,
            "quran_refs": self.quran_refs,
            "topic_tags": self.topic_tags,
            "applied": self.applied,
            "new_atom_ids": self.new_atom_ids,
            "duplicate_atom_ids": self.duplicate_atom_ids,
            "near_duplicate_pairs": self.near_duplicate_pairs,
        }


def _normalize(text: str) -> str:
    return _WORD_RE.sub(" ", (text or "").lower()).strip()


def _tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in _normalize(text).split() if len(t) > 2)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _slugify(text: str) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return out[:80].strip("-")


def _clean_tags(values: Iterable[Any]) -> list[str]:
    tags = []
    seen = set()
    for value in values or []:
        tag = " ".join(str(value).strip().lower().split())
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
    return tags


def _clean_qrefs(values: Iterable[Any], text: str = "") -> list[str]:
    refs: set[str] = set()
    for value in list(values or []) + [text]:
        for surah_s, ayah_s in _QREF_RE.findall(str(value or "")):
            surah, ayah = int(surah_s), int(ayah_s)
            if 1 <= surah <= 114 and 1 <= ayah <= 286:
                refs.add(f"{surah}:{ayah}")
    return sorted(refs, key=lambda r: tuple(int(x) for x in r.split(":")))


def _candidate_from_raw(raw: dict[str, Any]) -> Candidate:
    text = " ".join(str(raw.get("text_en") or raw.get("text") or "").split())
    if len(text) < 40:
        raise ValueError("candidate text is shorter than 40 characters")
    tags = _clean_tags(raw.get("topic_tags") or raw.get("topics") or [])
    qrefs = _clean_qrefs(raw.get("quran_refs") or raw.get("verses") or [], text)
    return Candidate(
        text_en=text,
        topic_tags=tags,
        quran_refs=qrefs,
        series=str(raw.get("series") or "").strip(),
        session=str(raw.get("session") or raw.get("title") or "").strip(),
        source_id=str(raw.get("source_id") or "").strip(),
        locator=str(raw.get("locator") or raw.get("timestamp") or "").strip(),
        content_level=raw.get("content_level"),
        confidence=float(raw.get("confidence") or 0.9),
    )


def load_candidates(path: Path) -> tuple[list[Candidate], list[dict[str, Any]]]:
    candidates: list[Candidate] = []
    invalid: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("line is not a JSON object")
            candidates.append(_candidate_from_raw(raw))
        except Exception as exc:
            invalid.append({"line": line_no, "error": str(exc)})
    return candidates, invalid


def _existing_doctrine_texts(conn) -> dict[str, str]:
    rows = conn.execute("SELECT id, body FROM atoms WHERE type='doctrine'").fetchall()
    out: dict[str, str] = {}
    for atom_id, body_raw in rows:
        try:
            body = json.loads(body_raw)
        except (TypeError, json.JSONDecodeError):
            body = {}
        text = str(body.get("text_en") or "")
        if text:
            out[str(atom_id)] = text
    return out


def _find_near_duplicates(
    candidate: Candidate,
    existing_texts: dict[str, str],
    *,
    threshold: float,
    limit: int = 3,
) -> list[dict[str, Any]]:
    cand_tokens = _tokens(candidate.text_en)
    scored = []
    for atom_id, text in existing_texts.items():
        score = _jaccard(cand_tokens, _tokens(text))
        if score >= threshold:
            scored.append({"incoming": candidate.atom_id, "existing": atom_id, "score": round(score, 4)})
    scored.sort(key=lambda row: row["score"], reverse=True)
    return scored[:limit]


def import_candidates(
    candidates: list[Candidate],
    *,
    apply: bool = False,
    near_threshold: float = 0.72,
    conn=None,
) -> ImportSummary:
    if conn is None:
        _db.run_migrations()
        conn = _db.get_connection()

    summary = ImportSummary(candidates_seen=len(candidates), applied=apply)
    existing_texts = _existing_doctrine_texts(conn)
    existing_norms = {_normalize(text): atom_id for atom_id, text in existing_texts.items()}
    seen_ids: set[str] = set()

    for cand in candidates:
        summary.candidates_valid += 1
        summary.quran_refs += len(cand.quran_refs)
        summary.topic_tags += len(cand.topic_tags)

        if cand.atom_id in seen_ids:
            summary.exact_duplicates_in_input += 1
            summary.duplicate_atom_ids.append(cand.atom_id)
            continue
        seen_ids.add(cand.atom_id)

        existing_exact = conn.execute("SELECT id FROM atoms WHERE id=?", (cand.atom_id,)).fetchone()
        text_exact = existing_norms.get(_normalize(cand.text_en))
        if existing_exact or text_exact:
            summary.already_in_corpus += 1
            summary.duplicate_atom_ids.append(str(text_exact or cand.atom_id))
            if apply:
                _add_source_and_tags(conn, cand.atom_id if existing_exact else str(text_exact), cand)
            continue

        near = _find_near_duplicates(cand, existing_texts, threshold=near_threshold)
        if near:
            summary.near_duplicates += len(near)
            summary.near_duplicate_pairs.extend(near)
            if apply:
                _queue_near_duplicate_review(conn, cand, near)
            continue

        summary.new_atoms += 1
        summary.new_atom_ids.append(cand.atom_id)
        if apply:
            _insert_atom(conn, cand)
            existing_texts[cand.atom_id] = cand.text_en
            existing_norms[_normalize(cand.text_en)] = cand.atom_id

    if apply:
        conn.commit()
    return summary


def _insert_atom(conn, cand: Candidate) -> None:
    fs_date = date.today().isoformat()
    conn.execute(
        """
        INSERT INTO atoms
            (id, type, body, first_seen_book, first_seen_chapter, first_seen_date,
             confidence, tradition, content_level)
        VALUES (?, 'doctrine', ?, ?, ?, ?, ?, 'universal', ?)
        """,
        (
            cand.atom_id,
            json.dumps(cand.body(), ensure_ascii=False, sort_keys=True),
            cand.source_book,
            cand.source_chapter,
            fs_date,
            max(0.0, min(1.0, cand.confidence)),
            cand.content_level,
        ),
    )
    _add_source_and_tags(conn, cand.atom_id, cand)


def _add_source_and_tags(conn, atom_id: str, cand: Candidate) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO atoms_sources (atom_id, book_slug, chapter_id, locator)
        VALUES (?, ?, ?, ?)
        """,
        (atom_id, cand.source_book, cand.source_chapter, cand.locator),
    )
    for tag in cand.topic_tags:
        conn.execute("INSERT OR IGNORE INTO atom_topic_tags (atom_id, tag) VALUES (?, ?)", (atom_id, tag))


def _queue_near_duplicate_review(conn, cand: Candidate, near: list[dict[str, Any]]) -> None:
    conn.execute(
        """
        INSERT INTO manual_review_queue (book_slug, chapter_id, reason, payload)
        VALUES (?, ?, ?, ?)
        """,
        (
            cand.source_book,
            cand.source_chapter,
            REVIEW_REASON,
            json.dumps({"candidate": cand.body(), "candidate_id": cand.atom_id, "near": near}, ensure_ascii=False),
        ),
    )


def write_reports(summary: ImportSummary, *, json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary.as_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(summary), encoding="utf-8")


def _render_markdown(summary: ImportSummary) -> str:
    mode = "applied" if summary.applied else "dry run"
    lines = [
        "# Quranic Studies import report",
        "",
        f"Mode: {mode}",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Candidates seen | {summary.candidates_seen} |",
        f"| Valid candidates | {summary.candidates_valid} |",
        f"| Invalid lines | {len(summary.invalid_lines)} |",
        f"| Exact duplicates in input | {summary.exact_duplicates_in_input} |",
        f"| Already in corpus | {summary.already_in_corpus} |",
        f"| Near-duplicate review hits | {summary.near_duplicates} |",
        f"| New atoms | {summary.new_atoms} |",
        f"| Quran references linked | {summary.quran_refs} |",
        f"| Topic tags carried | {summary.topic_tags} |",
        "",
    ]
    if summary.near_duplicate_pairs:
        lines.extend(["## Near duplicates", ""])
        for row in summary.near_duplicate_pairs[:20]:
            lines.append(f"- {row['incoming']} near {row['existing']} (score {row['score']})")
        lines.append("")
    if summary.new_atom_ids:
        lines.extend(["## New atom ids", ""])
        for atom_id in summary.new_atom_ids[:50]:
            lines.append(f"- {atom_id}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Import Quranic Studies teaching candidates into the knowledge corpus.")
    ap.add_argument("--input", required=True, type=Path, help="JSONL candidate file.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Report only. This is the default.")
    mode.add_argument("--apply", action="store_true", help="Write approved non-duplicate atoms into knowledge.db.")
    ap.add_argument("--near-threshold", type=float, default=0.72, help="Jaccard score that queues review.")
    ap.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    ap.add_argument("--md-report", type=Path, default=DEFAULT_MD_REPORT)
    args = ap.parse_args(argv)

    candidates, invalid = load_candidates(args.input)
    summary = import_candidates(candidates, apply=bool(args.apply), near_threshold=args.near_threshold)
    summary.candidates_seen += len(invalid)
    summary.invalid_lines = invalid
    write_reports(summary, json_path=args.json_report, md_path=args.md_report)
    print(
        f"{'applied' if args.apply else 'dry-run'}: {summary.new_atoms} new, {summary.already_in_corpus} existing, {summary.near_duplicates} near-duplicate hits"
    )
    print(f"report: {args.md_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
