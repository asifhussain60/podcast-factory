#!/usr/bin/env python3
"""build_glossary.py — derive BOOK_DIR/_system/glossary.yml from _phonetics.md.

PURPOSE

The podcast pipeline's Phase 0c emits _phonetics.md (a markdown table of
Arabic / proper-noun terms with transliteration + phonetic forms) so the
NotebookLM Customize prompt can steer host pronunciation. The chapters
uploaded to NotebookLM must never contain inline phonetic respelling
(R-PHONETICS-OUT), but Islamic scholarly chapters do persist Arabic script
beside the romanized term.

This script materializes a per-book `glossary.yml` consumed by deterministic
chapter Arabic injection, the Podcast Factory Astro Site reader overlay, and
the audio pronunciation path: each row pairs the romanized chapter anchor with
Arabic script, transliteration, and rendering metadata.

INVOCATION

    python3 scripts/podcast/build_glossary.py \\
        --book-dir content/drafts/the-master-and-the-disciple

INPUTS

    BOOK_DIR/_system/source/text/_phonetics.md   (required)
    BOOK_DIR/_system/source/ocr/raw-extract.md   (optional — used only as
                                                   a script-source hint for
                                                   downstream LLM-fill)
    BOOK_DIR/chapters/ch*.txt                    (fallback when _phonetics.md
                                                   is absent; scans a curated
                                                   canonical Arabic-term map)

OUTPUTS

    BOOK_DIR/_system/glossary.yml — per-book term overlay for the reader

The emitted YAML schema:

    - phonetic: Hujjah               # how the term renders in chapters/*.txt
      transliteration: Ḥujjah        # academic Latin transliteration
      arabic_script: ""              # Arabic native script; empty placeholder
                                     # until LLM-fill OR manual completion
      first_seen_snippet: "..."      # context from _phonetics.md (first match)

Reader / chapter behavior: `inject_chapter_arabic.py` scans chapter prose for
the `phonetic` value and persists `phonetic (Arabic)` in Islamic chapters. The
reader overlay avoids double-rendering terms that already carry an Arabic
parenthetical. Empty `arabic_script` fields are a P0 gap for Islamic books.

LLM-FILL PROTOCOL (separate, not invoked here)

To populate the arabic_script fields, a follow-up script `fill_glossary
_arabic.py` shells out to `claude -p` once per book with the glossary
+ raw-extract.md as context. That step is deferred to avoid rate-limit
pressure on a running orchestrator and to give Asif a manual review gate
before any LLM cost. Approximate cost: ~$0.05-0.15 per book.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CANONICAL_FALLBACK_TERMS: list[dict[str, str]] = [
    {
        "phonetic": "alam al-ruh",
        "transliteration": "alam al-ruh",
        "arabic_script": "عالم الروح",
        "audio_phonetic": "aa-lam al-rooh",
    },
    {
        "phonetic": "Imam al-Zaman",
        "transliteration": "Imam al-Zaman",
        "arabic_script": "إمام الزمان",
        "audio_phonetic": "i-maam az-za-maan",
    },
    {"phonetic": "Mukathir", "transliteration": "Mukathir", "arabic_script": "مُكَثِّر", "audio_phonetic": "mu-kath-thir"},
    {"phonetic": "tawhid", "transliteration": "tawhid", "arabic_script": "توحيد", "audio_phonetic": "taw-heed"},
    {"phonetic": "tanzih", "transliteration": "tanzih", "arabic_script": "تنزيه", "audio_phonetic": "tan-zeeh"},
    {"phonetic": "tajrid", "transliteration": "tajrid", "arabic_script": "تجريد", "audio_phonetic": "taj-reed"},
    {"phonetic": "ta'wil", "transliteration": "ta'wil", "arabic_script": "تأويل", "audio_phonetic": "ta-weel"},
    {
        "phonetic": "wilayah",
        "transliteration": "wilayah",
        "arabic_script": "ولاية",
        "audio_phonetic": "wi-laa-yah",
        "english_override": "allegiance",
    },
    {
        "phonetic": "amal",
        "transliteration": "amal",
        "arabic_script": "عَمَل",
        "audio_phonetic": "a-mal",
        "english_override": "action",
    },
    {"phonetic": "hudud", "transliteration": "hudud", "arabic_script": "حُدُود", "audio_phonetic": "hu-dood"},
    {"phonetic": "haykal", "transliteration": "haykal", "arabic_script": "هيكل", "audio_phonetic": "hay-kal"},
    {"phonetic": "ma'dhun", "transliteration": "ma'dhun", "arabic_script": "مأذون", "audio_phonetic": "ma-dhoon"},
    {"phonetic": "hujjah", "transliteration": "hujjah", "arabic_script": "حُجَّة", "audio_phonetic": "huj-jah"},
    {"phonetic": "da'i", "transliteration": "da'i", "arabic_script": "داعي", "audio_phonetic": "daa-ee"},
    {"phonetic": "surat", "transliteration": "surat", "arabic_script": "صورة", "audio_phonetic": "soo-rah"},
    {"phonetic": "basirah", "transliteration": "basirah", "arabic_script": "بصيرة", "audio_phonetic": "ba-see-rah"},
    {"phonetic": "Du'at", "transliteration": "Du'at", "arabic_script": "دعاة", "audio_phonetic": "du-aat"},
    {
        "phonetic": "Ilahiyyah",
        "transliteration": "Ilahiyyah",
        "arabic_script": "إلهية",
        "audio_phonetic": "i-laa-hiy-yah",
    },
    {"phonetic": "Hujjiyyah", "transliteration": "Hujjiyyah", "arabic_script": "حجية", "audio_phonetic": "huj-jiy-yah"},
    {
        "phonetic": "Hijabiyyah",
        "transliteration": "Hijabiyyah",
        "arabic_script": "حجابية",
        "audio_phonetic": "hi-jaab-iy-yah",
    },
    {
        "phonetic": "Khayaliyyah",
        "transliteration": "Khayaliyyah",
        "arabic_script": "خيالية",
        "audio_phonetic": "kha-yaa-liy-yah",
    },
    {
        "phonetic": "Fathiyyah",
        "transliteration": "Fathiyyah",
        "arabic_script": "فتحية",
        "audio_phonetic": "fath-iy-yah",
    },
    {"phonetic": "Jiddiyyah", "transliteration": "Jiddiyyah", "arabic_script": "جدية", "audio_phonetic": "jid-diy-yah"},
    {
        "phonetic": "Anza'iyyah",
        "transliteration": "Anza'iyyah",
        "arabic_script": "أنزعية",
        "audio_phonetic": "an-za-iy-yah",
    },
    {
        "phonetic": "Qa'imiyyah",
        "transliteration": "Qa'imiyyah",
        "arabic_script": "قائمية",
        "audio_phonetic": "qaa-i-miy-yah",
    },
    {"phonetic": "Jussiyyah", "transliteration": "Jussiyyah", "arabic_script": "جسية", "audio_phonetic": "jus-siy-yah"},
    {
        "phonetic": "Ahadiyyah",
        "transliteration": "Ahadiyyah",
        "arabic_script": "أحدية",
        "audio_phonetic": "a-ha-diy-yah",
    },
    {
        "phonetic": "Samadiyyah",
        "transliteration": "Samadiyyah",
        "arabic_script": "صمدية",
        "audio_phonetic": "sa-ma-diy-yah",
    },
    {"phonetic": "Huwiyyah", "transliteration": "Huwiyyah", "arabic_script": "هوية", "audio_phonetic": "hu-wiy-yah"},
]


def parse_phonetics_md(path: Path) -> list[dict[str, str]]:
    """Parse the pipe-table at _phonetics.md into a list of row dicts.

    Expected header: | term | transliteration | phonetic | first-occurrence-snippet |
    """
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, str]] = []
    header_seen = False
    for ln in lines:
        s = ln.strip()
        if not s.startswith("|"):
            continue
        if not header_seen:
            header_seen = True
            continue
        if set(s.replace("|", "").strip()) <= {"-", " ", ":"}:
            # divider row "|---|---|..."
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 4:
            continue
        rows.append(
            {
                "term": cells[0],
                "transliteration": cells[1],
                "phonetic": cells[2],
                "first_seen_snippet": cells[3],
            }
        )
    return rows


def emit_glossary_yaml(rows: list[dict[str, str]]) -> str:
    """Emit YAML by hand to avoid a pip dependency on PyYAML.

    Keeps the order stable; quotes strings; escapes nothing fancy because
    the source is already markdown-table-sanitized.
    """
    lines: list[str] = []
    lines.append("# Per-book glossary — phonetic ↔ Arabic-script source for chapters/reader/audio.")
    lines.append("# Generated by scripts/podcast/build_glossary.py.")
    lines.append("# Rows may come from _phonetics.md or the curated chapter-term fallback.")
    lines.append("# Empty arabic_script entries are a P0 gap for islamic_scholarly books.")
    lines.append("")
    lines.append("schema_version: 1")
    lines.append("entries:")
    for r in rows:
        # The phonetic ANCHOR must be the ROMANIZED form that actually appears in
        # the chapters/scripts (R-PHONETICS-OUT bans inline phonetic respelling) —
        # chapter Arabic injection, the reader overlay, and the PLS dictionary
        # all match against this value. The `term` column is romanized for some
        # books but ARABIC SCRIPT for Arabic-sourced books; matching Arabic against
        # Latin text never fires (regression: asaas-al-taveel-vol-01, 2026-06-13).
        # So anchor on `transliteration` (always romanized), and when the `term`
        # column IS Arabic script, seed arabic_script from it for free.
        term = r["term"]
        translit = r["transliteration"]
        phon = translit or term  # romanized anchor; term only as a last resort
        term_is_arabic = bool(re.search(r"[؀-ۿ]", term))
        arabic_seed = r.get("arabic_script", "") or (term if term_is_arabic else "")
        phon_audio = r.get("audio_phonetic", "") or r["phonetic"]
        snippet = r["first_seen_snippet"]
        lines.append(f'  - phonetic: "{_q(phon)}"')
        lines.append(f'    transliteration: "{_q(translit)}"')
        lines.append(f'    arabic_script: "{_q(arabic_seed)}"')
        lines.append(f'    audio_phonetic: "{_q(phon_audio)}"')
        lines.append(f'    first_seen_snippet: "{_q(snippet)}"')
        for field in (
            "teaching_relevance",
            "decision",
            "corrected_phonetic",
            "corrected_arabic",
            "english_override",
            "decided_by",
            "decided_at",
        ):
            val = str(r.get(field, "") or "").strip()
            if val:
                lines.append(f'    {field}: "{_q(val)}"')
    return "\n".join(lines) + "\n"


def rows_from_chapter_fallback(book_dir: Path) -> list[dict[str, str]]:
    """Build a glossary scaffold by scanning chapters for known Arabic terms.

    This is the post-2026-06-08 fallback for books whose retired phonetics pass
    never wrote _phonetics.md. It is intentionally conservative: only a curated
    high-confidence term map can emit Arabic script.
    """
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.exists():
        return []
    chapter_texts = [(p, p.read_text(encoding="utf-8")) for p in sorted(chapters_dir.glob("ch*.txt"))]
    rows: list[dict[str, str]] = []
    for term in CANONICAL_FALLBACK_TERMS:
        phonetic = term["phonetic"]
        pattern = re.compile(r"(?<![A-Za-z])" + re.escape(phonetic) + r"(?![A-Za-z])", re.I)
        snippet = ""
        for _, text in chapter_texts:
            match = pattern.search(text)
            if not match:
                continue
            start = max(0, match.start() - 55)
            end = min(len(text), match.end() + 55)
            snippet = re.sub(r"\s+", " ", text[start:end]).strip()
            break
        if snippet:
            rows.append(
                {
                    "term": phonetic,
                    "transliteration": term["transliteration"],
                    "phonetic": phonetic,
                    "arabic_script": term["arabic_script"],
                    "audio_phonetic": term["audio_phonetic"],
                    "english_override": term.get("english_override", ""),
                    "first_seen_snippet": snippet,
                }
            )
    return rows


def _q(s: str) -> str:
    """Escape `"` for YAML double-quoted strings; trim outer whitespace."""
    return s.replace("\\", "\\\\").replace('"', '\\"').strip()


# Fields a HUMAN (or an expensive LLM fill) owns. None of them can be re-derived
# from _phonetics.md — that source carries only term/transliteration/phonetic/
# snippet — so a rebuild that drops them destroys work it cannot recreate.
# `decided_by`/`decided_at` are what classify_term_defaults.py keys on to leave a
# human decision alone, which makes losing them doubly bad: the row silently
# becomes eligible for machine re-decision.
_CURATED_FIELDS = (
    "arabic_script",
    "audio_phonetic",
    "teaching_relevance",
    "decision",
    "corrected_phonetic",
    "corrected_arabic",
    "english_override",
    "decided_by",
    "decided_at",
)

_ENTRY_RE = re.compile(r'^\s*-\s+phonetic:\s*"(.*)"\s*$')
_FIELD_RE = re.compile(r'^\s+([a-z_]+):\s*"(.*)"\s*$')


def _unq(s: str) -> str:
    """Inverse of _q for the double-quoted scalars this file emits."""
    return s.replace('\\"', '"').replace("\\\\", "\\")


def read_existing_curation(path: Path) -> dict[str, dict[str, str]]:
    """Curated fields from an existing glossary.yml, keyed by phonetic anchor.

    Deliberately a minimal parser for the exact shape emit_glossary_yaml writes
    (this module avoids a PyYAML dependency on purpose). Anything it cannot parse
    is skipped rather than guessed — a malformed file must never silently drop
    curation, so callers treat an empty result as "nothing to preserve" only when
    the file itself is absent.
    """
    if not path.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    anchor = ""
    for line in path.read_text(encoding="utf-8").split("\n"):
        m = _ENTRY_RE.match(line)
        if m:
            anchor = _unq(m.group(1))
            continue
        if not anchor:
            continue
        f = _FIELD_RE.match(line)
        if not f:
            continue
        key, val = f.group(1), _unq(f.group(2)).strip()
        if key in _CURATED_FIELDS and val:
            out.setdefault(anchor, {})[key] = val
    return out


def merge_curation(rows: list[dict[str, str]], curated: dict[str, dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    """Carry curated fields onto freshly parsed rows. Returns (rows, n_preserved).

    The anchor is the same romanized value emit_glossary_yaml uses (transliteration,
    falling back to term), so a rebuild matches the prior file row-for-row. A freshly
    parsed value never overwrites a curated one — the human's correction wins.
    """
    preserved = 0
    for r in rows:
        anchor = (r.get("transliteration") or r.get("term") or "").strip()
        prior = curated.get(anchor)
        if not prior:
            continue
        for key, val in prior.items():
            if not str(r.get(key, "") or "").strip():
                r[key] = val
        preserved += 1
    return rows, preserved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--book-dir", required=True, type=Path)
    ap.add_argument(
        "--force",
        action="store_true",
        help="Rebuild an existing glossary.yml. Human curation (arabic_script, audio_phonetic, "
        "decision/corrected_*/english_override/decided_by/decided_at) is PRESERVED by anchor.",
    )
    ap.add_argument(
        "--reset-curation",
        action="store_true",
        help="With --force, ALSO discard prior curation instead of preserving it. Destructive; "
        "only for rebuilding a glossary whose curation is known to be wrong.",
    )
    args = ap.parse_args()

    book_dir: Path = args.book_dir.resolve()
    phonetics = book_dir / "_system" / "source" / "text" / "_phonetics.md"
    out_path = book_dir / "_system" / "glossary.yml"

    if out_path.exists() and not args.force:
        sys.stderr.write(
            f"Refusing to overwrite {out_path} — pass --force to regenerate.\n"
            f"NOTE: --force preserves human curation; add --reset-curation to discard it.\n"
        )
        return 3

    # Phase 0c calls this with --force on every refine run, so a rebuild MUST NOT
    # be the thing that erases hand-curated Arabic script and term decisions —
    # none of those fields are re-derivable from _phonetics.md.
    curated = {} if args.reset_curation else read_existing_curation(out_path)

    if phonetics.exists():
        rows = parse_phonetics_md(phonetics)
        source = "_phonetics.md"
    else:
        rows = rows_from_chapter_fallback(book_dir)
        source = "chapter fallback"
    if not rows:
        sys.stderr.write(f"No glossary rows parsed from {phonetics} and no fallback terms found in chapters.\n")
        return 4

    rows, preserved = merge_curation(rows, curated)

    out_path.write_text(emit_glossary_yaml(rows), encoding="utf-8")
    note = ""
    if curated:
        note = f" · curation preserved on {preserved}/{len(curated)} prior entries"
    elif args.reset_curation:
        note = " · prior curation DISCARDED (--reset-curation)"
    print(
        f"wrote {out_path.relative_to(book_dir)} — {len(rows)} entries from {source}{note}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
