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


def _atom_display(row, body: dict) -> dict:
    """Project an atom into the English-meaning-first display shape the lens renders."""
    t = row["type"]
    tradition = body.get("tradition") or row["tradition"] or "universal"
    if t == "quran":
        s, a = body.get("surah"), body.get("ayat")
        gloss = (body.get("pickthall") or body.get("asad") or "").strip()
        return {"gloss": gloss, "source_ref": f"Q {s}:{a}", "arabic": body.get("arabic", ""), "corpus": "quran", "tradition": tradition}
    if t == "hadith":
        return {"gloss": (body.get("english") or body.get("text_en") or "").strip(),
                "source_ref": f"hadith · {body.get('collection','')}".rstrip(' ·'),
                "arabic": body.get("arabic", ""), "corpus": "hadith", "tradition": tradition}
    if t == "term":
        return {"gloss": (body.get("definition") or body.get("term") or "").strip(),
                "source_ref": f"term · {body.get('term','')}".rstrip(' ·'),
                "arabic": body.get("arabic", ""), "corpus": "quran", "tradition": tradition}
    if t == "etymology":
        return {"gloss": (body.get("text_en") or body.get("definition") or "")[:160].strip(),
                "source_ref": f"root · {row['id'].split(':',1)[-1]}",
                "arabic": body.get("arabic", ""), "corpus": "wisdom", "tradition": tradition}
    if t == "doctrine":
        txt = (body.get("text_en") or "").strip().lstrip("#").strip()
        return {"gloss": txt.split("\n")[0][:160], "source_ref": f"wisdom · {body.get('chapter_slug','')}".rstrip(' ·'),
                "arabic": "", "corpus": "wisdom", "tradition": tradition}
    if t == "poetry":
        return {"gloss": (body.get("text_en") or "")[:160].strip(), "source_ref": "poetry",
                "arabic": body.get("arabic", ""), "corpus": "wisdom", "tradition": tradition}
    return {"gloss": "", "source_ref": row["id"], "arabic": "", "corpus": "wisdom", "tradition": tradition}


def build_concepts(conn) -> dict:
    """Derive concepts from existing atom metadata. Returns the full index dict."""
    rows = conn.execute("SELECT id, type, body, tradition FROM atoms").fetchall()

    # root -> concept accumulator
    roots: dict[str, dict] = {}
    themes: dict[str, dict] = {}
    tags: dict[str, dict] = {}
    mapped: set[str] = set()
    unmapped_by_type: dict[str, int] = {}
    total = len(rows)

    # atom_id -> [tags] (from atom_topic_tags; populated by tag_doctrine_concepts.py et al.)
    tag_rows = conn.execute("SELECT atom_id, tag FROM atom_topic_tags").fetchall()
    tags_by_atom: dict[str, list[str]] = {}
    for tr in tag_rows:
        tags_by_atom.setdefault(tr["atom_id"], []).append(tr["tag"])

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

    def tag_bucket(tag: str) -> dict:
        return tags.setdefault(_slug(tag), {
            "id": f"tag:{_slug(tag)}", "kind": "tag", "root": None,
            "label": tag, "arabic": "", "translit": "", "definition": f"Atoms tagged “{tag}”.",
            "synonyms": {tag}, "atom_ids": [], "by_type": {},
        })

    for row in rows:
        body = _body(row)
        t = row["type"]

        # tag-concepts: any atom carrying topic tags (e.g. doctrine after tag_doctrine_concepts)
        for tag in tags_by_atom.get(row["id"], []):
            add(tag_bucket(tag), row, body)

        # root concepts (terms + etymology) — the Arabic-root spine
        if t == "term":
            root = (body.get("root") or "").strip().lower()  # normalise case so variants merge
            if root:
                b = root_bucket(root)
                add(b, row, body)
                if body.get("term"):
                    b["synonyms"].add(body["term"])
                if body.get("arabic") and not b["arabic"]:
                    b["arabic"] = body["arabic"]
                d = (body.get("definition") or "").strip()
                if len(d) > len(b["definition"]):
                    b["definition"] = d
        elif t == "etymology":
            root = (row["id"].split(":", 1)[1] if ":" in row["id"] else "").strip().lower()
            if root:
                b = root_bucket(root)
                add(b, row, body)
                d = (body.get("text_en") or body.get("definition") or "").strip()
                if d and len(b["definition"]) < 40:
                    b["definition"] = d[:200]
        elif t == "hadith":
            theme = (body.get("collection") or "").strip()
            if theme:
                tb = themes.setdefault(_slug(theme), {
                    "id": f"theme:{_slug(theme)}", "kind": "theme", "root": None,
                    "label": theme, "arabic": "", "translit": "", "definition": f"Hadith on the theme of {theme}.",
                    "synonyms": {theme}, "atom_ids": [], "by_type": {},
                })
                add(tb, row, body)

    # unmapped = atoms that landed in no concept at all
    for row in rows:
        if row["id"] not in mapped:
            unmapped_by_type[row["type"]] = unmapped_by_type.get(row["type"], 0) + 1

    # finalise labels + serialise sets; build atom_id -> [concept_ids]
    concepts = []
    atom_concepts: dict[str, list[str]] = {}
    for b in list(roots.values()) + list(themes.values()) + list(tags.values()):
        if b["kind"] == "root":
            gloss = b["definition"] or next(iter(b["synonyms"]), b["root"])
            b["label"] = f"{b['root']} — {gloss}" if gloss else b["root"]
        b["synonyms"] = sorted(b["synonyms"])
        b["atom_count"] = len(b["atom_ids"])
        for aid in b["atom_ids"]:
            atom_concepts.setdefault(aid, []).append(b["id"])
        concepts.append(b)
    concepts.sort(key=lambda c: (-c["atom_count"], c["id"]))

    # display records for every mapped atom (English-meaning-first), for the lens
    atoms_out = []
    for row in rows:
        if row["id"] not in mapped:
            continue
        body = _body(row)
        disp = _atom_display(row, body)
        atoms_out.append({
            "id": row["id"], "type": row["type"],
            "concepts": atom_concepts.get(row["id"], []),
            "root": (body.get("root") or "").strip().lower() or None,
            "text_en": (body.get("text_en") or disp["gloss"])[:400],
            **disp,
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_from": "knowledge.db (deterministic; term roots + etymology ids + hadith themes + atom_topic_tags)",
        "concept_count": len(concepts),
        "kinds": {"root": len(roots), "theme": len(themes), "tag": len(tags)},
        "coverage": {
            "total_atoms": total,
            "concept_mapped": len(mapped),
            "unmapped": total - len(mapped),
            "unmapped_by_type": unmapped_by_type,
            "note": "Quran carries no root/tag metadata yet; doctrine becomes mapped once tag_doctrine_concepts runs.",
        },
        "concepts": concepts,
        "atoms": atoms_out,
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
