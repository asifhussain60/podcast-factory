#!/usr/bin/env python3
"""Import verified Kashkole binder translations into the knowledge corpus.

This is the binder-close bridge: a binder that has finished translation and
verification can be turned into doctrine atoms without creating duplicates.

The source of truth is ``content/knowledge-base/mirror.db``:

* ``fts_topics`` supplies the Urdu source metadata: binder, chapter, topic id.
* ``topic_translation`` supplies the verified English rendering and provenance.

The destination is ``content/knowledge-base/knowledge.db``.  The importer is
dry-run-first, idempotent, and chunk-based: long translated topics become
600-word doctrine atoms with stable ids under ``doctrine:kashkole:<topic>:<n>``.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import _db
from _paths import REPO_ROOT

from intelligence.kashkole_binder_import_core import (
    ALLOWED_CONTENT_LEVELS,
    ATOM_PREFIX,
    BINDER_CONFIGS,
    REVIEW_REASON,
    WISDOM_TRADITION,
    AtomCandidate,
    BinderConfig,
    ImportSummary,
    TopicRow,
    chunk_text,
    jaccard,
    normalize,
    quran_refs,
    slugify,
    tokens,
    topic_row_from_sql,
)

MIRROR = REPO_ROOT / "content" / "knowledge-base" / "mirror.db"
REPORT_DIR = REPO_ROOT / "_workspace" / "reviews" / "wisdom-audit" / "corpus-imports"


def _connect_mirror(path: Path = MIRROR) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def load_topics(mirror: sqlite3.Connection, binder: str, *, include_review: bool = False) -> tuple[int, list[TopicRow]]:
    total = mirror.execute("SELECT COUNT(*) FROM fts_topics WHERE binder=?", (binder,)).fetchone()[0]
    statuses = ("ok", "review") if include_review else ("ok",)
    placeholders = ",".join("?" * len(statuses))
    rows = mirror.execute(
        f"""
        SELECT
            t.topic_id, t.name, t.binder, t.chapter, t.body_plain,
            tr.name_en, tr.body_en, tr.source_sha, tr.source_chars, tr.output_chars,
            tr.windows, tr.model, tr.prompt_version, tr.standard_sha, tr.run_id,
            tr.translated_at, tr.status, tr.concerns
        FROM fts_topics t
        JOIN topic_translation tr ON tr.topic_id = t.topic_id
        WHERE t.binder = ? AND tr.status IN ({placeholders})
        ORDER BY t.topic_id
        """,
        (binder, *statuses),
    ).fetchall()
    return total, [topic_row_from_sql(row) for row in rows]


def build_candidates(topics: list[TopicRow], config: BinderConfig) -> list[AtomCandidate]:
    candidates: list[AtomCandidate] = []
    for topic in topics:
        chunks = chunk_text(topic.body_en)
        for idx, chunk in enumerate(chunks):
            atom_id = f"{ATOM_PREFIX}{topic.topic_id}:{idx}"
            candidates.append(
                AtomCandidate(
                    atom_id=atom_id,
                    text_en=chunk,
                    topic=topic,
                    chunk_index=idx,
                    chunk_count=len(chunks),
                    quran_refs=quran_refs(chunk),
                    config=config,
                )
            )
    return candidates


def _existing_doctrine_texts(conn) -> dict[str, str]:
    rows = conn.execute("SELECT id, body FROM atoms WHERE type='doctrine'").fetchall()
    out: dict[str, str] = {}
    for atom_id, body_raw in rows:
        try:
            body = json.loads(body_raw or "{}")
        except json.JSONDecodeError:
            body = {}
        text = body.get("text_en") or ""
        if text:
            out[str(atom_id)] = str(text)
    return out


def _near_duplicates(
    candidate: AtomCandidate,
    existing_tokens: dict[str, frozenset[str]],
    *,
    threshold: float,
) -> list[dict[str, Any]]:
    cand_tokens = tokens(candidate.text_en)
    rows = []
    for atom_id, atom_tokens in existing_tokens.items():
        score = jaccard(cand_tokens, atom_tokens)
        if score >= threshold:
            rows.append({"incoming": candidate.atom_id, "existing": atom_id, "score": round(score, 4)})
    rows.sort(key=lambda row: row["score"], reverse=True)
    return rows[:3]


def _missing_quran_atoms(conn, refs: Iterable[str]) -> list[str]:
    ids = [f"quran:{ref}" for ref in sorted(set(refs), key=lambda r: tuple(int(x) for x in r.split(":")))]
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    found = {r[0] for r in conn.execute(f"SELECT id FROM atoms WHERE id IN ({placeholders})", ids).fetchall()}
    return [i for i in ids if i not in found]


def _hydrate_quran_atoms(conn, mirror: sqlite3.Connection, missing_atom_ids: list[str]) -> int:
    """Insert only the canonical Quran atoms needed by this binder's quran_refs."""
    created = 0
    for atom_id in missing_atom_ids:
        try:
            _, surah_s, ayah_s = atom_id.split(":")
            surah, ayah = int(surah_s), int(ayah_s)
        except ValueError:
            continue
        row = mirror.execute(
            "SELECT surah, ayat, arabic, pickthall, asad, urdu, phonetic FROM fts_quran WHERE surah=? AND ayat=?",
            (surah, ayah),
        ).fetchone()
        if row is None:
            continue
        body = {
            "surah": surah,
            "ayah": ayah,
            "ayat": ayah,
            "arabic": row["arabic"],
            "text_en": row["pickthall"],
            "pickthall": row["pickthall"],
            "asad": row["asad"],
            "urdu": row["urdu"],
            "phonetic": row["phonetic"],
            "tradition": "universal",
        }
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO atoms
                (id, type, body, first_seen_book, first_seen_chapter, first_seen_date,
                 confidence, tradition, content_level)
            VALUES (?, 'quran', ?, 'quran', ?, ?, 1.0, 'universal', NULL)
            """,
            (atom_id, json.dumps(body, ensure_ascii=False, sort_keys=True), str(surah), date.today().isoformat()),
        )
        if conn.total_changes > before:
            created += 1
    return created


def import_binder(
    binder: str,
    *,
    apply: bool = False,
    include_review: bool = False,
    allow_partial: bool = False,
    allow_held: bool = False,
    hydrate_quran_refs: bool = False,
    near_threshold: float = 0.92,
    mirror_conn: sqlite3.Connection | None = None,
    knowledge_conn=None,
) -> ImportSummary:
    config = BINDER_CONFIGS.get(binder)
    summary = ImportSummary(binder=binder, dry_run=not apply)
    if config is None:
        summary.errors.append(f"No binder config for {binder!r}")
        return summary
    if config.content_level not in ALLOWED_CONTENT_LEVELS:
        summary.errors.append(f"Unsupported content level {config.content_level!r}")
        return summary
    if config.corpus_status == "held" and not allow_held:
        summary.errors.append(f"Binder {binder!r} is held pending atom-type decision")
        return summary

    mirror = mirror_conn or _connect_mirror()
    if knowledge_conn is None:
        _db.run_migrations()
        knowledge_conn = _db.get_connection()

    total, topics = load_topics(mirror, binder, include_review=include_review)
    summary.total_topics = total
    summary.translated_topics = len(topics)
    nonempty_topics = [t for t in topics if t.body_en.strip()]
    summary.empty_topics = len(topics) - len(nonempty_topics)
    summary.held_topics = max(0, total - len(topics))
    if total == 0:
        summary.errors.append(f"No source topics found for binder {binder!r}")
        return summary
    if len(topics) < total and not allow_partial:
        summary.errors.append(f"Binder is not complete: {len(topics)}/{total} eligible translated topics")
        return summary

    candidates = build_candidates(nonempty_topics, config)
    summary.eligible_topics = len(nonempty_topics)
    summary.candidates = len(candidates)
    summary.quran_refs = sum(len(c.quran_refs) for c in candidates)
    summary.missing_quran_atoms = _missing_quran_atoms(knowledge_conn, [r for c in candidates for r in c.quran_refs])
    if apply and hydrate_quran_refs and summary.missing_quran_atoms:
        summary.hydrated_quran_atoms = _hydrate_quran_atoms(knowledge_conn, mirror, summary.missing_quran_atoms)
        summary.missing_quran_atoms = _missing_quran_atoms(
            knowledge_conn, [r for c in candidates for r in c.quran_refs]
        )

    existing_texts = _existing_doctrine_texts(knowledge_conn)
    existing_norms = {normalize(text): atom_id for atom_id, text in existing_texts.items()}
    current_tokens = {atom_id: tokens(text) for atom_id, text in existing_texts.items()}
    seen_norms: dict[str, str] = {}

    for candidate in candidates:
        existing_id = knowledge_conn.execute("SELECT id FROM atoms WHERE id=?", (candidate.atom_id,)).fetchone()
        if existing_id:
            summary.existing_atoms += 1
            summary.existing_atom_ids.append(candidate.atom_id)
            if apply:
                _add_source_and_tags(knowledge_conn, candidate)
            current_tokens[candidate.atom_id] = tokens(candidate.text_en)
            continue

        norm = normalize(candidate.text_en)
        duplicate_of = seen_norms.get(norm) or existing_norms.get(norm)
        if duplicate_of:
            summary.exact_duplicates += 1
            summary.exact_duplicate_rows.append({"incoming": candidate.atom_id, "existing": duplicate_of})
            if apply:
                _add_source_and_tags(knowledge_conn, candidate, atom_id=duplicate_of)
            continue

        near = _near_duplicates(candidate, current_tokens, threshold=near_threshold)
        if near:
            summary.near_duplicates += len(near)
            summary.near_duplicate_rows.extend(near)
            if apply:
                _queue_near_duplicate_review(knowledge_conn, candidate, near)
            continue

        summary.new_atoms += 1
        summary.new_atom_ids.append(candidate.atom_id)
        seen_norms[norm] = candidate.atom_id
        current_tokens[candidate.atom_id] = tokens(candidate.text_en)
        if apply:
            _insert_atom(knowledge_conn, candidate)

    if apply:
        knowledge_conn.commit()
    return summary


def _insert_atom(conn, candidate: AtomCandidate) -> None:
    conn.execute(
        """
        INSERT INTO atoms
            (id, type, body, first_seen_book, first_seen_chapter, first_seen_date,
             confidence, tradition, content_level)
        VALUES (?, 'doctrine', ?, ?, ?, ?, 1.0, ?, ?)
        """,
        (
            candidate.atom_id,
            json.dumps(candidate.body(), ensure_ascii=False, sort_keys=True),
            candidate.source_book,
            candidate.source_chapter,
            date.today().isoformat(),
            WISDOM_TRADITION,
            candidate.config.content_level,
        ),
    )
    _add_source_and_tags(conn, candidate)


def _add_source_and_tags(conn, candidate: AtomCandidate, *, atom_id: str | None = None) -> None:
    target_id = atom_id or candidate.atom_id
    conn.execute(
        """
        INSERT OR IGNORE INTO atoms_sources (atom_id, book_slug, chapter_id, locator)
        VALUES (?, ?, ?, ?)
        """,
        (target_id, candidate.source_book, candidate.source_chapter, candidate.locator),
    )
    for tag in candidate.topic_tags():
        conn.execute("INSERT OR IGNORE INTO atom_topic_tags (atom_id, tag) VALUES (?, ?)", (target_id, tag))


def _queue_near_duplicate_review(conn, candidate: AtomCandidate, near: list[dict[str, Any]]) -> None:
    conn.execute(
        """
        INSERT INTO manual_review_queue (book_slug, chapter_id, reason, payload)
        VALUES (?, ?, ?, ?)
        """,
        (
            candidate.source_book,
            candidate.source_chapter,
            REVIEW_REASON,
            json.dumps(
                {"candidate_id": candidate.atom_id, "candidate": candidate.body(), "near": near}, ensure_ascii=False
            ),
        ),
    )


def write_reports(summary: ImportSummary, *, report_dir: Path = REPORT_DIR) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(summary.binder)
    suffix = "dry-run" if summary.dry_run else "applied"
    json_path = report_dir / f"{slug}-{suffix}.json"
    md_path = report_dir / f"{slug}-{suffix}.md"
    json_path.write_text(json.dumps(summary.as_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(_render_md(summary), encoding="utf-8")
    return json_path, md_path


def _render_md(summary: ImportSummary) -> str:
    lines = [
        f"# Kashkole binder import: {summary.binder}",
        "",
        f"Mode: {'dry run' if summary.dry_run else 'applied'}",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Source topics | {summary.total_topics} |",
        f"| Translated topics | {summary.translated_topics} |",
        f"| Eligible non-empty topics | {summary.eligible_topics} |",
        f"| Empty structural topics | {summary.empty_topics} |",
        f"| Held topics | {summary.held_topics} |",
        f"| Candidate chunks | {summary.candidates} |",
        f"| New atoms | {summary.new_atoms} |",
        f"| Existing atoms | {summary.existing_atoms} |",
        f"| Exact duplicates | {summary.exact_duplicates} |",
        f"| Near-duplicate review hits | {summary.near_duplicates} |",
        f"| Quran refs carried | {summary.quran_refs} |",
        f"| Hydrated Quran atoms | {summary.hydrated_quran_atoms} |",
        f"| Missing Quran atoms | {len(summary.missing_quran_atoms)} |",
        "",
    ]
    if summary.errors:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {e}" for e in summary.errors)
        lines.append("")
    if summary.missing_quran_atoms:
        lines.extend(["## Missing Quran atoms", ""])
        lines.extend(f"- {atom_id}" for atom_id in summary.missing_quran_atoms[:100])
        lines.append("")
    if summary.near_duplicate_rows:
        lines.extend(["## Near duplicates", ""])
        for row in summary.near_duplicate_rows[:100]:
            lines.append(f"- {row['incoming']} near {row['existing']} (score {row['score']})")
        lines.append("")
    if summary.new_atom_ids:
        lines.extend(["## New atom ids", ""])
        for atom_id in summary.new_atom_ids[:100]:
            lines.append(f"- {atom_id}")
        if len(summary.new_atom_ids) > 100:
            lines.append(f"- ... {len(summary.new_atom_ids) - 100} more")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Import a verified Kashkole binder translation into knowledge.db.")
    ap.add_argument("--binder", required=True, help="Exact Kashkole binder name.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Report only. Default.")
    mode.add_argument("--apply", action="store_true", help="Write eligible atoms.")
    ap.add_argument("--include-review", action="store_true", help="Include topic_translation status=review rows.")
    ap.add_argument("--allow-partial", action="store_true", help="Allow importing an incomplete binder.")
    ap.add_argument(
        "--allow-held", action="store_true", help="Allow importing binders marked held in the category map."
    )
    ap.add_argument(
        "--hydrate-quran-refs",
        action="store_true",
        help="On apply, insert only missing canonical quran:S:A atoms referenced by this binder.",
    )
    ap.add_argument("--near-threshold", type=float, default=0.92)
    args = ap.parse_args(argv)

    summary = import_binder(
        args.binder,
        apply=bool(args.apply),
        include_review=args.include_review,
        allow_partial=args.allow_partial,
        allow_held=args.allow_held,
        hydrate_quran_refs=args.hydrate_quran_refs,
        near_threshold=args.near_threshold,
    )
    _, md_path = write_reports(summary)
    print(
        f"{'applied' if args.apply else 'dry-run'}: {summary.new_atoms} new, "
        f"{summary.existing_atoms} existing, {summary.exact_duplicates} exact duplicates, "
        f"{summary.near_duplicates} near-duplicate hits"
    )
    if summary.errors:
        for error in summary.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"report: {md_path}")
        return 2
    print(f"report: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
