"""_authoring/refine.py — Phase 0b (English refinement) and Phase 0c (phonetics).

Extracted from _authoring.py (A4 split).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ._core import (  # noqa: E402
    DEFAULT_TIMEOUT,
    PHASE_0B_WINDOW_WORDS,
    PHASE_0B_OVERLAP_WORDS,
    PHASE_0B_WINDOW_TIMEOUT,
    PHASE_0C_WINDOW_WORDS,
    PHASE_0C_OVERLAP_WORDS,
    PHASE_0C_WINDOW_TIMEOUT,
    AuthoringError,
)
from _chunking import ChunkingError, concat_outputs, run_windowed  # noqa: E402


def build_phase_0b_window_prompt(
    book_slug: str,
    idx: int,
    total: int,
    win_in: Path,
    win_out: Path,
) -> str:
    """Construct the per-window refinement prompt sent to ``claude -p``."""
    return (
        f"You are driving Phase 0b (English Refinement) of the /podcast skill on book-slug "
        f"`{book_slug}`, **window {idx} of {total}**. Read the canonical Phase 0b procedure "
        f"from `skills-staging/podcast/SKILL.md` (search `### PHASE 0b: ENGLISH REFINEMENT`).\n\n"
        f"INPUT  (read this window only): `{win_in}`\n"
        f"OUTPUT (write the refined window here): `{win_out}`\n\n"
        f"This is one window in a sequence — DO NOT add chapter headings, intros, "
        f"summaries, or transitions that assume you have seen the whole book. Refine only "
        f"the prose in the INPUT file. If the input begins with a `<!-- context-overlap -->` "
        f"block, that is the tail of the prior window for continuity — DO NOT re-emit it "
        f"in your output; resume cleanly after it.\n\n"
        f"**Page-marker invariant (CRITICAL — P22.markers).** The INPUT contains "
        f"`<!-- page N -->` HTML comments — one before the prose extracted from each "
        f"source PDF page. You MUST preserve every `<!-- page N -->` comment verbatim "
        f"at the same relative position in the OUTPUT where it appears in the INPUT. "
        f"Do NOT collapse adjacent page markers. Do NOT renumber them. Do NOT omit any. "
        f"Do NOT invent new ones. Do NOT move them to the start or end of the output. "
        f"These markers are downstream anchors for content-range enforcement (P4.10), "
        f"per-page citation accuracy (P21), and operator navigation — refinement "
        f"without them silently breaks every downstream phase. If your refined prose "
        f"merges paragraphs across a page boundary, keep the `<!-- page N -->` comment "
        f"in place at the sentence boundary closest to where it originally sat.\n\n"
        f"Constraints (same as the whole-book Phase 0b — apply at the window scope):\n"
        f"- Do NOT modify any file other than `{win_out}`.\n"
        f"- Do NOT invent content not present in the INPUT — fidelity to the source is mandatory.\n"
        f"- Preserve every Arabic-derived term in transliteration form (al-Razi, al-Kirmani, etc.).\n"
        f"- Preserve every citation (verse references, hadith collection numbers).\n"
        f"- Preserve every `<!-- page N -->` HTML comment verbatim and in-place (see invariant above).\n"
        f"- Do NOT wrap output in code fences or add preamble like 'Here is the refined text:'.\n\n"
        f"Exit when `{win_out}` is non-empty."
    )


def author_phase_0b(
    book_dir: Path,
    timeout: int = DEFAULT_TIMEOUT,
    *,
    window_words: int = PHASE_0B_WINDOW_WORDS,
    overlap_words: int = PHASE_0B_OVERLAP_WORDS,
    window_timeout: int = PHASE_0B_WINDOW_TIMEOUT,
    log=print,
) -> str:
    """Refine the Azure-translated raw extract into clean English prose — windowed."""
    book_slug = book_dir.name
    in_path = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    out_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    chunks_dir = book_dir / "_system" / "source" / "text" / "_chunks" / "0b"

    if not in_path.exists():
        raise AuthoringError(
            phase="0b",
            message=f"prerequisite missing: {in_path} (Phase 0a should have produced this)",
            manual_fallback="Re-run Phase 0a or drop a manual raw-extract.md.",
        )

    raw_text = in_path.read_text(encoding="utf-8")

    def _builder(body: str, idx: int, total: int, win_out: Path) -> str:
        win_in = win_out.with_suffix("").with_suffix(".in.md")
        return build_phase_0b_window_prompt(book_slug, idx, total, win_in, win_out)

    import os as _os
    _max_workers = int(_os.environ.get("PHASE_0B_MAX_WORKERS", "3"))
    log(f"  phase 0b · chunked refinement (parallel max_workers={_max_workers})")
    try:
        out_paths = run_windowed(
            text=raw_text,
            chunks_dir=chunks_dir,
            prompt_builder=_builder,
            target_words=window_words,
            overlap_words=overlap_words,
            timeout_per_window=window_timeout,
            log=lambda m: log(m),
            book_dir=book_dir,
            phase="0b",
            max_workers=_max_workers,
        )
    except ChunkingError as e:
        raise AuthoringError(
            phase="0b",
            message=str(e),
            manual_fallback=e.manual_fallback or (
                "1. Inspect _chunks/0b/win-*.in.md and drive failed windows via /podcast.\n"
                "2. Drop each result at _chunks/0b/win-NNN.out.md.\n"
                "3. Re-invoke orchestrate-book --resume."
            ),
        ) from e

    try:
        merged = concat_outputs(out_paths)
    except ChunkingError as e:
        raise AuthoringError(
            phase="0b",
            message=str(e),
            manual_fallback=e.manual_fallback,
        ) from e

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(merged, encoding="utf-8")
    if out_path.stat().st_size == 0:
        raise AuthoringError(
            phase="0b",
            message=f"Phase 0b assembled artifact is empty: {out_path}",
            manual_fallback="Inspect _chunks/0b/win-*.out.md — at least one was non-empty but stitched to nothing.",
        )

    return f"0b chunked: {len(out_paths)} windows merged into {out_path.name}"


def author_phase_0c(
    book_dir: Path,
    timeout: int = DEFAULT_TIMEOUT,
    *,
    window_words: int = PHASE_0C_WINDOW_WORDS,
    overlap_words: int = PHASE_0C_OVERLAP_WORDS,
    window_timeout: int = PHASE_0C_WINDOW_TIMEOUT,
    log=print,
) -> str:
    """Add phonetic transcription for every Arabic / non-English term — windowed."""
    book_slug = book_dir.name
    in_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    out_path = book_dir / "_system" / "source" / "text" / "_phonetics.md"
    chunks_dir = book_dir / "_system" / "source" / "text" / "_chunks" / "0c"

    if not in_path.exists():
        raise AuthoringError(
            phase="0c",
            message=f"prerequisite missing: {in_path} (Phase 0b should have produced this)",
            manual_fallback="Run Phase 0b first.",
        )

    refined_text = in_path.read_text(encoding="utf-8")

    def _builder(body: str, idx: int, total: int, win_out: Path) -> str:
        win_in = win_out.with_suffix("").with_suffix(".in.md")
        return (
            f"You are driving Phase 0c (Arabic Phonetic Transcription Pass) of the /podcast skill "
            f"on book-slug `{book_slug}`, **window {idx} of {total}**. Read the canonical "
            f"procedure from `skills-staging/podcast/SKILL.md` (search `### PHASE 0c`).\n\n"
            f"INPUT  (read this window): `{win_in}`\n"
            f"AUTHORITY (the Arabic-manifest and name-alias handbook tree was retired in the\n"
            f"2026-05-23 restructure; if `content/_shared/arabic/*` exists in this repo it is\n"
            f"advisory only — otherwise rely on the rules inlined below and on this window's\n"
            f"own Arabic terms. For doctrinal naming (Imam lineage, 'Father of Imams', etc.)\n"
            f"see `content/_shared/islam/imam-lineage-ismaili.yml` and `naming-conventions.yml`).\n"
            f"OUTPUT (write the phonetic table for THIS window only): `{win_out}`\n\n"
            f"Output FORMAT — a markdown pipe table with EXACTLY this header:\n"
            f"```\n"
            f"| term | transliteration | phonetic | first-occurrence-snippet |\n"
            f"|---|---|---|---|\n"
            f"```\n"
            f"One row per unique Arabic-derived term in the INPUT. The shared manifest WINS — "
            f"copy its entries verbatim for any term it covers; add new rows only for terms it "
            f"doesn't carry.\n\n"
            f"Constraints:\n"
            f"- Do NOT modify any file other than `{win_out}`.\n"
            f"- Do NOT wrap output in code fences.\n"
            f"- If a term repeats within this window, emit it once.\n"
            f"- Per-window dedup only — cross-window dedup is handled by the orchestrator.\n\n"
            f"Exit when `{win_out}` contains a valid pipe table (header + at least zero rows; "
            f"emit just the header if the window has no Arabic terms)."
        )

    import os as _os
    _max_workers = int(_os.environ.get("PHASE_0C_MAX_WORKERS", "3"))
    log(f"  phase 0c · chunked phonetic extraction (parallel max_workers={_max_workers})")
    try:
        out_paths = run_windowed(
            text=refined_text,
            chunks_dir=chunks_dir,
            prompt_builder=_builder,
            target_words=window_words,
            overlap_words=overlap_words,
            timeout_per_window=window_timeout,
            log=lambda m: log(m),
            book_dir=book_dir,
            phase="0c",
            max_workers=_max_workers,
        )
    except ChunkingError as e:
        raise AuthoringError(
            phase="0c",
            message=str(e),
            manual_fallback=e.manual_fallback or (
                "1. Inspect _chunks/0c/win-*.in.md and drive failed windows via /podcast.\n"
                "2. Drop each result at _chunks/0c/win-NNN.out.md.\n"
                "3. Re-invoke orchestrate-book --resume."
            ),
        ) from e

    merged = _merge_phonetic_tables(out_paths)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(merged, encoding="utf-8")
    if out_path.stat().st_size == 0:
        raise AuthoringError(
            phase="0c",
            message=f"Phase 0c assembled artifact is empty: {out_path}",
            manual_fallback="Inspect _chunks/0c/win-*.out.md and merge manually.",
        )

    glossary_msg = _bake_glossary(book_dir, log=log)
    return f"0c chunked: {len(out_paths)} windows merged into {out_path.name}{glossary_msg}"


def _bake_glossary(book_dir: Path, *, log=print) -> str:
    """Generate BOOK_DIR/_system/glossary.yml + fill arabic_script from OCR."""
    here = Path(__file__).resolve().parents[1]  # scripts/podcast/
    builder = here / "build_glossary.py"
    filler = here / "fill_glossary_arabic.py"
    msg_parts: list[str] = []

    rc, out, err = _run([sys.executable, str(builder), "--book-dir", str(book_dir), "--force"])
    if rc == 0:
        msg_parts.append("scaffold")
    else:
        log(f"  phase 0c · glossary scaffold failed (rc={rc}): {err.strip()[:200]}")
        return ""

    rc, out, err = _run([sys.executable, str(filler), "--book-dir", str(book_dir)])
    if rc == 0:
        msg_parts.append("Arabic-fill")
    else:
        log(f"  phase 0c · glossary Arabic-fill skipped (rc={rc}): {err.strip()[:200]}")
    return f" + glossary: {' + '.join(msg_parts)}"


def _run(argv: list[str]) -> tuple[int, str, str]:
    """Local shellout helper."""
    import subprocess as _sp
    proc = _sp.run(argv, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _merge_phonetic_tables(paths: list[Path]) -> str:
    """Concatenate pipe-table outputs from windowed runs; dedup on first column."""
    import re as _re

    header = "| term | transliteration | phonetic | first-occurrence-snippet |"
    divider = "|---|---|---|---|"
    seen: dict[str, str] = {}
    order: list[str] = []

    row_re = _re.compile(r"^\s*\|\s*([^|]+?)\s*\|.*\|\s*$")
    for p in paths:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("```"):
                continue
            if s.startswith("| term ") or s.startswith("|---"):
                continue
            m = row_re.match(line)
            if not m:
                continue
            term = m.group(1).strip().strip("`").lower()
            if not term or term in seen:
                continue
            seen[term] = line.rstrip()
            order.append(term)

    body = "\n".join(seen[t] for t in order)
    return f"{header}\n{divider}\n{body}\n" if order else f"{header}\n{divider}\n"
