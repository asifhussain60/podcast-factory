"""_etymology_corpus.py — the Quranic-morphology grounding half of the etymology engine.

Split from ``_etymology.py`` (DR-005 line cap) 2026-07-28. Everything here is
deterministic and read-only: the corpus-backed veto reference, per-term root
resolution against ``morphology.db``, and the CORPUS GROUND TRUTH prompt block.
No LLM, no writes — ``_etymology`` composes these into its gate + generation.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from _buckwalter import arabic_fold, folds_match, latin_fold


def load_morphology_reference(db_path: Path | None = None) -> dict[str, set[str]]:
    """``{term_fold: {root_fold, ...}}`` from the Quranic morphology corpus.

    The strong half of the deterministic veto: ~3,000 human-annotated lemmas
    mapped to their ~1,600 roots (``morphology.db``, see quranic_morphology.py),
    keyed in the shared romanization fold space (``_buckwalter.latin_fold`` /
    ``arabic_fold``) so a glossary term like "tawakkul" lands on the same key as
    lemma توكل. An ambiguous fold keeps the UNION of its candidate roots, so
    ambiguity degrades to a permissive veto (under-firing), never a false one.
    Empty dict when the DB is absent — the legacy term_index and the adversarial
    verifier then carry the gate alone.
    """
    import quranic_morphology

    conn = quranic_morphology.open_db(db_path)
    if conn is None:
        return {}
    out: dict[str, set[str]] = {}
    try:
        rows = conn.execute(
            """SELECT l.lemma_skel, r.root_skel FROM lemmas l
               JOIN roots r ON l.root_bw = r.root_bw WHERE l.lemma_skel IS NOT NULL"""
        ).fetchall()
        for lemma_skel, root_skel in rows:
            key, root_fold = arabic_fold(lemma_skel or ""), arabic_fold(root_skel or "")
            if key and root_fold:
                out.setdefault(key, set()).add(root_fold)
        # A term may BE a root's own romanization ("rhm") — key roots by themselves.
        for (root_skel,) in conn.execute("SELECT root_skel FROM roots"):
            root_fold = arabic_fold(root_skel or "")
            if root_fold:
                out.setdefault(root_fold, set()).add(root_fold)
    except sqlite3.Error:
        return {}
    finally:
        conn.close()
    return out


# ─── Corpus grounding (deterministic; no LLM) ───────────────────────────────
_FAMILY_CAP = 8  # top lemmas per root injected into the prompt — grounding, not bloat


def _resolve_corpus_terms(candidates: list[tuple[str, int]], db_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """``{term: corpus record}`` for candidates resolvable to exactly ONE root.

    A term resolves when its romanization fold matches corpus lemma(s) that all
    share one root; any cross-root ambiguity → the term is left unresolved (the
    model path handles it, gated as before). Each record carries the canonical
    root (Arabic + Buckwalter + skeleton), the top derived lemmas with POS,
    occurrence counts and a first verse location, and the classical-lexicon
    entry for the root when one is ingested.
    """
    import quranic_morphology
    from lexicon_ingest import load_lexicon

    conn = quranic_morphology.open_db(db_path)
    if conn is None:
        return {}
    resolved: dict[str, dict[str, Any]] = {}
    try:
        rows = conn.execute(
            """SELECT l.lemma_skel, l.root_bw, r.root_ar, r.root_skel FROM lemmas l
               JOIN roots r ON l.root_bw = r.root_bw WHERE l.lemma_skel IS NOT NULL"""
        ).fetchall()
        by_fold: dict[str, list[tuple[str, str, str]]] = {}
        for lemma_skel, root_bw, root_ar, root_skel in rows:
            by_fold.setdefault(arabic_fold(lemma_skel or ""), []).append((root_bw, root_ar, root_skel))
        lexicon = load_lexicon()

        for term, _freq in candidates:
            fold = latin_fold(term)
            hits = [
                hit for lemma_fold, root_hits in by_fold.items() if folds_match(fold, lemma_fold) for hit in root_hits
            ]
            roots = {h[0] for h in hits}
            if len(roots) != 1:
                continue  # unknown or ambiguous — decline to ground, never guess
            root_bw, root_ar, root_skel = hits[0]
            family = [
                dict(r)
                for r in conn.execute(
                    """SELECT lemma_bw, lemma_ar, lemma_skel, pos, occurrence_count
                       FROM lemmas WHERE root_bw = ?
                       ORDER BY occurrence_count DESC, lemma_bw LIMIT ?""",
                    (root_bw, _FAMILY_CAP),
                ).fetchall()
            ]
            # SQLite pairs bare columns with MIN(): each lemma gets the row of
            # its FIRST occurrence in mushaf order.
            locations = {
                row[0]: row[1]
                for row in conn.execute(
                    """SELECT lemma_bw, chapter || ':' || verse || ':' || word,
                              MIN(chapter*1000000 + verse*1000 + word)
                       FROM segments WHERE root_bw = ? AND lemma_bw IS NOT NULL
                       GROUP BY lemma_bw""",
                    (root_bw,),
                ).fetchall()
            }
            for lem in family:
                lem["first_location"] = locations.get(lem["lemma_bw"], "")
            resolved[term] = {
                "root_bw": root_bw,
                "root_ar": root_ar,
                "root_skel": root_skel,
                "root_dashed": "-".join(root_skel),
                "family": family,
                "lexicon": lexicon.get(root_skel) or {},
            }
    except sqlite3.Error:
        return {}
    finally:
        conn.close()
    return resolved


def _grounding_block(resolved: dict[str, dict[str, Any]]) -> str:
    """The CORPUS GROUND TRUTH prompt section — authoritative roots + families."""
    if not resolved:
        return ""
    lines: list[str] = []
    for term, rec in resolved.items():
        fam = "; ".join(
            f"{lem['lemma_ar']} ({lem['lemma_bw']}"
            + (f", {lem['pos']}" if lem["pos"] else "")
            + f", {lem['occurrence_count']}x"
            + (f", first at {lem['first_location']}" if lem["first_location"] else "")
            + ")"
            for lem in rec["family"]
        )
        lines.append(f"- {term}: root {rec['root_dashed']} ({rec['root_ar']}). Derived words in the Quran: {fam}")
        lex = rec["lexicon"]
        if lex.get("lane_en"):
            lines.append(f"  Lane's Lexicon on this root: {lex['lane_en']}")
        if lex.get("maqayis_ar"):
            lines.append(f"  Ibn Faris (Maqayis) core sense: {lex['maqayis_ar']}")
        if lex.get("mufradat_ar"):
            lines.append(f"  al-Raghib (Mufradat): {lex['mufradat_ar']}")
    return (
        "\nCORPUS GROUND TRUTH (Quranic Arabic Corpus + classical lexica — AUTHORITATIVE)\n"
        "For every term listed below, the root is verified morphology data, not your recall.\n"
        "Use EXACTLY the given root; pick derivatives from the listed real derived words;\n"
        "when a lexicon gloss is given, base meaning_en on it.\n" + "\n".join(lines) + "\n"
    )
