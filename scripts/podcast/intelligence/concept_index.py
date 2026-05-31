"""intelligence/concept_index.py — WC2 concept-derivation engine (decision D19).

Builds the CONCEPT layer behind the "Concept Lens": an English-meaningful concept
(keyed by Arabic root, or by a hadith theme) that aggregates atoms across every
source. This is the deterministic foundation — it derives concepts from the
metadata that already exists on the consolidated atoms:

  * ROOT concepts  — from `term` atoms (body.root) + `etymology` atoms (root parsed
    from the id, e.g. etymology:ilm -> "ilm"). Terms/etymology sharing a root merge
    into one concept; the Arabic root is the cross-source spine.
  * THEME concepts — from `hadith` atoms (body.collection holds a thematic label
    such as "soul", "tawheed", "intellect").

It does NOT invent metadata. Quran (no root/tag) and doctrine (no topic tags) atoms
are reported as UNMAPPED — closing that gap is the concept-enrichment pass (WC2
Part 2), tracked separately. Output is a derived JSON index (no DB mutation):
``content/knowledge-base/_index/concepts.json`` — rebuilt deterministically.

CLI:
    python3 scripts/podcast/intelligence/concept_index.py --stats   # read-only coverage report
    python3 scripts/podcast/intelligence/concept_index.py           # emit concepts.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _db import get_connection
from _paths import REPO_ROOT

INDEX_PATH = REPO_ROOT / "content" / "knowledge-base" / "_index" / "concepts.json"
SCHEMA_VERSION = 1


def _body(row) -> dict:
    try:
        return json.loads(row["body"])
    except Exception:
        return {}


def _slug(s: str) -> str:
    out, dash = [], False
    for ch in (s or "").strip().lower():
        if ch.isalnum():
            out.append(ch); dash = False
        elif not dash:
            out.append("-"); dash = True
    return "".join(out).strip("-")


def build_concepts(conn) -> dict:
    """Derive concepts from existing atom metadata. Returns the full index dict."""
    rows = conn.execute("SELECT id, type, body, tradition FROM atoms").fetchall()

    # root -> concept accumulator
    roots: dict[str, dict] = {}
    themes: dict[str, dict] = {}
    mapped: set[str] = set()
    unmapped_by_type: dict[str, int] = {}
    total = len(rows)

    def root_bucket(root: str) -> dict:
        return roots.setdefault(root, {
            "id": f"root:{root}", "kind": "root", "root": root,
            "label": "", "arabic": "", "translit": root, "definition": "",
            "synonyms": set(), "atom_ids": [], "by_type": {},
        })

    def add(bucket: dict, row, body: dict):
        bucket["atom_ids"].append(row["id"])
        bucket["by_type"][row["type"]] = bucket["by_type"].get(row["type"], 0) + 1
        mapped.add(row["id"])

    for row in rows:
        body = _body(row)
        t = row["type"]
        if t == "term":
            root = (body.get("root") or "").strip().lower()  # normalise case so variants merge
            if not root:
                unmapped_by_type[t] = unmapped_by_type.get(t, 0) + 1
                continue
            b = root_bucket(root)
            add(b, row, body)
            if body.get("term"):
                b["synonyms"].add(body["term"])
            if body.get("arabic") and not b["arabic"]:
                b["arabic"] = body["arabic"]
            # longest definition wins as the concept gloss
            d = (body.get("definition") or "").strip()
            if len(d) > len(b["definition"]):
                b["definition"] = d
        elif t == "etymology":
            # root is the id suffix: etymology:<root>
            root = (row["id"].split(":", 1)[1] if ":" in row["id"] else "").strip().lower()
            if not root:
                unmapped_by_type[t] = unmapped_by_type.get(t, 0) + 1
                continue
            b = root_bucket(root)
            add(b, row, body)
            d = (body.get("text_en") or body.get("definition") or "").strip()
            if d and len(b["definition"]) < 40:
                b["definition"] = d[:200]
        elif t == "hadith":
            theme = (body.get("collection") or "").strip()
            if not theme:
                unmapped_by_type[t] = unmapped_by_type.get(t, 0) + 1
                continue
            tb = themes.setdefault(_slug(theme), {
                "id": f"theme:{_slug(theme)}", "kind": "theme", "root": None,
                "label": theme, "arabic": "", "translit": "", "definition": f"Hadith on the theme of {theme}.",
                "synonyms": set([theme]), "atom_ids": [], "by_type": {},
            })
            add(tb, row, body)
        else:
            unmapped_by_type[t] = unmapped_by_type.get(t, 0) + 1

    # finalise labels + serialise sets
    concepts = []
    for b in list(roots.values()) + list(themes.values()):
        if b["kind"] == "root":
            gloss = b["definition"] or next(iter(b["synonyms"]), b["root"])
            b["label"] = f"{b['root']} — {gloss}" if gloss else b["root"]
        b["synonyms"] = sorted(b["synonyms"])
        b["atom_count"] = len(b["atom_ids"])
        concepts.append(b)
    concepts.sort(key=lambda c: (-c["atom_count"], c["id"]))

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_from": "knowledge.db (deterministic; term roots + etymology ids + hadith themes)",
        "concept_count": len(concepts),
        "coverage": {
            "total_atoms": total,
            "concept_mapped": len(mapped),
            "unmapped": total - len(mapped),
            "unmapped_by_type": unmapped_by_type,
            "note": "Quran + doctrine carry no root/tag metadata yet — concept-enrichment is WC2 Part 2.",
        },
        "concepts": concepts,
    }


def emit(index: dict, path: Path = INDEX_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_stats(index: dict) -> None:
    cov = index["coverage"]
    print(f"Concepts derived: {index['concept_count']}")
    print(f"Atoms: {cov['total_atoms']}  mapped: {cov['concept_mapped']}  unmapped: {cov['unmapped']}")
    print(f"Unmapped by type: {cov['unmapped_by_type']}")
    print("Top concepts:")
    for c in index["concepts"][:10]:
        print(f"  {c['id']:<22} {c['atom_count']:>3} atoms  {c['by_type']}")


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="WC2 concept-index builder (D19)")
    p.add_argument("--stats", action="store_true", help="Print coverage report; do not write the index")
    args = p.parse_args()
    index = build_concepts(get_connection())
    if args.stats:
        _print_stats(index)
        return 0
    emit(index)
    _print_stats(index)
    print(f"\nWrote {INDEX_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
