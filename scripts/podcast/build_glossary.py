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

import _glossary_io
from _arabic_coverage import ARABIC_RE
from _glossary_io import load_glossary

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
    """Normalize parsed rows into glossary entries and serialize them.

    Serialization goes through `_glossary_io.dump_glossary` — the ONE writer
    (2026-08-02). This used to hand-roll the YAML AND carry a fixed list of
    optional fields to emit, so a field added anywhere else was silently dropped
    on the next rebuild. That is how the annotation policy was lost. What remains
    here is the part that is genuinely this module's job: deciding what a row
    MEANS before it becomes an entry.
    """
    entries: list[dict[str, str]] = []
    for r in rows:
        # The phonetic ANCHOR must be the ROMANIZED form that actually appears in
        # the chapters/scripts (R-PHONETICS-OUT bans inline phonetic respelling) —
        # chapter Arabic injection, the reader overlay, and the PLS dictionary
        # all match against this value. The `term` column is romanized for some
        # books but ARABIC SCRIPT for Arabic-sourced books; matching Arabic against
        # Latin text never fires (regression: asaas-al-taveel-vol-01, 2026-06-13).
        # So anchor on `transliteration` (always romanized), and when the `term`
        # column IS Arabic script, seed arabic_script from it for free.
        term = r.get("term", "")
        translit = r.get("transliteration", "")
        term_is_arabic = bool(ARABIC_RE.search(term))  # this was the base block only
        entry = {k: v for k, v in r.items() if k != "term"}
        entry.update(
            {
                "phonetic": translit or term,  # romanized anchor; term only as a last resort
                "transliteration": translit,
                "arabic_script": r.get("arabic_script", "") or (term if term_is_arabic else ""),
                "audio_phonetic": r.get("audio_phonetic", "") or r.get("phonetic", ""),
                "first_seen_snippet": r.get("first_seen_snippet", ""),
            }
        )
        entries.append({k: v for k, v in entry.items() if str(v or "").strip() or k in _glossary_io._LEAD_FIELDS})
    return _glossary_io.dump_glossary(entries, {"schema_version": 1})


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
#
# The annotation-policy trio was ABSENT from this list until 2026-08-02, which
# made a rebuild silently un-classify every term — and an unclassified term falls
# back to `legacy` in the inline-Arabic overlay, i.e. annotated once per CHAPTER
# instead of once per book. Losing them is not a cosmetic loss; it changes what
# the printed page looks like.
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
    "annotation_class",
    "annotation_reason",
    "english_equivalent",
)


def read_existing_curation(path: Path) -> dict[str, dict[str, str]]:
    """Curated fields from an existing glossary.yml, keyed by phonetic anchor.

    Reads through `_glossary_io`, the one reader (2026-08-02). This used to be a
    hand-rolled line matcher requiring `  - phonetic: "…"` exactly — two-space
    indent, quoted — and `_annotation_policy` had begun writing the file with
    `yaml.safe_dump`, which emits `- phonetic: x` at column 0. Both are valid
    YAML and neither reader used a YAML parser, so this returned **zero** for
    three of the five real glossaries and `--force` discarded every curated field
    on those books: the precise loss `_CURATED_FIELDS` exists to prevent.

    An absent file is still `{}` — "nothing to preserve". A malformed one now
    raises out of `load_glossary` rather than reading as empty, because reading a
    file you cannot parse as "no curation here" is how the curation was lost.
    """
    if not path.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    entries, _top = load_glossary(path)
    for entry in entries:
        anchor = str(entry.get("phonetic") or "").strip()
        if not anchor:
            continue
        for key in _CURATED_FIELDS:
            val = str(entry.get(key) or "").strip()
            if val:
                out.setdefault(anchor, {})[key] = val
    return out


def merge_curation(rows: list[dict[str, str]], curated: dict[str, dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    """Carry curated fields onto freshly parsed rows. Returns (rows, n_preserved).

    The anchor is the same romanized value emit_glossary_yaml uses (transliteration,
    falling back to term), so a rebuild matches the prior file row-for-row. A freshly
    parsed value never overwrites a curated one — the human's correction wins.

    UNION, not intersection (2026-08-02). This used to carry curated fields ONTO
    the fresh rows and return only those, so any entry absent from the fresh set
    was annihilated. `rows` comes from `_phonetics.md` — which nothing has written
    since it was retired on 2026-06-08 — or, failing that, from the 30-item
    `CANONICAL_FALLBACK_TERMS` list. So on a book whose glossary was built any
    other way, `--force` deleted almost all of it: `degrees-of-excellence`'s
    eleven hand-authored entries share not one term with the fallback. A prior
    entry the fresh parse does not know about is now KEPT, appended after the
    fresh rows, because a rebuild is supposed to refresh a glossary rather than
    replace the vocabulary it had learned.
    """
    preserved = 0
    seen: set[str] = set()
    for r in rows:
        anchor = (r.get("transliteration") or r.get("term") or "").strip()
        seen.add(anchor)
        prior = curated.get(anchor)
        if not prior:
            continue
        for key, val in prior.items():
            if not str(r.get(key, "") or "").strip():
                r[key] = val
        preserved += 1
    # Resurrections are NOT counted as `preserved`: that number means "fresh rows
    # that inherited curation", and the caller prints it as such.
    for anchor, prior in curated.items():
        if anchor in seen or not anchor:
            continue
        rows.append({"term": anchor, "transliteration": anchor, "phonetic": anchor, "first_seen_snippet": "", **prior})
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
