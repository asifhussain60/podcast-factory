#!/usr/bin/env python3
"""multi_source_synthesis.py — N-source holistic editorial for merged audio books.

Generalizes holistic_editorial.py (single-source) to a SPINE corpus plus N
AUGMENTATION corpora. Routes here when orchestrator-state carries a `multi_source`
block (written by promote_staging_to_book.py); single-source books keep using
holistic_editorial.py.

Model (locked: "spine + curated merge + atoms"):
  - The spine (raw-extract.md) is the BACKBONE — reorganized, denoised, and
    language-enriched, exactly like the single-source path. The over-compression
    floor is measured against the SPINE word count only.
  - An augmentation passage is MERGED inline ONLY when it directly extends a
    ledgered spine teaching (genuine-gap rule, mirroring augment_book.py W1).
    Default = do NOT merge. Everything not merged is emitted as an atom candidate
    for Phase 0e to weave — never silently dropped, never silently inlined.

Passes (deterministic scaffolding around flat-rate `claude -p` calls):
  0. RE-TAG (deterministic) — rewrite each augmentation's `<!-- lecture N -->`
     markers to globally-unique `<!-- AUG:<name> lecture N -->` so every span is
     source-attributable before any LLM sees it.
  1. UNIFIED LEDGER — per-corpus teaching ledger (spine first, then each aug),
     concatenated in Python with namespaced ids + `source` tags.
  2. EDITORIAL MERGE — spine backbone + genuine-gap augmentation merge →
     unified-book.md (+ refined-english.md) + _reorg-map.md + _curation-log.md.
  3. FIDELITY GATE — 100% spine-teaching coverage AND every merged aug span
     traceable to a ledger teaching + its origin. Hard-fail (exit 3) otherwise.
  4. ATOM HANDOFF (deterministic) — emit _atom-candidates.jsonl (non-merged aug
     spans) for the enrichment pipeline.

Arabic integrity is snapshotted before Pass 2 and verified after Pass 3 — Arabic
script can only change via canonical injection or the Astro phonetic-view curation.

On success advances state to phase=0c (the Islamic resume point), exactly like
holistic_editorial.py. Idempotent: each pass skips if its output exists unless --force.

Usage:
  python3 scripts/podcast/multi_source_synthesis.py --slug <slug> [--skip-fidelity] [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _paths import REPO_ROOT, content_dir, find_content  # noqa: E402
from _authoring._core import _run_claude_p, _run_claude_p_with_retry  # noqa: E402
import arabic_integrity as _ai  # noqa: E402

LEDGER_TIMEOUT = 1800
LEDGER_BATCH_TIMEOUT = 900   # per ~10-lecture sub-batch; hung call → in-process retry/fallback
EDITORIAL_TIMEOUT = 3600
FIDELITY_TIMEOUT = 1800
# Enhanced edition must retain >= this fraction of the SPINE word count.
OVER_COMPRESSION_FLOOR = 0.45
# Large single-shot ledger calls on big corpora intermittently hang the claude CLI
# mid-stream; chunking each corpus into ~N-lecture sub-batches keeps every call short
# enough to finish (and each sub-batch is cached + retried). 0 disables chunking.
LEDGER_CHUNK_LECTURES = 10

_LEC_MARKER_RE = re.compile(r"<!--\s*lecture\s+(\d+)\s*-->", re.IGNORECASE)
_AUG_MARKER_RE = re.compile(r"<!--\s*AUG:[^\s]+\s+lecture\s+\d+\s*-->", re.IGNORECASE)


def _die(msg: str) -> int:
    print(f"multi_source_synthesis: {msg}", file=sys.stderr)
    return 2


def _info(msg: str) -> None:
    print(msg)


def _resolve_book_dir(slug: str) -> Path | None:
    hit = find_content(slug)
    if hit:
        return hit[2]
    cand = content_dir(slug)
    return cand if cand.exists() else None


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─────────────────────────────────────────────────────────────────────────────
# Pass 0 — deterministic re-tag
# ─────────────────────────────────────────────────────────────────────────────
def _retag_augmentation(book_dir: Path, manifest: list[dict[str, Any]],
                        *, force: bool) -> list[dict[str, Any]]:
    """Write `<name>/raw-extract.tagged.md` with globally-unique AUG markers.

    Returns the manifest enriched with the tagged path. Pure string rewrite.
    """
    out: list[dict[str, Any]] = []
    for m in manifest:
        name = m["name"]
        raw = book_dir / m["raw_extract"]
        tagged = raw.with_name("raw-extract.tagged.md")
        if not raw.is_file():
            _info(f"    ⚠ augmentation {name}: raw-extract missing ({_rel(raw)}); skipping")
            continue
        if not tagged.exists() or force:
            text = raw.read_text(encoding="utf-8")
            text = _LEC_MARKER_RE.sub(
                lambda mo, n=name: f"<!-- AUG:{n} lecture {mo.group(1)} -->", text)
            tagged.write_text(text, encoding="utf-8")
        out.append({**m, "tagged": tagged.relative_to(book_dir).as_posix()})
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Pass 1 — per-corpus ledger
# ─────────────────────────────────────────────────────────────────────────────
def _ledger_prompt(src: Path, out: Path, source_tag: str, marker_hint: str) -> str:
    return f"""You are extracting a TEACHING LEDGER from an Ismaili scholarly corpus transcript.

Read: {_rel(src)}

Write a JSON array to: {_rel(out)}

Each element is one KEY TEACHING — a doctrine, claim, definition, ruling, named authority,
scriptural anchor (Quran/hadith), or core argument. For each, output an object:
  {{"id": "T001", "teaching": "<one-sentence plain-English statement>",
    "kind": "doctrine|definition|claim|ruling|authority|scripture|argument",
    "source": "{source_tag}",
    "source_marker": "<the {marker_hint} the teaching first appears under>",
    "key_terms": ["<arabic-transliterated terms central to it>"]}}

Rules:
- Be COMPLETE: capture every distinct teaching, not a summary.
- One teaching per element; split compound teachings.
- Plain ASCII transliteration for Arabic terms (no diacritics).
- Output ONLY the JSON array to the file. No prose, no markdown fences.
"""


def _split_tagged_by_lectures(text: str, batch_size: int) -> list[str]:
    """Split an AUG-tagged transcript into batches of ~batch_size lecture blocks.

    Each batch string preserves its `<!-- AUG:<name> lecture N -->` markers + content,
    so per-batch ledgers stay source-attributable. Any preamble before the first marker
    rides with batch 1.
    """
    marks = list(_AUG_MARKER_RE.finditer(text))
    if not marks:
        return [text] if text.strip() else []
    # Block i spans from marker i to marker i+1 (last to EOF); preamble joins block 0.
    blocks: list[str] = []
    pre = text[: marks[0].start()]
    for i, mo in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        blocks.append(text[mo.start():end])
    if pre.strip():
        blocks[0] = pre + blocks[0]
    batches: list[str] = []
    for i in range(0, len(blocks), batch_size):
        batches.append("".join(blocks[i:i + batch_size]))
    return batches


def _corpus_ledger(book_dir: Path, name: str, tagged_path: Path, slice_out: Path,
                   text_dir: Path, *, force: bool) -> bool:
    """Build one augmentation corpus's ledger slice, chunked by lecture-range.

    Splits the corpus into ~LEDGER_CHUNK_LECTURES-lecture sub-batches, runs a retried
    ledger claude -p per batch (short enough to avoid the mid-stream hang large
    single-shot calls hit), then concatenates the batch JSON arrays into slice_out.
    Idempotent: cached batch files + an existing slice_out skip. Returns True on success.
    """
    if slice_out.exists() and not force:
        return True
    text = tagged_path.read_text(encoding="utf-8")
    batches = _split_tagged_by_lectures(text, LEDGER_CHUNK_LECTURES) if LEDGER_CHUNK_LECTURES else [text]
    batch_dir = tagged_path.parent
    all_items: list[Any] = []
    for bi, btext in enumerate(batches, 1):
        bfile = batch_dir / f"ledger-batch-{bi:02d}.tagged.md"
        bout = text_dir / f"_teaching-ledger.aug-{name}.batch{bi:02d}.json"
        if not bout.exists() or force:
            bfile.write_text(btext, encoding="utf-8")
            _info(f"    ledger: aug:{name} batch {bi}/{len(batches)} ...")
            rc, _o, err = _run_claude_p_with_retry(
                _ledger_prompt(bfile, bout, f"aug:{name}", f"<!-- AUG:{name} lecture N -->"),
                timeout=LEDGER_BATCH_TIMEOUT, book_dir=book_dir,
                phase="0a-synthesize", step=f"ledger-aug-{name}-b{bi:02d}", log=_info)
            if rc != 0 or not bout.exists():
                _die(f"augmentation ledger {name} batch {bi} failed (rc={rc}): {err[:300]}")
                return False
        try:
            all_items.extend(json.loads(bout.read_text(encoding="utf-8")))
        except Exception as e:
            _die(f"ledger {bout.name} is not valid JSON: {e}")
            return False
    slice_out.write_text(json.dumps(all_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def _build_unified_ledger(book_dir: Path, spine_raw: Path,
                          tagged_manifest: list[dict[str, Any]], *,
                          force: bool) -> tuple[list[dict[str, Any]], int] | None:
    text_dir = book_dir / "_system" / "source" / "text"
    text_dir.mkdir(parents=True, exist_ok=True)

    # spine
    spine_ledger = text_dir / "_teaching-ledger.spine.json"
    if not spine_ledger.exists() or force:
        _info("    ledger: spine ...")
        rc, _o, err = _run_claude_p(
            _ledger_prompt(spine_raw, spine_ledger, "spine", "<!-- lecture N -->"),
            timeout=LEDGER_TIMEOUT, book_dir=book_dir,
            phase="0a-synthesize", step="ledger-spine")
        if rc != 0 or not spine_ledger.exists():
            _die(f"spine ledger failed (rc={rc}): {err[:300]}")
            return None

    # each augmentation — chunked by lecture-range (avoids the mid-stream hang that
    # large single-shot ledger calls hit). Completed corpus slices skip entirely.
    for m in tagged_manifest:
        name = m["name"]
        led = text_dir / f"_teaching-ledger.aug-{name}.json"
        if led.exists() and not force:
            continue
        if not _corpus_ledger(book_dir, name, book_dir / m["tagged"], led, text_dir, force=force):
            return None

    # concatenate with namespaced ids
    merged: list[dict[str, Any]] = []
    spine_n = 0
    for prefix, path, src in (
        [("S", spine_ledger, "spine")]
        + [(f"A-{m['name']}", text_dir / f"_teaching-ledger.aug-{m['name']}.json", f"aug:{m['name']}")
           for m in tagged_manifest]
    ):
        if not path.is_file():
            continue
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            _die(f"ledger {path.name} is not valid JSON: {e}")
            return None
        for i, it in enumerate(items, 1):
            if not isinstance(it, dict):
                continue
            it = {**it, "id": f"{prefix}{i:03d}", "source": it.get("source", src)}
            merged.append(it)
            if src == "spine":
                spine_n += 1
    unified = text_dir / "_teaching-ledger.json"
    unified.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _info(f"    unified ledger: {len(merged)} teachings ({spine_n} spine, {len(merged)-spine_n} aug)")
    return merged, spine_n


# ─────────────────────────────────────────────────────────────────────────────
# Pass 2 — editorial merge
# ─────────────────────────────────────────────────────────────────────────────
def _editorial_prompt(book_dir: Path, spine_raw: Path, ledger: Path,
                      tagged_manifest: list[dict[str, Any]],
                      unified: Path, refined: Path, reorg: Path, curation: Path,
                      spine_words: int) -> str:
    aug_list = "\n".join(
        f"  - aug:{m['name']} -> {_rel(book_dir / m['tagged'])}" for m in tagged_manifest)
    lo = int(spine_words * 0.55)
    hi = int(spine_words * 0.95)
    return f"""You are the holistic editor of an Ismaili scholarly book built from lecture transcripts.

THE SPINE (the backbone — this IS the book):
- Faithful spine transcript: {_rel(spine_raw)}

AUGMENTATION CORPORA (other teachers on the SAME subject — supporting material ONLY):
{aug_list}

THE TEACHING LEDGER (fidelity contract; each item tagged source=spine or source=aug:<name>):
- {_rel(ledger)}

PRODUCE the enhanced reading edition. Write the SAME enhanced text to BOTH:
- {_rel(unified)}
- {_rel(refined)}

SPINE LATITUDE (granted on the spine): you MAY reorganize into a logical themed flow with H2
headings, denoise off-topic asides / filler / repetition / audio crosstalk, and enrich the
author's OWN language for reading.

AUGMENTATION MERGE RULE (strict — this is a curated merge, not a fusion):
- An augmentation passage may be merged INLINE *only* when it directly EXTENDS or DEEPENS a
  spine teaching that exists in the ledger (a genuine gap the spine leaves open). Default is to
  NOT merge. When you do merge, keep it brief and clearly in service of the spine teaching.
- DO NOT let augmentation reshape the book's backbone or introduce a doctrine the spine never
  raises. Augmentation that does not extend a ledgered spine teaching is NOT merged here — it
  will be handled later as an enrichment atom.

HARD LIMITS (fidelity contract): you MUST
- Preserve EVERY spine teaching at FULL DEPTH and undistorted (full exposition, reasoning,
  examples, scriptural support) — NOT a one-line mention.
- DO NOT SUMMARIZE the spine. LENGTH EXPECTATION: enhanced edition ~{lo:,}-{hi:,} words
  (denoise removes ~25-45% of spine oral redundancy). Dramatically shorter = summarization = FAILURE.
- Use plain ASCII transliteration for Arabic in prose; keep any Quran/Arabic quotations VERBATIM
  (do not alter Arabic script — it is restored canonically by a separate step).

ALSO write:
- {_rel(reorg)} — markdown table: | Section | Spine spans (<!-- lecture N -->) | Merged aug spans
  (aug:<name> lecture N) | Extends which ledger teaching (id) | — one row per H2 section. Every
  merged augmentation span MUST cite the ledger teaching id it extends.
- {_rel(curation)} — two parts: (1) spine denoise removals, each with a one-line reason; (2) an
  "## Augmentation disposition" table classifying EVERY augmentation lecture span as
  `merged-inline` / `atom` / `dropped` with a one-line reason. Close with:
  "Spine words: <N>  ->  Enhanced words: <M>".

Output files only; no chat response.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Pass 3 — fidelity gate
# ─────────────────────────────────────────────────────────────────────────────
def _fidelity_prompt(refined: Path, ledger: Path, reorg: Path, curation: Path,
                     coverage: Path, openq: Path) -> str:
    return f"""You are the FIDELITY GATE for a merged Ismaili book. Verify the editorial merge kept
faith with the SPINE and traced every merged augmentation span.

INPUTS:
- Enhanced text: {_rel(refined)}
- Teaching ledger (source-tagged): {_rel(ledger)}
- Reorg map (section -> source spans + ledger linkage): {_rel(reorg)}
- Curation log (augmentation disposition): {_rel(curation)}

Write a coverage report to: {_rel(coverage)}
A markdown table for SPINE teachings only (ledger items with source=spine):
  | Ledger ID | Teaching | Present? (yes/no) | At full depth? (yes/no) | Note |
"Present" requires the teaching's FULL exposition to survive. End with EXACTLY:
  "Coverage: <present>/<total> present, <full-depth>/<total> at full depth."
(<total> = number of source=spine ledger items.)

Then verify TRACEABILITY: every span the reorg map marks `merged-inline` (or lists under
"Merged aug spans") must (a) cite a ledger teaching id it extends and (b) be attributable to a
real `aug:<name> lecture N` origin. For EVERY spine teaching missing/distorted, OR any merged
augmentation span with no ledger linkage / untraceable origin / that introduces external doctrine,
APPEND to {_rel(openq)} under "## Fidelity-gate flags (multi-source synthesis)":
  - [<P0/P1>] <ledger id or aug span>: <what is wrong> — <recommended fix>

Output files only; no chat response.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Pass 4 — deterministic atom-candidate hand-off
# ─────────────────────────────────────────────────────────────────────────────
def _emit_atom_candidates(book_dir: Path, tagged_manifest: list[dict[str, Any]]) -> int:
    """Emit one candidate row per augmentation lecture block for Phase 0e to weave.

    Deterministic: splits each tagged augmentation transcript on its AUG markers.
    These are CANDIDATES — the enrichment pass (augment_book.py / ingest) selects
    which genuinely deepen a chapter; merged-inline passages are deduped there by
    the genuine-gap rule. Never silently dropped.
    """
    out = book_dir / "_system" / "source" / "augmentation" / "_atom-candidates.jsonl"
    rows: list[str] = []
    marker_re = re.compile(r"<!--\s*AUG:(?P<name>[^\s]+)\s+lecture\s+(?P<n>\d+)\s*-->", re.IGNORECASE)
    for m in tagged_manifest:
        tagged = book_dir / m["tagged"]
        if not tagged.is_file():
            continue
        text = tagged.read_text(encoding="utf-8")
        matches = list(marker_re.finditer(text))
        for i, mo in enumerate(matches):
            start = mo.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if not body:
                continue
            rows.append(json.dumps({
                "source": f"aug:{m['name']}",
                "marker": f"AUG:{m['name']} lecture {mo.group('n')}",
                "lecture": int(mo.group("n")),
                "chars": len(body),
                "text": body,
            }, ensure_ascii=False))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return len(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────
def run(slug: str, *, skip_fidelity: bool = False, force: bool = False) -> int:
    book_dir = _resolve_book_dir(slug)
    if book_dir is None:
        return _die(f"book workspace not found for slug {slug!r}")

    state_path = book_dir / "_system" / "orchestrator-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    ms = state.get("multi_source")
    if not ms:
        return _die("no multi_source block in state — run promote_staging_to_book.py first "
                    "(or use holistic_editorial.py for single-source books).")

    manifest_path = book_dir / ms.get("augmentation_manifest",
                                      "_system/source/augmentation/_manifest.json")
    if not manifest_path.is_file():
        return _die(f"augmentation manifest missing: {_rel(manifest_path)}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    spine_raw = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    if not spine_raw.is_file() or not spine_raw.read_text(encoding="utf-8").strip():
        return _die(f"spine master missing/empty: {_rel(spine_raw)}")

    text_dir = book_dir / "_system" / "source" / "text"
    unified = book_dir / "_system" / "unified-book.md"
    refined = text_dir / "refined-english.md"
    reorg = text_dir / "_reorg-map.md"
    curation = text_dir / "_curation-log.md"
    coverage = text_dir / "_teaching-ledger-coverage.md"
    openq = text_dir / "_open-questions.md"
    ledger = text_dir / "_teaching-ledger.json"

    # Pass 0 — re-tag
    _info("==> [0/4] Re-tagging augmentation markers (deterministic) ...")
    tagged_manifest = _retag_augmentation(book_dir, manifest, force=force)
    _info(f"    {len(tagged_manifest)} augmentation corpora tagged")

    # Pass 1 — unified ledger
    _info("==> [1/4] Building unified teaching ledger (claude -p, per corpus) ...")
    if ledger.exists() and not force:
        items = json.loads(ledger.read_text(encoding="utf-8"))
        spine_n = sum(1 for it in items if it.get("source") == "spine")
        _info(f"    ledger cached: {len(items)} teachings ({spine_n} spine)")
    else:
        res = _build_unified_ledger(book_dir, spine_raw, tagged_manifest, force=force)
        if res is None:
            return 2
        items, spine_n = res

    # Arabic baseline BEFORE the first mutating editorial pass.
    _info("==> Arabic integrity: snapshotting baseline ...")
    _ai.snapshot(slug, force=force)

    # Pass 2 — editorial merge
    spine_words = len(spine_raw.read_text(encoding="utf-8").split())
    if unified.exists() and refined.exists() and not force:
        _info("==> [2/4] Editorial merge cached (--force to redo)")
    else:
        _info("==> [2/4] Editorial merge — spine backbone + genuine-gap augmentation (claude -p) ...")
        rc, _o, err = _run_claude_p(
            _editorial_prompt(book_dir, spine_raw, ledger, tagged_manifest,
                              unified, refined, reorg, curation, spine_words),
            timeout=EDITORIAL_TIMEOUT, book_dir=book_dir,
            phase="0a-synthesize", step="editorial-merge")
        if rc != 0 or not refined.exists() or not unified.exists():
            return _die(f"editorial merge failed (rc={rc}): {err[:300]}")
        enhanced_words = len(refined.read_text(encoding="utf-8").split())
        ratio = enhanced_words / max(spine_words, 1)
        _info(f"    wrote refined-english.md ({enhanced_words:,} words = {ratio:.0%} of spine)")
        if ratio < OVER_COMPRESSION_FLOOR:
            _info(f"    ⚠ OVER-COMPRESSION: {ratio:.0%} of spine (<{OVER_COMPRESSION_FLOOR:.0%}) — "
                  f"that is summarization. NOT advancing; re-run the editorial.")
            return 3

    # Pass 3 — fidelity gate
    if skip_fidelity:
        _info("==> [3/4] fidelity gate SKIPPED (--skip-fidelity)")
    else:
        _info("==> [3/4] Fidelity gate — spine coverage + merged-span traceability (claude -p) ...")
        rc, _o, err = _run_claude_p(
            _fidelity_prompt(refined, ledger, reorg, curation, coverage, openq),
            timeout=FIDELITY_TIMEOUT, book_dir=book_dir,
            phase="0a-synthesize", step="fidelity-gate")
        if rc != 0 or not coverage.exists():
            return _die(f"fidelity gate failed (rc={rc}): {err[:300]}")
        cov = coverage.read_text(encoding="utf-8")
        last = cov.strip().splitlines()[-1].lower() if cov.strip() else ""
        _info("    " + (cov.strip().splitlines()[-1] if cov.strip() else "(coverage written)"))
        if "coverage:" in last:
            m = re.search(r"coverage:\s*(\d+)\s*/\s*(\d+)", last)
            if m and m.group(1) != m.group(2):
                _info(f"    ⚠ spine coverage incomplete ({m.group(1)}/{m.group(2)}) — see "
                      f"{_rel(openq)}. NOT advancing phase.")
                return 3

    # Arabic verify AFTER the editorial/fidelity passes.
    _info("==> Arabic integrity: verifying spans unchanged (phase 0a) ...")
    if _ai.verify(slug, "0a") == _ai.EXIT_FORBIDDEN:
        _info(f"    ⚠ R-ARABIC-INTEGRITY: forbidden Arabic mutation — see "
              f"_system/{_ai.REPORT_NAME}. NOT advancing phase.")
        return 3

    # Pass 4 — atom candidates
    _info("==> [4/4] Emitting augmentation atom candidates (deterministic) ...")
    n_cand = _emit_atom_candidates(book_dir, tagged_manifest)
    _info(f"    {n_cand} atom candidates → _system/source/augmentation/_atom-candidates.jsonl")

    # advance state
    now = _utc()
    state["last_completed_phase"] = "0a"
    state["phase"] = "0c"
    state["phase_status"] = "pending"
    state["last_error"] = None
    state["updated"] = now
    state.setdefault("phases", {})["0a-synthesize"] = {
        "completed_via": "multi_source_synthesis.py (claude -p)",
        "completed_at": now,
        "teachings_in_ledger": len(items),
        "spine_teachings": spine_n,
        "aug_teachings": len(items) - spine_n,
        "augmentation_corpora": len(tagged_manifest),
        "atom_candidates": n_cand,
    }
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _info("")
    _info("==> DONE. Merged edition ready; state advanced to phase=0c.")
    _info(f"    review: {_rel(refined)} + {_rel(reorg)} + {_rel(coverage)} + {_rel(openq)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--skip-fidelity", action="store_true", help="debug: skip the fidelity gate")
    ap.add_argument("--force", action="store_true", help="redo all passes, ignore caches")
    args = ap.parse_args()
    return run(args.slug, skip_fidelity=args.skip_fidelity, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
