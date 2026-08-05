#!/usr/bin/env python3
"""fill_glossary_arabic.py — populate arabic_script in BOOK_DIR/_system/glossary.yml.

PURPOSE

`build_glossary.py` emits a glossary.yml scaffold from _phonetics.md with
every `arabic_script` field empty. This script fires one `claude -p` call
per book with the empty glossary + the Arabic OCR raw-extract as context,
and writes the populated glossary back to disk. Idempotent: re-running
on an already-populated glossary is a no-op unless --force is passed.

INVOCATION

    python3 scripts/podcast/fill_glossary_arabic.py \\
        --book-dir content/drafts/the-master-and-the-disciple [--force]

INPUTS

    BOOK_DIR/_system/glossary.yml                  (required)
    BOOK_DIR/_system/source/ocr/raw-extract.md     (preferred) OR
    BOOK_DIR/_system/source/text/raw-extract.md    (fallback for books
                                                     whose Phase 0a wrote
                                                     the Arabic OCR directly
                                                     to the text/ folder)

OUTPUT

    BOOK_DIR/_system/glossary.yml — same file, with arabic_script filled.

COST

    One claude -p call per book (Sonnet by default — Arabic script extraction
    is content-recognition, not deep reasoning). Approximate spend: $0.05–0.15
    depending on glossary size + OCR length. Cost is logged to the book's
    _system/cost-ledger.jsonl.

INVARIANTS

    - Entries with an existing non-empty arabic_script are PRESERVED unless
      --force is passed. The LLM is instructed to only emit fills for the
      empty rows.
    - Output YAML preserves the original entry order from the input.
    - If the LLM emits a row that doesn't exist in the input, it is dropped
      with a warning. Hallucinations don't get committed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _glossary_io import dump_glossary, load_glossary


def _unq(s: str) -> str:
    """Strip outer double-quotes and unescape.

    Used ONLY on the model's reply in `parse_llm_yaml` — the glossary file itself
    is read by a real YAML parser now. Kept local because what the model emits is
    not a file format and does not deserve one.
    """
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    return s.replace('\\"', '"').replace("\\\\", "\\")


CLAUDE_CMD = "claude"
CLAUDE_TIMEOUT_S = 1800  # 30 min — bumped 2026-05-24 after 600s proved too tight for
# 75-entry / 106KB-OCR master-disciple. Sonnet streams output
# slower on long context windows than the dense per-entry
# processing rate suggests. 30 min absorbs the worst case.
MODEL = "claude-sonnet-4-6"
BATCH_SIZE = 40  # Max entries per LLM call. If a book has > BATCH_SIZE empty
# entries, split into multiple calls and merge results. Keeps
# each call's prompt small enough to finish within the timeout.


def parse_glossary_yml(path: Path) -> tuple[list[dict[str, str]], dict[str, object]]:
    """`(entries, top_level_fields)` — delegates to `_glossary_io`, the ONE reader.

    This was a hand-rolled line parser requiring `  - phonetic: "…"` exactly, and
    it returned ZERO entries for three of the five real glossaries once
    `_annotation_policy` began writing the `yaml.safe_dump` shape. `main()` below
    reads, fills, and WRITES BACK, so a zero-entry read on a 161-entry book wrote
    a glossary with `entries:` and nothing under it. Same for
    `phases/audio_driver.py`, `classify_term_defaults.py`, and
    `teaching_relevance_classifier.py`, which share this round-trip.
    """
    return load_glossary(path)


def emit_glossary_yml(entries: list[dict[str, str]], top: dict[str, object]) -> str:
    """Serialize through `_glossary_io`, the ONE writer.

    The hand-rolled version emitted five base fields plus a fixed `_V2_FIELDS`
    allow-list, so `annotation_class` / `annotation_reason` / `english_equivalent`
    — added later, elsewhere — were silently destroyed by any round-trip through
    this module. `dump_glossary` passes unknown keys through instead; do not
    reintroduce a field list here.
    """
    return dump_glossary(entries, top)


def build_prompt(empty_rows: list[dict[str, str]], ocr_text: str) -> str:
    rows_block = "\n".join(
        f'  - phonetic: "{r["phonetic"]}"  transliteration: "{r["transliteration"]}"  '
        f'first_seen_snippet: "{r["first_seen_snippet"]}"'
        for r in empty_rows
    )
    return (
        "You are filling in the Arabic-script column of a podcast-book glossary. "
        "For each row below, identify the Arabic script that the phonetic + "
        "transliteration + first-occurrence-snippet refer to, by searching the "
        "OCR text appended at the end.\n\n"
        "OUTPUT FORMAT — strict; one entry per row, in input order:\n"
        '  - phonetic: "<verbatim from input>"\n'
        '    arabic_script: "<the Arabic script as it appears in the OCR; '
        'preserve diacritics + spacing>"\n\n'
        "RULES\n"
        "  1. Phonetic value MUST match the input verbatim (used for join).\n"
        "  2. If you cannot find a confident match in the OCR, set arabic_script "
        'to the EMPTY string "" — do not guess. Empty fields stay empty in the '
        "glossary.\n"
        "  3. Do NOT emit any row whose phonetic is not in the input.\n"
        "  4. Do NOT emit prose around the YAML. Just the YAML block.\n"
        "  5. Entry order matches input order.\n\n"
        f"INPUT ROWS ({len(empty_rows)}):\n{rows_block}\n\n"
        f"OCR TEXT (Arabic source; page-marker lines prefixed with `<!-- page N -->`):\n"
        f"{ocr_text}\n"
    )


def parse_llm_yaml(raw: str) -> dict[str, str]:
    """Parse the LLM's output into {phonetic: arabic_script}. Ignores hallucinations."""
    out: dict[str, str] = {}
    current_phon: str | None = None
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("- phonetic:"):
            current_phon = _unq(s[len("- phonetic:") :].strip())
        elif s.startswith("arabic_script:") and current_phon is not None:
            val = _unq(s[len("arabic_script:") :].strip())
            out[current_phon] = val
            current_phon = None
    return out


def _normalize_taa_marbuta(entries: list[dict]) -> int:
    """A word-final taa marbuta (ة) is pronounced "h"/"ah", not "t"; the phonetic
    generator sometimes emits a trailing "t" (ri-yaat). Rewrite it to "h" so the
    audio says "ri-yaah". Idempotent; only entries whose Arabic ends in ة."""
    n = 0
    for e in entries:
        ar = str(e.get("arabic_script") or "").strip()
        ap = str(e.get("audio_phonetic") or "").strip()
        if ar.endswith("ة") and ap.endswith("t"):
            e["audio_phonetic"] = ap[:-1] + "h"
            n += 1
    return n


def corpus_fill(rows: list[dict[str, str]], ocr_text: str, db_path: Path | None = None) -> dict[str, str]:
    """Deterministic Quranic-lemma fill — corpus-guided, OCR-grounded, model-free.

    For each empty row, the romanized phonetic is matched against the Quranic
    morphology corpus lemmas (``morphology.db``) in the shared consonant-class
    fold space. Three guard rails, because the naive version of this would
    reintroduce fabricated script deterministically (Latin consonants map
    ambiguously: s→س/ص/ث, h→ه/ح/خ):

      1. class-level fold match (``_buckwalter.folds_match``);
      2. the match must be UNIQUE across all corpus lemma skeletons — any
         second candidate falls through to the model path;
      3. the winning lemma's skeleton must occur in the book's own OCR as a
         WHOLE WORD (bare, or carrying the definite article) — the corpus
         GUIDES the lookup, the book's pages remain the ground (the
         provenance-ladder rule). Whole-word, not substring: on live probing
         (the-master-and-the-disciple, 2026-07-28) a substring check let نقب
         "ground" inside النقباء and filled a different word than the term —
         the exact fabrication class these rails exist to stop.

    Fills are the UNVOWELLED form (harakat stripped, letters intact): glossary
    script prints inline beside terms, and a vowelled fill would land every
    annotation on the fabricated-vowelling review list. Returns
    ``{phonetic: arabic_script}``; empty dict when morphology.db is absent.
    """
    import quranic_morphology
    from _arabic_coverage import _ARABIC_TASHKEEL_RE, normalize_arabic
    from _buckwalter import folds_match, latin_fold

    conn = quranic_morphology.open_db(db_path)
    if conn is None:
        return {}
    try:
        lemma_rows = conn.execute(
            "SELECT lemma_ar, lemma_skel FROM lemmas WHERE lemma_skel IS NOT NULL AND lemma_skel != ''"
        ).fetchall()
    finally:
        conn.close()

    from _buckwalter import arabic_fold

    lemmas = [(arabic_fold(skel), str(ar), str(skel)) for ar, skel in lemma_rows]
    # Boundary-anchored word haystack (the _mushaf technique): each OCR word
    # normalized separately, space-padded, so ` needle ` can only match a word
    # the book actually prints — never a run inside a longer word.
    ocr_words = " " + " ".join(normalize_arabic(w) for w in ocr_text.split()) + " "
    fills: dict[str, str] = {}
    for r in rows:
        phon = str(r.get("phonetic") or "").strip()
        term = re.sub(r"^al-", "", phon, flags=re.IGNORECASE)
        fold = latin_fold(term)
        if len(fold) < 2:
            continue
        cand_skels = {skel for lf, _ar, skel in lemmas if folds_match(fold, lf)}
        if len(cand_skels) != 1:
            continue  # unknown or ambiguous — the model path (OCR-read) handles it
        skel = next(iter(cand_skels))
        if f" {skel} " not in ocr_words and f" ال{skel} " not in ocr_words:
            continue  # the book never prints this word standalone — decline
        vowelled = next(ar for lf, ar, s in lemmas if s == skel)
        # Printable bare form: harakat stripped, letters intact, and the corpus's
        # Uthmani alif wasla (ٱ) folded to the plain alif a modern glossary prints.
        bare = _ARABIC_TASHKEEL_RE.sub("", vowelled).replace("ٱ", "ا").strip()
        if len(bare) >= 3:
            fills[phon] = bare
    return fills


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--book-dir", required=True, type=Path)
    ap.add_argument("--force", action="store_true", help="Re-fill entries that already have arabic_script populated.")
    ap.add_argument("--dry-run", action="store_true", help="Print the prompt that would be sent; do not call the LLM.")
    args = ap.parse_args()

    book_dir: Path = args.book_dir.resolve()
    glossary_path = book_dir / "_system" / "glossary.yml"
    ocr_candidates = [
        book_dir / "_system" / "source" / "ocr" / "raw-extract.md",
        book_dir / "_system" / "source" / "text" / "raw-extract.md",
    ]
    # The vowelled copy when there is a current one: this is what puts marks on
    # `arabic_script` at its ROOT, so the terms the inline overlay weaves into the
    # English arrive already vowelled rather than waiting on a later pass.
    from _vowelled_source import resolve_arabic_source

    ocr_path = next((resolve_arabic_source(p) for p in ocr_candidates if p.exists()), None)
    if not glossary_path.exists():
        sys.stderr.write(f"glossary.yml not found at {glossary_path}\nRun scripts/podcast/build_glossary.py first.\n")
        return 2
    if ocr_path is None:
        sys.stderr.write(f"raw-extract.md not found in either:\n  {ocr_candidates[0]}\n  {ocr_candidates[1]}\n")
        return 3

    entries, top = parse_glossary_yml(glossary_path)
    if args.force:
        empty = entries
    else:
        empty = [r for r in entries if not r.get("arabic_script", "")]
    if not empty:
        print(f"all {len(entries)} entries already have arabic_script — nothing to fill", file=sys.stderr)
        return 0

    ocr_text = ocr_path.read_text(encoding="utf-8")

    # Deterministic corpus fill FIRST — zero cost, zero recall. Only rows whose
    # arabic_script is genuinely empty are eligible (even under --force, a
    # populated/curated script is never deterministically overwritten); whatever
    # the corpus cannot fill unambiguously goes to the model path as before.
    eligible = [r for r in empty if not r.get("arabic_script", "")]
    det_fills = corpus_fill(eligible, ocr_text)
    for r in eligible:
        script = det_fills.get(str(r.get("phonetic") or "").strip())
        if script:
            r["arabic_script"] = script
    if not args.force:
        empty = [r for r in empty if not r.get("arabic_script", "")]
    print(
        f"  corpus fill: {len(det_fills)} filled deterministically from the Quranic "
        f"morphology corpus, {len(empty)} to the model",
        file=sys.stderr,
    )
    if not empty:
        n_taa = _normalize_taa_marbuta(entries)
        if n_taa:
            print(f"  normalized {n_taa} taa-marbuta phonetics (-t -> -h)", file=sys.stderr)
        glossary_path.write_text(emit_glossary_yml(entries, top), encoding="utf-8")
        print(
            f"wrote {glossary_path.relative_to(book_dir)} — {len(det_fills)} entries filled "
            f"deterministically (total non-empty: {sum(1 for r in entries if r.get('arabic_script', ''))})",
            file=sys.stderr,
        )
        return 0

    if args.dry_run:
        # Show the prompt for the first batch only (rest are identical structure).
        print(build_prompt(empty[:BATCH_SIZE], ocr_text))
        return 0

    # Batch the empty entries so each LLM call's prompt stays small enough
    # to finish within CLAUDE_TIMEOUT_S. Sonnet's streaming rate drops as the
    # response gets longer; chunking keeps each call under the timeout.
    batches: list[list[dict[str, str]]] = [empty[i : i + BATCH_SIZE] for i in range(0, len(empty), BATCH_SIZE)]
    print(
        f"calling {MODEL} for {len(empty)} entries in {len(batches)} batch(es) "
        f"of ≤{BATCH_SIZE} (OCR {len(ocr_text):,} chars per call) …",
        file=sys.stderr,
    )

    all_fills: dict[str, str] = {}
    for i, batch in enumerate(batches, 1):
        prompt = build_prompt(batch, ocr_text)
        print(f"  batch {i}/{len(batches)} ({len(batch)} entries) …", file=sys.stderr)
        t0 = time.monotonic()
        try:
            result = subprocess.run(
                [CLAUDE_CMD, "-p", "--model", MODEL, prompt],
                capture_output=True,
                text=True,
                timeout=CLAUDE_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            sys.stderr.write(
                f"  batch {i} exceeded {CLAUDE_TIMEOUT_S}s timeout — partial "
                f"results from prior batches will still be written. Re-run "
                f"without --force to retry only the empty entries.\n"
            )
            break
        elapsed = time.monotonic() - t0
        if result.returncode != 0:
            sys.stderr.write(f"  batch {i} claude -p failed (rc={result.returncode}):\n{result.stderr[:600]}\n")
            break
        batch_fills = parse_llm_yaml(result.stdout)
        print(
            f"  batch {i}/{len(batches)} → {len(batch_fills)} fills in {elapsed:.1f}s",
            file=sys.stderr,
        )
        all_fills.update(batch_fills)

    # Merge fills into entries (preserve order, ignore unknown phonetics)
    by_phon = {r["phonetic"]: r for r in entries}
    n_filled = 0
    n_skipped_unknown = 0
    for phon, script in all_fills.items():
        if phon not in by_phon:
            n_skipped_unknown += 1
            continue
        if script:  # only update on non-empty
            by_phon[phon]["arabic_script"] = script
            n_filled += 1

    if n_skipped_unknown:
        print(f"  ⚠ {n_skipped_unknown} LLM-emitted rows had unknown phonetics; dropped", file=sys.stderr)

    n_taa = _normalize_taa_marbuta(entries)
    if n_taa:
        print(f"  normalized {n_taa} taa-marbuta phonetics (-t -> -h)", file=sys.stderr)

    glossary_path.write_text(emit_glossary_yml(entries, top), encoding="utf-8")
    print(
        f"wrote {glossary_path.relative_to(book_dir)} — {n_filled} entries filled "
        f"(total non-empty: {sum(1 for r in entries if r.get('arabic_script', ''))})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
