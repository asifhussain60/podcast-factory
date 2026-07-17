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
    AuthoringError,
    ARABIC_SCHOLARLY_CATEGORIES,
    SKIP_PHONETICS_CATEGORIES,
    _read_category,
)
from _chunking import ChunkingError, concat_outputs, run_windowed, make_sdk_invoke_fn  # noqa: E402


def build_phase_0b_window_prompt_technical(
    book_slug: str,
    idx: int,
    total: int,
    win_in: "Path",
    win_out: "Path",
) -> str:
    """Phase 0b refinement prompt for technical/developer content (explainers category).

    Replaces the Arabic-preservation constraint with technical-content
    preservation rules: CLI commands, code blocks, version numbers, and
    official documentation quotes must survive the refinement pass unchanged.
    Marketing hyperbole and spec hedging are the noise targets.
    """
    return (
        f"You are driving Phase 0b (Technical Content Refinement) of the /podcast skill on "
        f"book-slug `{book_slug}`, **window {idx} of {total}**.\n\n"
        f"INPUT  (read this window only): `{win_in}`\n"
        f"OUTPUT (write the refined window here): `{win_out}`\n\n"
        f"This is one window in a sequence — DO NOT add chapter headings, intros, "
        f"summaries, or transitions. Refine only the prose in the INPUT file. If the "
        f"input begins with a `<!-- context-overlap -->` block, that is tail context "
        f"for continuity — DO NOT re-emit it in your output; resume cleanly after it.\n\n"
        f"**Page-marker invariant (CRITICAL).** The INPUT may contain `<!-- page N -->` "
        f"HTML comments. Preserve every one verbatim and in-place. Do NOT move, collapse, "
        f"renumber, or omit them.\n\n"
        f"REFINEMENT GOALS for technical content:\n"
        f"- Strip marketing hyperbole: remove phrases like 'revolutionary', 'game-changing', "
        f"  'paradigm-shifting', 'supercharge', 'unleash potential', 'seamlessly'.\n"
        f"- Strip spec hedging: remove 'may', 'might', 'could potentially', 'in some cases' "
        f"  when the source documentation states facts definitively.\n"
        f"- Improve prose flow for audio: break run-on sentences, clarify pronoun references, "
        f"  make clause order logical when read aloud.\n"
        f"- Do NOT invent content not present in the INPUT — technical accuracy is mandatory.\n\n"
        f"PRESERVATION RULES (must survive refinement unchanged):\n"
        f"- **CLI commands and shell syntax** — preserve exactly: `claude --version`, "
        f"  `npm install -g @anthropic-ai/claude-code`, `curl -fsSL ...`, etc.\n"
        f"- **Code blocks** — preserve all ` ``` ` fenced blocks and inline `backtick` code verbatim.\n"
        f"- **Version numbers** — preserve exactly: '4.6', '18.0', 'v1.99', '2026-05-24'.\n"
        f"- **Official product names** — preserve capitalisation: 'Claude Code', 'GitHub Copilot', "
        f"  'NotebookLM', 'VS Code', 'Model Context Protocol', 'MCP'.\n"
        f"- **URL references and file paths** — preserve exactly.\n"
        f"- **Direct quotes from official documentation** — preserve verbatim; mark with "
        f"  attribution context if it helps clarity.\n"
        f"- **Numeric claims** — preserve exact figures (token counts, percentages, dollar amounts); "
        f"  do NOT round or approximate.\n\n"
        f"Constraints:\n"
        f"- Do NOT modify any file other than `{win_out}`.\n"
        f"- Do NOT wrap output in code fences or add preamble like 'Here is the refined text:'.\n\n"
        f"Exit when `{win_out}` is non-empty."
    )


def build_phase_0b_window_prompt_narrative(
    book_slug: str,
    idx: int,
    total: int,
    win_in: "Path",
    win_out: "Path",
) -> str:
    """Phase 0b refinement prompt for narrative fiction (content_profile=fiction).

    Polishes translated narrative prose for fluent reading and listening: smooths
    seams left by windowed translation, keeps proper-name romanization consistent,
    and preserves verse/poetry passages. Carries NONE of the Arabic-term,
    scriptural-citation, honorific, or CLI/code preservation rules — those belong
    to scholarly or technical content. The marker invariant is CHAPTER markers
    (`<!-- chapter N -->` / chapter headings), since fiction sources carry chapter
    structure, not PDF page markers.
    """
    return (
        f"You are driving Phase 0b (Narrative Refinement) of the /podcast skill on "
        f"book-slug `{book_slug}`, **window {idx} of {total}**.\n\n"
        f"INPUT  (read this window only): `{win_in}`\n"
        f"OUTPUT (write the refined window here): `{win_out}`\n\n"
        f"This is one window in a sequence — DO NOT add chapter headings, intros, "
        f"summaries, or transitions not present in the INPUT. Refine only the prose in "
        f"the INPUT. If the input begins with a `<!-- context-overlap -->` block, that is "
        f"tail context for continuity — DO NOT re-emit it; resume cleanly after it.\n\n"
        f"**Chapter-marker invariant (CRITICAL).** Preserve every `<!-- chapter N -->` "
        f"HTML comment and every chapter heading verbatim and in-place. Do NOT move, "
        f"renumber, merge, or omit them — they are the downstream anchors for chapter "
        f"design (0d).\n\n"
        f"REFINEMENT GOALS for narrative fiction:\n"
        f"- Smooth seams left by windowed translation: fix abrupt tense or register "
        f"  shifts, clarify pronoun antecedents, make clause order read naturally aloud.\n"
        f"- Render dialogue and narration as fluent, vivid literary English while staying "
        f"  faithful to the events, imagery, and tone of the INPUT.\n"
        f"- Keep proper-name romanization consistent within the window (a character named "
        f"  once keeps that spelling throughout).\n"
        f"- Preserve verse/poetry passages as set-apart lines — render them as readable "
        f"  English verse; do NOT collapse them into prose or drop them.\n"
        f"- Do NOT invent plot, characters, or description not present in the INPUT — "
        f"  fidelity to the source narrative is mandatory.\n\n"
        f"Do NOT apply Arabic-term, scriptural-citation, or honorific rules — this is "
        f"narrative fiction, not religious scholarship. Do NOT preserve CLI commands, code "
        f"blocks, or version numbers — there are none.\n\n"
        f"Constraints:\n"
        f"- Do NOT modify any file other than `{win_out}`.\n"
        f"- Do NOT wrap output in code fences or add preamble like 'Here is the refined text:'.\n\n"
        f"Exit when `{win_out}` is non-empty."
    )


# De-calque rule (Book Pipeline v2): appended to the scholarly 0b prompt ONLY when
# book_pipeline_v2 is enabled for the book, so flag-OFF refinement is unchanged.
# It fixes the stiff word-for-word-from-Arabic prose that made book2 read like a
# gloss rather than a book — WITHOUT loosening fidelity (terms/citations/teachings
# are still mandatory to preserve).
_DE_CALQUE_BLOCK = (
    "\n\n**Fluent modern English (de-calque) — Book Pipeline v2.** Render the "
    "meaning in natural, idiomatic contemporary English. Do NOT calque the source "
    "syntax: avoid word-for-word constructions, Arabic word-order that reads "
    "awkwardly in English, and stiff literalisms. This is a fidelity-preserving "
    "restyle of the connective prose only — every teaching, argument, named person, "
    "Arabic term (kept in transliteration), Quran/hadith citation, and quotation "
    "MUST survive unchanged. Do not summarize, condense, or add. Aim for prose a "
    "modern reader follows easily on first read."
)


def build_phase_0b_window_prompt(
    book_slug: str,
    idx: int,
    total: int,
    win_in: Path,
    win_out: Path,
    *,
    de_calque: bool = False,
) -> str:
    """Construct the per-window refinement prompt sent to ``claude -p``.

    ``de_calque`` appends the fluent-English rule (scholarly variant only).
    """
    base = (
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
    return base + (_DE_CALQUE_BLOCK if de_calque else "")


def author_phase_0b(
    book_dir: Path,
    timeout: int = DEFAULT_TIMEOUT,
    *,
    window_words: int = PHASE_0B_WINDOW_WORDS,
    overlap_words: int = PHASE_0B_OVERLAP_WORDS,
    window_timeout: int = PHASE_0B_WINDOW_TIMEOUT,
    log=print,
    category: str | None = None,
) -> str:
    """Refine the source text — windowed. Routes to the correct prompt per category.

    category=None → auto-detected from _system/orchestrator-state.json / meta.yml.
    Islamic/scholarly categories: scholarly-tone refinement with Arabic preservation.
    explainers: technical-denoise (strip marketing, preserve CLI/code/version numbers).
    sites: web-consumer-denoise (strip legal jargon, re-voice for plain English).
    """
    if category is None:
        category = _read_category(book_dir)
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

    # Wave-Fiction: route by content_profile FIRST so a non-Islamic profile never
    # falls into the Arabic-preservation scholarly prompt. Fiction gets a dedicated
    # narrative prompt; every other profile keeps its prior category-based routing
    # byte-for-byte (no regression to Islamic / technical / sites / Guides books).
    from _content_profile import resolve_content_profile  # local import: avoid circularity
    _profile = resolve_content_profile(book_dir)
    _is_fiction = _profile == "fiction"
    _use_technical = (not _is_fiction) and category not in ARABIC_SCHOLARLY_CATEGORIES and category != "sites"
    _prompt_label = (
        "narrative" if _is_fiction
        else "technical" if _use_technical
        else "consumer" if category == "sites"
        else "scholarly"
    )
    log(f"  phase 0b · category={category!r}, content_profile={_profile!r}, prompt-variant={_prompt_label!r}")

    # The scholarly refinement de-calques stiff Arabic-calqued prose
    # (fidelity-preserving; only the scholarly variant carries the rule).
    _de_calque = True
    log("  phase 0b · de-calque (fluent modern English) rule active")

    def _builder(body: str, idx: int, total: int, win_out: Path) -> str:
        win_in = win_out.with_suffix("").with_suffix(".in.md")
        if _is_fiction:
            return build_phase_0b_window_prompt_narrative(book_slug, idx, total, win_in, win_out)
        if _use_technical:
            return build_phase_0b_window_prompt_technical(book_slug, idx, total, win_in, win_out)
        return build_phase_0b_window_prompt(
            book_slug, idx, total, win_in, win_out, de_calque=_de_calque)

    import os as _os
    _max_workers = int(_os.environ.get("PHASE_0B_MAX_WORKERS", "3"))
    _model = _os.environ.get("PHASE_0B_MODEL", "claude-sonnet-4-6")
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
            model=_model,
            max_workers=_max_workers,
            _invoke_fn=make_sdk_invoke_fn(_model),
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

    # Shift-left deterministic pre-check (Phase A). Flag-and-proceed: surfaces
    # length-drift / structural-collapse defects to the human 06a/0ci gate and
    # the findings ledger; NEVER raises, NEVER blocks. Zero LLM cost.
    try:
        from ._artifact_convergence import run_0b_precheck
        run_0b_precheck(book_dir, log=log)
    except Exception as _e:  # noqa: BLE001 — a precheck must never break 0b
        log(f"  phase 0b · precheck skipped (non-fatal: {_e!r})")

    return f"0b chunked: {len(out_paths)} windows merged into {out_path.name}"


def author_phase_0c(
    book_dir: Path,
    timeout: int = DEFAULT_TIMEOUT,
    *,
    log=print,
    category: str | None = None,
) -> str:
    """Phase 0c — glossary scaffold for Islamic scholarly content.

    Builds glossary.yml (phonetic field + Arabic-script overlay) used by the
    podcast-reader 'Show Arabic' toggle. Pronunciation respelling (the old
    _phonetics.md windowed extraction + EP00 probe) was retired 2026-06-08:
    NotebookLM reads hyphen-CAPS respellings literally. Term rendering is now
    handled by _tts_sanitize.sanitize_text_with_terms per chapter at authoring
    time, drawing on content/knowledge-base/exonyms.json + loanwords.json.

    SKIPPED for non-Islamic or skip-phonetics categories (no Arabic terms).
    """
    if category is None:
        category = _read_category(book_dir)

    if category in SKIP_PHONETICS_CATEGORIES:
        log(f"  phase 0c · SKIPPED (category={category!r} has no Arabic terms)")
        return f"0c skipped: category={category!r} does not require glossary scaffold"

    from _content_profile import is_islamic_scholarly, resolve_content_profile  # local import to avoid circularity
    if not is_islamic_scholarly(book_dir):
        profile = resolve_content_profile(book_dir)
        log(f"  phase 0c · SKIPPED (content_profile={profile!r} has no Arabic terms)")
        return f"0c skipped: content_profile={profile!r} does not require glossary scaffold"

    glossary_msg = _bake_glossary(book_dir, log=log)
    log(f"  phase 0c · glossary scaffold complete{glossary_msg}")
    return f"0c complete: glossary scaffold{glossary_msg}"


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


