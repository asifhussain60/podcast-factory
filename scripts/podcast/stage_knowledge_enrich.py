"""stage_knowledge_enrich.py — WC8 knowledge stage: MCP-backed per-chapter enrichment.

Runs against all chapters (or one) for a given book slug.  For each chapter:

  Step 1 — Quran citations
    Load verified refs from _system/quran-citations.json; fetch full verse data
    (Arabic Uthmani script + Pickthall + Asad translations) via verify_quran_citation().

  Step 2 — Etymology annotation
    Scan normalized.md for Islamic technical terms (mapped from English surface forms
    to Arabic root transliterations).  Annotate top matches via get_etymology().

  Step 3 — Doctrine context
    Search KASHKOLE for chapter-relevant ethics / golden-sayings topics (TypeID 18+20
    only — tradition-adjacent universal Islamic ethics; Ismaili-specific types blocked).

  Step 4 — Write outputs
    Overwrite _stages/<ch>/knowledge-report.json with all findings.
    Replace the "## References" block at the bottom of augmented.md.

Zero LLM calls.  Pure local SQLite mirror lookups.  $0 cost.

CLI:
    python3 scripts/podcast/stage_knowledge_enrich.py --slug ayyuhal-walad
    python3 scripts/podcast/stage_knowledge_enrich.py --slug ayyuhal-walad --chapter ch02-hatim-eight-benefits
    python3 scripts/podcast/stage_knowledge_enrich.py --slug ayyuhal-walad --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for p in (str(_HERE), str(_REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.podcast.intelligence.mcp_access import (
    verify_quran_citation,
    get_etymology,
    get_doctrine_context,
    ENRICHMENT_TYPE_IDS,
)

# ── paths ─────────────────────────────────────────────────────────────────────

_DRAFTS = _REPO / "content" / "drafts" / "books"


def _book_dir(slug: str) -> Path:
    return _DRAFTS / slug


def _stage_dir(slug: str, chapter: str) -> Path:
    return _book_dir(slug) / "_stages" / chapter


# ── Islamic technical term map (English surface → transliteration for term_index) ──

_TERM_MAP: dict[str, str] = {
    "sincerity":     "ikhlas",
    "trust":         "tawakkul",
    "reliance":      "tawakkul",
    "repentance":    "tawbah",
    "patience":      "sabr",
    "gratitude":     "shukr",
    "soul":          "nafs",
    "heart":         "qalb",
    "knowledge":     "ilm",
    "worship":       "ibadah",
    "humility":      "tawadu",
    "asceticism":    "zuhd",
    "worldly":       "dunya",
    "heedlessness":  "ghaflah",
    "intention":     "niyyah",
    "fear":          "khawf",
    "hope":          "raja",
    "love":          "mahabbah",
    "remembrance":   "dhikr",
    "contemplation": "tafakkur",
    "path":          "tariqah",
    "station":       "maqam",
    "state":         "hal",
    "shaykh":        "shaykh",
    "scholar":       "alim",
}

_TERM_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _TERM_MAP) + r")\b",
    re.IGNORECASE,
)

# ── chapter theme seeds (for doctrine context search) ─────────────────────────

_CHAPTER_THEMES: dict[str, list[str]] = {
    "ch01": ["sincerity", "knowledge", "heart", "counsel"],
    "ch02": ["eight benefits", "soul", "trust", "sincerity", "tawakkul"],
    "ch03": ["path", "spiritual journey", "station", "patience"],
    "ch04": ["caution", "heedlessness", "heart", "deed", "intention"],
    "ch05": ["prayer", "method", "sincerity", "closing", "dua"],
}

_REF_SECTION_RE = re.compile(
    r"\n---\n\n## References in this chapter.*$",
    re.DOTALL,
)

# Matches "✅ Quran 2:255" or "✅ **2:255**" patterns in augmented.md
_EXISTING_REF_RE = re.compile(r"✅\s+(?:Quran\s+)?(\d+:\d+)")
# Matches "18:11", "7:179" inline — surah:ayat number pairs
_INLINE_REF_RE = re.compile(r"\b(\d{1,3}:\d{1,3})\b")


def _collect_chapter_refs(slug: str, chapter: str) -> list[str]:
    """Return refs for this chapter from augmented.md markers or knowledge-report.json."""
    stage = _stage_dir(slug, chapter)
    refs: list[str] = []

    # Source 1: existing augmented.md has "✅ Quran N:N" markers
    aug_md = stage / "augmented.md"
    if aug_md.exists():
        for match in _EXISTING_REF_RE.finditer(aug_md.read_text()):
            r = match.group(1)
            if r not in refs:
                refs.append(r)

    # Source 2: existing knowledge-report.json quran_refs list (ch01 format)
    if not refs:
        kr = stage / "knowledge-report.json"
        if kr.exists():
            try:
                d = json.loads(kr.read_text())
                for entry in d.get("quran_refs", []):
                    r = entry.get("key") or entry.get("ref")
                    if r and r not in refs:
                        refs.append(r)
            except (json.JSONDecodeError, AttributeError):
                pass

    return refs


# ── Step 1: Quran citation enrichment ─────────────────────────────────────────

def _enrich_quran(
    slug: str,
    chapter: str,
) -> list[dict[str, Any]]:
    """Load chapter's Quran refs; fetch full verse data (Arabic + translations)."""
    raw_refs = _collect_chapter_refs(slug, chapter)

    enriched = []
    for ref in raw_refs:
        try:
            surah_s, ayat_s = ref.split(":")
            surah, ayat = int(surah_s), int(ayat_s)
        except (ValueError, AttributeError):
            continue

        verse = verify_quran_citation(surah, ayat)
        if verse:
            enriched.append({
                "ref":       ref,
                "surah_num": surah,
                "ayat_num":  ayat,
                "arabic":    verse.get("arabic", ""),
                "pickthall": verse.get("pickthall", ""),
                "asad":      verse.get("asad", ""),
                "phonetic":  verse.get("phonetic", ""),
                "status":    "verified",
                "source":    "kqur-mirror",
            })
        else:
            enriched.append({"ref": ref, "status": "not-found"})

    return enriched


# ── Step 2: Etymology annotation ──────────────────────────────────────────────

def _enrich_etymology(
    normalized_text: str,
    max_terms: int = 6,
) -> list[dict[str, Any]]:
    """Scan normalized text for Islamic technical terms; return etymology records."""
    found_terms: dict[str, int] = {}
    for match in _TERM_RE.finditer(normalized_text):
        surface = match.group(1).lower()
        transliteration = _TERM_MAP.get(surface, surface)
        found_terms[transliteration] = found_terms.get(transliteration, 0) + 1

    # Sort by frequency descending; take top N
    top_terms = sorted(found_terms.items(), key=lambda x: -x[1])[:max_terms]

    results = []
    for term, count in top_terms:
        record = get_etymology(term)
        if record and "root" in record:
            root = record["root"]
            results.append({
                "term":             term,
                "occurrences":      count,
                "root_arabic":      root.get("root_arabic", ""),
                "transliteration":  root.get("transliteration", term),
                "meaning_en":       root.get("meaning_en", ""),
                "meaning_ar":       root.get("meaning_ar", ""),
                "derivatives_count": len(record.get("derivatives", [])),
                "source":           record.get("source", "mirror"),
            })

    return results


# ── Step 3: Doctrine context ──────────────────────────────────────────────────

def _enrich_doctrine(
    chapter: str,
    max_topics: int = 3,
) -> list[dict[str, Any]]:
    """Fetch KASHKOLE ethics/aphorism topics relevant to the chapter theme."""
    chapter_prefix = chapter.split("-")[0]
    themes = _CHAPTER_THEMES.get(chapter_prefix, ["knowledge", "ethics"])

    results: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for theme in themes:
        topics = get_doctrine_context(
            theme,
            type_ids=ENRICHMENT_TYPE_IDS,
            limit=3,
        )
        for t in topics:
            tid = t.get("topic_id")
            if tid not in seen_ids:
                seen_ids.add(tid)
                results.append({
                    "topic_id":      tid,
                    "topic_type_id": t.get("topic_type_id"),
                    "name":          t.get("name", ""),
                    "binder":        t.get("binder", ""),
                    "chapter":       t.get("chapter", ""),
                    "matched_theme": theme,
                })
        if len(results) >= max_topics:
            break

    return results[:max_topics]


# ── Step 4: Write outputs ─────────────────────────────────────────────────────

def _build_knowledge_report(
    slug: str,
    chapter: str,
    quran_refs: list,
    etymology: list,
    doctrine: list,
) -> dict[str, Any]:
    meta_file = _book_dir(slug) / "_system" / "meta.yml"
    tradition = "unknown"
    if meta_file.exists():
        for line in meta_file.read_text().splitlines():
            if line.strip().startswith("tradition:"):
                tradition = line.split(":", 1)[1].strip()
                break

    verified_q = [r for r in quran_refs if r.get("status") == "verified"]

    return {
        "slug":               slug,
        "chapter":            chapter,
        "stage":              "knowledge-enriched",
        "chapter_tradition":  tradition,
        "enrichment_source":  "mcp-mirror (KQUR + KASHKOLE, zero LLM calls)",
        "quran_verified":     len(verified_q),
        "quran_refs":         quran_refs,
        "etymology_terms":    etymology,
        "doctrine_topics":    doctrine,
        "hadith_refs":        [],
        "hadith_note":        (
            "KQUR Ahadees are Ismaili tradition — not matched to Ghazali's "
            "Sunni Prophetic narrations.  Tradition filter correctly withholds injection."
        ),
    }


def _build_references_section(
    quran_refs: list,
    etymology: list,
    doctrine: list,
) -> str:
    lines = ["", "---", "", "## References in this chapter (knowledge stage — MCP enriched)", ""]

    # Quran
    verified = [r for r in quran_refs if r.get("status") == "verified"]
    not_found = [r for r in quran_refs if r.get("status") != "verified"]
    if verified:
        lines.append(f"**{len(verified)} Quran citation{'s' if len(verified) != 1 else ''} verified** (Arabic text + Pickthall/Asad translations from KQUR mirror)\n")
        for r in verified:
            ref = r["ref"]
            arabic = r.get("arabic", "")
            pickthall = r.get("pickthall", "")
            asad = r.get("asad", "")
            lines.append(f"- ✅ **{ref}** — {arabic}")
            if pickthall:
                lines.append(f"  - *Pickthall:* {pickthall[:200]}")
            if asad:
                lines.append(f"  - *Asad:* {asad[:200]}")
    if not_found:
        lines.append("")
        for r in not_found:
            lines.append(f"- ⚠️ {r['ref']} — not found in KQUR mirror")

    # Etymology
    if etymology:
        lines.append("")
        lines.append(f"**{len(etymology)} Islamic term{'s' if len(etymology) != 1 else ''} annotated** (KQUR Roots + Derivatives)\n")
        for e in etymology:
            ar = f" ({e['root_arabic']})" if e.get("root_arabic") else ""
            meaning = e.get("meaning_en", "")
            occ = e.get("occurrences", 1)
            lines.append(f"- **{e['term']}**{ar} — {meaning} ×{occ}")

    # Doctrine context
    if doctrine:
        lines.append("")
        lines.append(f"**{len(doctrine)} KASHKOLE wisdom topic{'s' if len(doctrine) != 1 else ''} matched** (ethics/aphorism topics — tradition-adjacent)\n")
        for d in doctrine:
            binder = d.get("binder", "")
            name = d.get("name", "")
            theme = d.get("matched_theme", "")
            lines.append(f"- [{d['topic_id']}] {name} (binder: {binder}, matched: {theme})")

    return "\n".join(lines)


def _update_augmented_md(aug_path: Path, ref_section: str) -> None:
    """Replace or append the References block in augmented.md."""
    if not aug_path.exists():
        return
    text = aug_path.read_text()
    if _REF_SECTION_RE.search(text):
        text = _REF_SECTION_RE.sub(ref_section, text)
    else:
        text = text.rstrip() + "\n" + ref_section
    aug_path.write_text(text)


# ── Main per-chapter runner ───────────────────────────────────────────────────

def enrich_chapter(
    slug: str,
    chapter: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run enrichment for one chapter. Returns the knowledge report dict."""
    stage = _stage_dir(slug, chapter)
    normalized = stage / "normalized.md"
    aug_md = stage / "augmented.md"
    kr_path = stage / "knowledge-report.json"

    if not normalized.exists():
        return {"error": f"normalized.md not found: {normalized}"}

    norm_text = normalized.read_text()

    print(f"  [{chapter}] Step 1 — Quran citations …", end=" ", flush=True)
    quran_refs = _enrich_quran(slug, chapter)
    print(f"{len([r for r in quran_refs if r.get('status') == 'verified'])} verified")

    print(f"  [{chapter}] Step 2 — Etymology …", end=" ", flush=True)
    etymology = _enrich_etymology(norm_text)
    print(f"{len(etymology)} terms")

    print(f"  [{chapter}] Step 3 — Doctrine context …", end=" ", flush=True)
    doctrine = _enrich_doctrine(chapter)
    print(f"{len(doctrine)} topics")

    report = _build_knowledge_report(slug, chapter, quran_refs, etymology, doctrine)

    if not dry_run:
        kr_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        ref_section = _build_references_section(quran_refs, etymology, doctrine)
        _update_augmented_md(aug_md, ref_section)
        print(f"  [{chapter}] ✅ Wrote knowledge-report.json + updated augmented.md")
    else:
        q = report["quran_verified"]
        e = len(report["etymology_terms"])
        d = len(report["doctrine_topics"])
        print(f"  [{chapter}] dry-run: would write {q} quran + {e} etymology + {d} doctrine")

    return report


def enrich_all(
    slug: str,
    dry_run: bool = False,
    only_chapter: str | None = None,
) -> None:
    """Enrich all chapters (or one) for a book slug."""
    stages_dir = _book_dir(slug) / "_stages"
    if not stages_dir.exists():
        print(f"No _stages/ directory found for {slug}")
        return

    chapters = sorted(d.name for d in stages_dir.iterdir() if d.is_dir())
    if only_chapter:
        chapters = [c for c in chapters if c == only_chapter or c.startswith(only_chapter)]
        if not chapters:
            print(f"Chapter '{only_chapter}' not found under {stages_dir}")
            return

    print(f"Enriching {len(chapters)} chapter(s) for '{slug}' {'(dry-run)' if dry_run else ''}")
    total_quran = total_etym = total_doctrine = 0
    for chapter in chapters:
        report = enrich_chapter(slug, chapter, dry_run=dry_run)
        if "error" not in report:
            total_quran += report.get("quran_verified", 0)
            total_etym += len(report.get("etymology_terms", []))
            total_doctrine += len(report.get("doctrine_topics", []))

    print()
    print(f"Total: {total_quran} Quran refs verified, "
          f"{total_etym} terms annotated, "
          f"{total_doctrine} doctrine topics matched")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="MCP-backed knowledge enrichment for pipeline chapters."
    )
    parser.add_argument("--slug", required=True,
                        help="Book slug, e.g. ayyuhal-walad")
    parser.add_argument("--chapter", default=None,
                        help="Restrict to one chapter (prefix or full name), e.g. ch02")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without writing files.")
    args = parser.parse_args()
    enrich_all(args.slug, dry_run=args.dry_run, only_chapter=args.chapter)


if __name__ == "__main__":
    _cli()
