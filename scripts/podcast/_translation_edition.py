"""Translation-edition compose orchestration.

This module defines the contract for a faithful, visually enhanced translation
PDF path. It is deliberately separate from ``content_profile``: the profile says
what the source is about; ``deliverable_mode`` says what product we are making.

R3 DR-005 split (2026-07-18): the config/contract predicates moved verbatim to
``_translation_contract.py`` and the deterministic text post-processing (seam
trim/dedup, prose normalization, output findings, monochrome SVG, crosswalk
builder) to ``_translation_text.py``. Every moved name is re-exported here
(`X as X`, the `_azure.py` pattern) so importers and test patch-targets keep
working unchanged. What REMAINS is the one thing that could not move without
smell: the `claude -p` retry/caching orchestration. The compose PROMPT moved to
``_translation_prompts.py`` on 2026-07-20 (DR-005 gate) and is re-exported here —
see that module for why the Spec-2 "prompt stays with its orchestration" precedent
does not apply to it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _arabic_coverage import (
    arabic_coverage_shortfall,
    arabic_run_spans,
)
from _authoring._core import AuthoringError, _run_claude_p_with_retry
from _book_compose import (
    _line_pages,
    _load_arabic_pages,
    _pages_for_ranges,
    _quran_anchor_block,
    _slice_source,
)
from _pipeline_flags import narrative_frame, narrator_subject

# R3 DR-005 re-exports — moved names, kept importable from this module.
from _translation_contract import (
    DEFAULT_VISUAL_STYLE as DEFAULT_VISUAL_STYLE,
)
from _translation_contract import (
    TRANSLATION_EDITION_MODE as TRANSLATION_EDITION_MODE,
)
from _translation_contract import (
    assert_translation_contract as assert_translation_contract,
)
from _translation_contract import (
    contract_findings as contract_findings,
)
from _translation_contract import (
    deliverable_mode as deliverable_mode,
)
from _translation_contract import (
    is_faithful_translation_deliverable as is_faithful_translation_deliverable,
)
from _translation_contract import (
    is_translation_edition as is_translation_edition,
)
from _translation_contract import (
    read_series_config as read_series_config,
)
from _translation_contract import (
    requires_monochrome_visuals as requires_monochrome_visuals,
)
from _translation_contract import (
    translation_policy as translation_policy,
)
from _translation_prompts import _compose_prompt as _compose_prompt
from _translation_text import (
    _adjacent_echo as _adjacent_echo,
)
from _translation_text import (
    _boundary_echo as _boundary_echo,
)
from _translation_text import (
    _compress_line_ranges as _compress_line_ranges,
)
from _translation_text import (
    _iter_source_windows as _iter_source_windows,
)
from _translation_text import (
    _overlap_tokens as _overlap_tokens,
)
from _translation_text import (
    _para_is_echo as _para_is_echo,
)
from _translation_text import (
    _slugify as _slugify,
)
from _translation_text import (
    _source_headings as _source_headings,
)
from _translation_text import (
    _split_paragraphs as _split_paragraphs,
)
from _translation_text import (
    _topic_hits as _topic_hits,
)
from _translation_text import (
    _translation_long_enough as _translation_long_enough,
)
from _translation_text import (
    _trim_seam_overlap as _trim_seam_overlap,
)
from _translation_text import (
    build_source_crosswalk as build_source_crosswalk,
)
from _translation_text import (
    dedupe_seam_paragraphs as dedupe_seam_paragraphs,
)
from _translation_text import (
    monochrome_svg as monochrome_svg,
)
from _translation_text import (
    normalize_translation_prose as normalize_translation_prose,
)
from _translation_text import (
    source_title_drift_findings as source_title_drift_findings,
)
from _translation_text import (
    translation_output_findings as translation_output_findings,
)
from _translit import simplify_transliteration

_COMPOSE_TIMEOUT = 900
_RETRY_TIMEOUT = 1350
_LONG_CHAPTER_WORDS = 4500


def _compose_one(
    title: str,
    body: str,
    previous_tail: str,
    book_dir: Path,
    label: str,
    log,
    *,
    arabic_src: str = "",
    quran_anchor: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    prompt = _compose_prompt(
        title,
        body,
        previous_tail,
        arabic_src=arabic_src,
        quran_anchor=quran_anchor,
        frame=frame,
        narrator=narrator,
    )
    rc, out, err = _run_claude_p_with_retry(
        prompt,
        timeout=_COMPOSE_TIMEOUT,
        book_dir=book_dir,
        phase="0book-compose",
        step=f"translation-{label}",
        log=log,
    )
    out = (out or "").strip()
    if rc != 0:
        raise AuthoringError(
            phase="0book-compose",
            message=f"{label}: translation edition compose failed rc={rc}: {err[:300]}",
            manual_fallback="Re-run the translation edition path; completed chunks are skipped.",
        )
    source_words = len(body.split())
    if source_words >= 200 and len(out.split()) < 0.55 * source_words:
        log(f"      {label}: short ({len(out.split())}/{source_words}w) - retry")
        rc2, out2, _ = _run_claude_p_with_retry(
            prompt + "\n\nYour previous attempt was too compressed. Rewrite faithfully, preserving the full teaching.",
            timeout=_RETRY_TIMEOUT,
            book_dir=book_dir,
            phase="0book-compose",
            step=f"translation-{label}-retry",
            log=log,
        )
        if rc2 == 0 and len((out2 or "").split()) > len(out.split()):
            out = (out2 or "").strip()
    findings = translation_output_findings(
        out, expected_title=title, frame=frame, narrator_subject=narrator, source=body
    )
    if findings:
        log(f"      {label}: invalid translation output ({'; '.join(findings[:3])}) - retry")
        retry_prompt = (
            prompt + "\n\nYour previous answer included process commentary or model-owned headings. "
            "Rewrite now as clean chapter prose only. Do not mention instructions, options, "
            "source mismatch, inability, the title selection, or the prompt. Do not emit Markdown headings."
        )
        rc2, out2, err2 = _run_claude_p_with_retry(
            retry_prompt,
            timeout=_RETRY_TIMEOUT,
            book_dir=book_dir,
            phase="0book-compose",
            step=f"translation-{label}-integrity-retry",
            log=log,
        )
        if rc2 == 0:
            candidate = (out2 or "").strip()
            if not translation_output_findings(
                candidate, expected_title=title, frame=frame, narrator_subject=narrator, source=body
            ):
                out = candidate
            else:
                out = candidate or out
        else:
            log(f"      {label}: integrity retry failed rc={rc2}: {err2[:160]}")
        findings = translation_output_findings(
            out, expected_title=title, frame=frame, narrator_subject=narrator, source=body
        )
    if findings:
        raise AuthoringError(
            phase="0book-compose",
            message=f"{label}: translation edition output failed integrity gate: " + "; ".join(findings),
            manual_fallback=(
                "Re-run 0book-design/0book-compose after inspecting the source range; "
                "the pipeline refused to persist model commentary or generated headings."
            ),
        )
    # Arabic-coverage safety net (see _arabic_coverage): when the output drops too
    # much of the ground truth's quoted Arabic, retry ONCE with the specific spans
    # named. Non-fatal and keep-best — a residual shortfall never blocks the book,
    # and an empty suffix (no Arabic source, or coverage already adequate) skips it.
    arabic_retry = arabic_coverage_shortfall(out, arabic_src)
    if arabic_retry:
        log(f"      {label}: Arabic coverage low - retrying with the dropped spans named")
        rc3, out3, _err3 = _run_claude_p_with_retry(
            prompt + arabic_retry,
            timeout=_RETRY_TIMEOUT,
            book_dir=book_dir,
            phase="0book-compose",
            step=f"translation-{label}-arabic-retry",
            log=log,
        )
        cand = (out3 or "").strip()
        if (
            rc3 == 0
            and cand
            and not translation_output_findings(
                cand, expected_title=title, frame=frame, narrator_subject=narrator, source=body
            )
            and len(arabic_run_spans(cand)) > len(arabic_run_spans(out))
            and _translation_long_enough(cand, source_words)
        ):
            out = cand
        else:
            log(f"      {label}: Arabic-coverage retry did not improve - keeping best attempt")
    if not _translation_long_enough(out, source_words):
        raise AuthoringError(
            phase="0book-compose",
            message=(
                f"{label}: translation edition output is too compressed ({len(out.split())}/{source_words} words)"
            ),
            manual_fallback="Re-run after reducing chapter/window size or inspect the source range.",
        )
    return normalize_translation_prose(out, title=title)


def author_translation_edition_compose(
    book_dir: Path, *, log=print, force: bool = False, enforce_contract: bool = True
) -> Path:
    """Compose ``book/book.md`` for the translation-edition lane.

    Uses the existing ``book/book-toc.json`` from 0book-design, but writes a
    faithful translation edition instead of the normal author-first-person
    companion book. It also mirrors each generated chapter into ``chapters/`` so
    existing slide-deck authoring can operate without a separate adapter.

    ``enforce_contract`` gates the ``deliverable_mode == translation_edition`` +
    monochrome-visual contract. The legacy lane keeps it True. Book Pipeline v2
    drives route selection through the two knobs (``book_augmentation`` /
    ``book_voice``), NOT through ``deliverable_mode``, so it reuses this function
    as the shared *faithful base* with ``enforce_contract=False``.
    """
    book_dir = Path(book_dir).resolve()
    if enforce_contract:
        assert_translation_contract(book_dir)

    # Who narrates is read once per run and applies to every chapter and window.
    # It is a property of the SOURCE, so it governs this route exactly as it
    # governs the re-voice route — see _rules.NARRATIVE_FRAMES.
    _frame = narrative_frame(book_dir)
    _narrator = narrator_subject(book_dir)
    log(f"    0book-compose: narrative frame = {_frame}")

    toc_path = book_dir / "book" / "book-toc.json"
    refined_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not toc_path.exists():
        raise AuthoringError(
            phase="0book-compose",
            message=f"missing {toc_path} - run 0book-design first.",
            manual_fallback="Run the translation edition driver from the beginning.",
        )
    if not refined_path.exists():
        raise AuthoringError(
            phase="0book-compose",
            message=f"missing {refined_path} - run 0b first.",
            manual_fallback="Run Phase 0a/0b before translation edition compose.",
        )

    toc = json.loads(toc_path.read_text(encoding="utf-8"))
    lines = refined_path.read_text(encoding="utf-8").split("\n")
    chunks_dir = book_dir / "book" / "_chunks" / "translation"
    # Scoped under book/, alongside _chunks — NEVER the top-level chapters/ dir,
    # which is the podcast lane's own namespace (one ch<NN><letter>-<slug>.txt per
    # episode). The ship gate globs that folder expecting every match to pair with
    # an episode; a book-lane sidecar sharing the glob shape blocks publish. Found
    # live 2026-07-19 — see _workspace/plan/pending-work.yaml for the incident.
    chapters_dir = book_dir / "book" / "_chapters"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    arabic_pages = _load_arabic_pages(book_dir)
    line_pages = _line_pages(lines) if arabic_pages else []
    crosswalk = build_source_crosswalk(book_dir, toc, lines, line_pages or _line_pages(lines))
    drift = [
        f"chapter {entry['index']} ({entry['title']}): {'; '.join(entry['drift_findings'])}"
        for entry in crosswalk
        if entry.get("drift_findings")
    ]
    if drift:
        raise AuthoringError(
            phase="0book-compose",
            message="source crosswalk failed title/source alignment: " + "; ".join(drift[:4]),
            manual_fallback=(
                "Fix book/book-toc.json source_line_ranges or chapter titles, then rerun "
                "translation edition compose. OCR/refinement/audio do not need to rerun."
            ),
        )
    (book_dir / "book" / "source-crosswalk.json").write_text(
        json.dumps(
            {
                "schema": "podcast.translation-edition.source-crosswalk/v1",
                "book": book_dir.name,
                "chapters": crosswalk,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    parts: list[str] = [f"# {toc.get('book_title', book_dir.name)}\n"]
    previous_tail = ""
    manifest: list[dict[str, Any]] = []
    prior_manifest: dict[int, dict[str, Any]] = {}
    prior_manifest_path = book_dir / "_system" / "translation-edition-manifest.json"
    if prior_manifest_path.exists():
        try:
            prior_data = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
            prior_manifest = {
                int(item.get("index")): item
                for item in (prior_data.get("chapters") or [])
                if item.get("index") is not None
            }
        except Exception:
            prior_manifest = {}

    def _arabic_for(ranges: list[list[int]]) -> tuple[str, str]:
        if not arabic_pages or not ranges:
            return "", ""
        nums = [n for n in _pages_for_ranges(line_pages, ranges) if n in arabic_pages]
        if not nums:
            return "", ""
        return "\n\n".join(arabic_pages[n] for n in nums), f"pp.{nums[0]}-{nums[-1]}"

    if arabic_pages:
        log(f"    translation-edition-compose: Arabic ground truth loaded ({len(arabic_pages)} OCR pages)")

    def _cache_fresh(path: Path) -> bool:
        try:
            return path.stat().st_mtime >= refined_path.stat().st_mtime
        except OSError:
            return False

    # Preface / front-matter. book-toc.json may declare a preface with its own
    # source range (e.g. the work's opening teaching). The chapter loop below
    # only iterates ``chapters``, so without this the planned preface is silently
    # dropped at assembly and its teaching is lost from the deliverable.
    prev_emitted_prose = ""
    preface = toc.get("preface") or {}
    pf_ranges = preface.get("source_line_ranges") or []
    if preface.get("include") and pf_ranges:
        pf_title = str(preface.get("title") or "Preface")
        pf_source = _slice_source(lines, pf_ranges)
        if pf_source.strip():
            pf_path = chunks_dir / "preface.md"
            pf_prose = ""
            if not force and _cache_fresh(pf_path) and pf_path.exists() and pf_path.read_text(encoding="utf-8").strip():
                cached_pf = normalize_translation_prose(pf_path.read_text(encoding="utf-8").strip(), title=pf_title)
                if not translation_output_findings(cached_pf, expected_title=pf_title):
                    pf_prose = cached_pf
            if not pf_prose:
                pf_qa, _ = _quran_anchor_block(pf_source)
                pf_arabic, pf_span = _arabic_for(pf_ranges)
                log(
                    f"      preface: {pf_title} ({len(pf_source.split())} source words"
                    + (f", Arabic {pf_span}" if pf_span else "")
                    + ") -> translation edition"
                )
                pf_prose = _compose_one(
                    pf_title,
                    pf_source,
                    "",
                    book_dir,
                    "preface",
                    log,
                    arabic_src=pf_arabic,
                    quran_anchor=pf_qa,
                    frame=_frame,
                    narrator=_narrator,
                )
                pf_path.write_text(pf_prose.rstrip() + "\n", encoding="utf-8")
            parts.append(f"## {pf_title}\n\n{pf_prose}\n")
            previous_tail = " ".join(pf_prose.split()[-80:])
            prev_emitted_prose = pf_prose

    for ch in toc.get("chapters", []):
        idx = int(ch.get("bk_index") or len(manifest) + 1)
        title = str(ch.get("title") or f"Chapter {idx}")
        label = f"bk-{idx:02d}"
        ch_ranges = ch.get("source_line_ranges", [])
        source = _slice_source(lines, ch_ranges)
        out_path = chunks_dir / f"{label}.md"
        prior = prior_manifest.get(idx) or {}
        cache_matches_source = prior.get("title") == title and prior.get("source_line_ranges") == ch_ranges
        if (
            not force
            and cache_matches_source
            and _cache_fresh(out_path)
            and out_path.read_text(encoding="utf-8").strip()
        ):
            cached = out_path.read_text(encoding="utf-8").strip()
            cached = normalize_translation_prose(cached, title=title)
            cached_findings = translation_output_findings(cached, expected_title=title)
            if cached_findings:
                log(
                    f"      {label}: cached translation failed integrity gate "
                    f"({'; '.join(cached_findings[:3])}) - recompute"
                )
                prose = ""
            elif _translation_long_enough(cached, len(source.split())):
                prose = cached
            else:
                log(
                    f"      {label}: cached translation is too compressed "
                    f"({len(cached.split())}/{len(source.split())} words) - recompute"
                )
                prose = ""
        else:
            prose = ""
        if not prose:
            windows = _iter_source_windows(lines, ch_ranges) if len(source.split()) > _LONG_CHAPTER_WORDS else []
            if not windows:
                windows = [(source, ch_ranges)]
            log(
                f"      {label}: {title} ({len(source.split())} source words"
                + (f", {len(windows)} windows" if len(windows) > 1 else "")
                + ") -> translation edition"
            )
            prose_parts: list[str] = []

            def compose_part(
                part_idx: int, part_source: str, part_ranges: list[list[int]], part_tail: str
            ) -> tuple[int, str]:
                part_label = label if len(windows) == 1 else f"{label}-part-{part_idx:02d}"
                part_path = chunks_dir / f"{part_label}.md"
                if (
                    not force
                    and cache_matches_source
                    and _cache_fresh(part_path)
                    and part_path.read_text(encoding="utf-8").strip()
                ):
                    cached_part = part_path.read_text(encoding="utf-8").strip()
                    cached_part = normalize_translation_prose(cached_part, title=title)
                    cached_findings = translation_output_findings(cached_part, expected_title=title)
                    if cached_findings:
                        log(
                            f"        {part_label}: cached translation failed integrity gate "
                            f"({'; '.join(cached_findings[:3])}) - recompute"
                        )
                    elif _translation_long_enough(cached_part, len(part_source.split())):
                        return part_idx, cached_part
                    else:
                        log(
                            f"        {part_label}: cached translation is too compressed "
                            f"({len(cached_part.split())}/{len(part_source.split())} words) - recompute"
                        )
                qa_block, qa_stats = _quran_anchor_block(part_source)
                arabic_src, arabic_span = _arabic_for(part_ranges)
                if qa_stats["cited"]:
                    log(
                        f"        {part_label}: Quran anchoring - {qa_stats['anchored']}/"
                        f"{qa_stats['cited']} cited verses anchored"
                    )
                log(
                    f"        {part_label}: {len(part_source.split())} source words"
                    + (f", Arabic {arabic_span}" if arabic_span else "")
                )
                part_prose = _compose_one(
                    title,
                    part_source,
                    part_tail,
                    book_dir,
                    part_label,
                    log,
                    arabic_src=arabic_src,
                    quran_anchor=qa_block,
                    frame=_frame,
                    narrator=_narrator,
                )
                part_path.write_text(part_prose.rstrip() + "\n", encoding="utf-8")
                return part_idx, part_prose

            # Windows are composed SEQUENTIALLY (not in parallel): each window is
            # given the real tail of the window before it, so the compose prompt's
            # "do not repeat this" continuity note actually holds at the seam. This
            # is what stops the chunk-seam double-render (composing the boundary
            # passage into both adjacent windows). A deterministic seam trim then
            # removes any residual echo before the parts are joined.
            window_tail = previous_tail
            for part_idx, (part_source, part_ranges) in enumerate(windows, start=1):
                _, part_prose = compose_part(part_idx, part_source, part_ranges, window_tail)
                if prose_parts:
                    part_prose = _trim_seam_overlap(prose_parts[-1], part_prose)
                prose_parts.append(part_prose)
                window_tail = " ".join(part_prose.split()[-80:])
            prose = "\n\n".join(prose_parts).strip()
            prose = normalize_translation_prose(prose, title=title)
            out_path.write_text(prose.rstrip() + "\n", encoding="utf-8")

        # Cross-chapter seam trim: drop a chapter-opening paragraph that verbatim-
        # echoes the previous chapter's (or the preface's) tail — the boundary
        # over-run where one chapter runs into the next chapter's first passage.
        prose = _trim_seam_overlap(prev_emitted_prose, prose)

        chapter_slug = f"ch{idx:02d}-{_slugify(title, label)}"
        chapter_path = chapters_dir / f"{chapter_slug}.txt"
        chapter_path.write_text(f"# {title}\n\n{prose.rstrip()}\n", encoding="utf-8")
        parts.append(f"## {idx}. {title}\n\n{prose}\n")
        previous_tail = " ".join(prose.split()[-80:])
        prev_emitted_prose = prose
        manifest.append(
            {
                "index": idx,
                "title": title,
                "chapter_file": str(chapter_path.relative_to(book_dir)),
                "source_line_ranges": ch.get("source_line_ranges", []),
                "source_words": len(source.split()),
                "output_words": len(prose.split()),
            }
        )

    book_md = book_dir / "book" / "book.md"
    assembled = dedupe_seam_paragraphs(simplify_transliteration("\n".join(parts).rstrip() + "\n"))
    book_md.write_text(assembled, encoding="utf-8")
    (book_dir / "_system" / "translation-edition-manifest.json").write_text(
        json.dumps(
            {
                "schema": "podcast.translation-edition/v1",
                "mode": TRANSLATION_EDITION_MODE,
                "augmentation": "forbidden",
                "visual_style": DEFAULT_VISUAL_STYLE,
                "chapters": manifest,
                "source_crosswalk": "book/source-crosswalk.json",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    log(f"    translation-edition-compose: assembled book.md with {len(manifest)} chapters")
    return book_md
