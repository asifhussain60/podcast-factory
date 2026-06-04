"""intelligence/dedup_corpus.py — tiered corpus dedup engine (WC1, decision D7).

Source-agnostic. Scans atoms already in knowledge.db, finds exact and
near-duplicate teachings, and routes them by confidence tier:

  HIGH (exact text OR token-Jaccard >= --high, default 0.90)
        -> cluster; the most-complete atom is canonical; each other member is
           recorded as a variant of the canonical (atoms_variants, non-destructive)
           and queued as an auto-merge candidate (manual_review_queue,
           reason='corpus_dedup_high').
  BORDERLINE (--review <= Jaccard < --high, default 0.65..0.90)
        -> queued for human judgement (manual_review_queue,
           reason='corpus_dedup_review').
  below --review -> treated as distinct.

NON-DESTRUCTIVE by design: nothing is deleted or merged in place. Destructive
auto-merge (collapsing a cluster to one canonical atom) is deferred to the WC4
curation view, where a human confirms. This engine only DETECTS and RECORDS.

IDEMPOTENT: each run first clears its own prior output (manual_review_queue rows
whose reason starts 'corpus_dedup', and atoms_variants rows whose book_slug
starts 'corpus-dedup:'), then rewrites — so re-running never accumulates.

Comparisons are blocked by topic tag (atoms sharing a tag are compared) to keep
the pass tractable; atoms with no tags are blocked by their source corpus. Block
sizes above --max-block are reported and skipped rather than silently truncated.

CLI:
    python3 scripts/podcast/intelligence/dedup_corpus.py
    python3 scripts/podcast/intelligence/dedup_corpus.py --types doctrine --high 0.9 --review 0.65
    python3 scripts/podcast/intelligence/dedup_corpus.py --dry-run

Python API:
    from intelligence.dedup_corpus import dedup, DedupSummary
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _db import get_connection, run_migrations

VARIANT_BOOK_PREFIX = "corpus-dedup:"     # marks variants this engine wrote (idempotency)
REASON_HIGH = "corpus_dedup_high"
REASON_REVIEW = "corpus_dedup_review"
_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class _Atom:
    id: str
    text: str
    tags: tuple[str, ...]
    corpus: str
    tokens: frozenset[str] = field(default_factory=frozenset)
    norm: str = ""


@dataclass
class DedupSummary:
    atoms_scanned: int = 0
    blocks: int = 0
    pairs_compared: int = 0
    high_pairs: int = 0
    borderline_pairs: int = 0
    clusters: int = 0          # HIGH clusters with >1 member
    variants_written: int = 0
    review_high: int = 0
    review_borderline: int = 0
    skipped_blocks: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return _WORD_RE.sub(" ", text.lower()).strip()


def _tokens(norm: str) -> frozenset[str]:
    return frozenset(t for t in norm.split() if t)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / len(a | b)


def _extract_text(body_raw: str) -> str:
    """Atom bodies are JSON (doctrine: {text_en: ...}); fall back to raw string."""
    try:
        body = json.loads(body_raw)
    except (json.JSONDecodeError, TypeError):
        return body_raw or ""
    if isinstance(body, dict):
        return str(body.get("text_en") or body.get("text") or body.get("body") or "")
    return str(body)


# ---------------------------------------------------------------------------
# Union-find (cluster HIGH edges)
# ---------------------------------------------------------------------------

class _UF:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:        # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


# ---------------------------------------------------------------------------
# Loading + blocking
# ---------------------------------------------------------------------------

def _load_atoms(conn, types: tuple[str, ...]) -> list[_Atom]:
    placeholders = ",".join("?" for _ in types)
    rows = conn.execute(
        f"SELECT id, body, first_seen_book FROM atoms WHERE type IN ({placeholders})",
        types,
    ).fetchall()
    tag_rows = conn.execute("SELECT atom_id, tag FROM atom_topic_tags").fetchall()
    tags_by_atom: dict[str, list[str]] = {}
    for atom_id, tag in tag_rows:
        tags_by_atom.setdefault(atom_id, []).append(tag)

    atoms: list[_Atom] = []
    for atom_id, body_raw, corpus in rows:
        norm = _normalize(_extract_text(body_raw))
        atoms.append(_Atom(
            id=atom_id,
            text=norm,
            tags=tuple(sorted(tags_by_atom.get(atom_id, ()))),
            corpus=corpus or "?",
            tokens=_tokens(norm),
            norm=norm,
        ))
    return atoms


def _build_blocks(atoms: list[_Atom]) -> dict[str, list[_Atom]]:
    """Group atoms by each topic tag; tagless atoms grouped by their corpus."""
    blocks: dict[str, list[_Atom]] = {}
    for a in atoms:
        keys = [f"tag:{t}" for t in a.tags] or [f"corpus:{a.corpus}"]
        for k in keys:
            blocks.setdefault(k, []).append(a)
    return blocks


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def dedup(
    *,
    types: tuple[str, ...] = ("doctrine",),
    high: float = 0.90,
    review: float = 0.65,
    max_block: int = 600,
    dry_run: bool = False,
) -> DedupSummary:
    conn = get_connection()
    atoms = _load_atoms(conn, types)
    by_id = {a.id: a for a in atoms}
    summary = DedupSummary(atoms_scanned=len(atoms))

    blocks = _build_blocks(atoms)
    uf = _UF()
    seen_pairs: set[tuple[str, str]] = set()
    borderline: list[tuple[str, str, float]] = []

    for key, members in blocks.items():
        if len(members) < 2:
            continue
        if len(members) > max_block:
            summary.skipped_blocks.append(f"{key} ({len(members)} atoms > max-block {max_block})")
            continue
        summary.blocks += 1
        for a, b in combinations(members, 2):
            pair = (a.id, b.id) if a.id < b.id else (b.id, a.id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            summary.pairs_compared += 1
            sim = 1.0 if (a.norm and a.norm == b.norm) else _jaccard(a.tokens, b.tokens)
            if sim >= high:
                summary.high_pairs += 1
                uf.union(a.id, b.id)
            elif sim >= review:
                summary.borderline_pairs += 1
                borderline.append((pair[0], pair[1], round(sim, 4)))

    # Resolve HIGH clusters (size > 1).
    clusters: dict[str, list[str]] = {}
    for atom_id in {p for pr in seen_pairs for p in pr}:
        root = uf.find(atom_id)
        if root != atom_id or atom_id in uf.parent:
            clusters.setdefault(uf.find(atom_id), []).append(atom_id)
    clusters = {r: ids for r, ids in clusters.items() if len(ids) > 1}
    summary.clusters = len(clusters)

    if dry_run:
        summary.variants_written = sum(len(ids) - 1 for ids in clusters.values())
        summary.review_high = summary.variants_written
        summary.review_borderline = len(borderline)
        return summary

    # Idempotency: clear this engine's prior output before rewriting.
    conn.execute("DELETE FROM manual_review_queue WHERE reason LIKE 'corpus_dedup%'")
    conn.execute("DELETE FROM atoms_variants WHERE book_slug LIKE ?", (VARIANT_BOOK_PREFIX + "%",))

    for ids in clusters.values():
        # Canonical = most-complete (longest text), tie-break on id for determinism.
        canonical = max(ids, key=lambda i: (len(by_id[i].text), i))
        for dup_id in ids:
            if dup_id == canonical:
                continue
            dup = by_id[dup_id]
            conn.execute(
                "INSERT OR IGNORE INTO atoms_variants (atom_id, book_slug, text_en, translator)"
                " VALUES (?, ?, ?, 'corpus-dedup')",
                (canonical, VARIANT_BOOK_PREFIX + dup_id, dup.text),
            )
            summary.variants_written += 1
            conn.execute(
                "INSERT INTO manual_review_queue (book_slug, chapter_id, reason, payload)"
                " VALUES ('', '', ?, ?)",
                (REASON_HIGH, json.dumps({
                    "tier": "high", "canonical": canonical, "duplicate": dup_id,
                    "action": "auto-merge-candidate",
                }, ensure_ascii=False)),
            )
            summary.review_high += 1

    # Borderline pairs that did not collapse into the same HIGH cluster.
    for a_id, b_id, sim in borderline:
        if a_id in uf.parent and b_id in uf.parent and uf.find(a_id) == uf.find(b_id):
            continue
        conn.execute(
            "INSERT INTO manual_review_queue (book_slug, chapter_id, reason, payload)"
            " VALUES ('', '', ?, ?)",
            (REASON_REVIEW, json.dumps({
                "tier": "borderline", "atom_a": a_id, "atom_b": b_id, "similarity": sim,
                "action": "needs-human-judgement",
            }, ensure_ascii=False)),
        )
        summary.review_borderline += 1

    conn.commit()
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    run_migrations()
    p = argparse.ArgumentParser(description="Tiered corpus dedup engine (D7)")
    p.add_argument("--types", default="doctrine",
                   help="Comma list of atom types to scan (default: doctrine)")
    p.add_argument("--high", type=float, default=0.90, help="HIGH (auto-merge) Jaccard threshold")
    p.add_argument("--review", type=float, default=0.65, help="BORDERLINE (review) Jaccard threshold")
    p.add_argument("--max-block", type=int, default=600, help="Skip blocks larger than this")
    p.add_argument("--dry-run", action="store_true", help="Compute tiers without writing")
    args = p.parse_args()

    s = dedup(
        types=tuple(t.strip() for t in args.types.split(",") if t.strip()),
        high=args.high, review=args.review, max_block=args.max_block, dry_run=args.dry_run,
    )
    flag = " (dry-run)" if args.dry_run else ""
    print(f"Dedup{flag}:")
    print(f"  atoms scanned:        {s.atoms_scanned}")
    print(f"  blocks compared:      {s.blocks}  ({s.pairs_compared} pairs)")
    print(f"  HIGH clusters:        {s.clusters}  -> {s.variants_written} variants, {s.review_high} auto-merge candidates")
    print(f"  BORDERLINE for review: {s.review_borderline}")
    if s.skipped_blocks:
        print(f"  skipped blocks ({len(s.skipped_blocks)}): " + "; ".join(s.skipped_blocks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
