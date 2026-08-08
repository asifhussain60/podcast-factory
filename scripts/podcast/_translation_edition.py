"""Translation-edition compose orchestration.

This module defines the contract for a faithful, visually enhanced translation
PDF path. It is deliberately separate from ``content_profile``: the profile says
what the source is about; ``deliverable_mode`` says what product we are making.

R3 DR-005 split (2026-07-18): the config/contract predicates moved verbatim to
``_translation_contract.py`` and the deterministic text post-processing (seam
trim/dedup, prose normalization, output findings, monochrome SVG, crosswalk
builder) to ``_translation_text.py``. Every moved name is re-exported here
(`X as X`, the `_azure.py` pattern) so importers and test patch-targets keep
working unchanged. The compose PROMPT moved to ``_translation_prompts.py`` on
2026-07-20 (DR-005 gate) and is re-exported here — see that module for why the
Spec-2 "prompt stays with its orchestration" precedent does not apply to it. The
per-chunk `claude -p` orchestration and its three retries moved to
``_translation_chunk.py`` on 2026-08-03, under the same gate.

What REMAINS is the ASSEMBLY, and it is now the whole of this module: which
chunks exist, which are served from cache, which are the author's own from the
Composer, where the source's own opening goes, and how the parts become book.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _authoring._core import AuthoringError
from _book_compose import (
    _line_pages,
    _load_arabic_pages,
    _pages_for_ranges,
    _quran_anchor_block,
    _slice_source,
)
from _book_edits import anchor_key, edited_body, edited_chapter_keys
from _pipeline_flags import narrative_frame, narrator_subject
from _translation_cache import make_is_fresh
from _translation_chunk import _compose_one as _compose_one

# R3 DR-005 re-exports — moved names, kept importable from this module. One line
# each: the parenthesised three-line form cost 60 lines of the module's 600-line
# budget and said nothing the single line does not.
from _translation_contract import DEFAULT_VISUAL_STYLE as DEFAULT_VISUAL_STYLE
from _translation_contract import TRANSLATION_EDITION_MODE as TRANSLATION_EDITION_MODE
from _translation_contract import assert_translation_contract as assert_translation_contract
from _translation_contract import contract_findings as contract_findings
from _translation_contract import deliverable_mode as deliverable_mode
from _translation_contract import is_faithful_translation_deliverable as is_faithful_translation_deliverable
from _translation_contract import is_translation_edition as is_translation_edition
from _translation_contract import read_series_config as read_series_config
from _translation_contract import requires_monochrome_visuals as requires_monochrome_visuals
from _translation_contract import translation_policy as translation_policy
from _translation_prompts import _compose_prompt as _compose_prompt
from _translation_text import _adjacent_echo as _adjacent_echo
from _translation_text import _boundary_echo as _boundary_echo
from _translation_text import _compress_line_ranges as _compress_line_ranges
from _translation_text import _iter_source_windows as _iter_source_windows
from _translation_text import _overlap_tokens as _overlap_tokens
from _translation_text import _para_is_echo as _para_is_echo
from _translation_text import _slugify as _slugify
from _translation_text import _source_headings as _source_headings
from _translation_text import _split_paragraphs as _split_paragraphs
from _translation_text import _topic_hits as _topic_hits
from _translation_text import _translation_long_enough as _translation_long_enough
from _translation_text import _trim_seam_overlap as _trim_seam_overlap
from _translation_text import build_source_crosswalk as build_source_crosswalk
from _translation_text import dedupe_seam_paragraphs as dedupe_seam_paragraphs
from _translation_text import duplicate_passage_findings as duplicate_passage_findings
from _translation_text import monochrome_svg as monochrome_svg
from _translation_text import normalize_translation_prose as normalize_translation_prose
from _translation_text import record_seam_removals as record_seam_removals
from _translation_text import source_title_drift_findings as source_title_drift_findings
from _translation_text import translation_output_findings as translation_output_findings
from _translit import simplify_transliteration

_LONG_CHAPTER_WORDS = 4500


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

    A chapter the human has authored in the Book Composer is NOT re-translated: its
    saved body is emitted directly and no model call is made for it. The Composer is
    the singular path for PDF-bound chapter changes, so composing over it bought
    nothing — the replay at the end of compose discarded the fresh prose anyway. On
    2026-07-21 that cost a full re-translation of nine chapters to keep one of them,
    and the book moved 111 words in 33 minutes. ``force`` re-composes regardless,
    and says so.
    """
    book_dir = Path(book_dir).resolve()
    if enforce_contract:
        assert_translation_contract(book_dir)

    _edited = edited_chapter_keys(book_dir)
    authored = set() if force else _edited
    if force and _edited:
        log(f"    0book-compose: --force will RE-COMPOSE OVER {len(_edited)} Composer-authored chapter(s)")

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

    # Freshness rule lives in _translation_cache — see that module for why it
    # covers the prompts and the config, not just the source text.
    _cache_fresh = make_is_fresh(book_dir, refined_path)

    # The source's own opening. book-toc.json may declare a preface with its own
    # source range (e.g. the work's opening teaching). The chapter loop below only
    # iterates ``chapters``, so without this the planned opening is silently
    # dropped at assembly and its teaching is lost from the deliverable.
    #
    # It is no longer emitted as a section of its own (Asif, 2026-08-03). A book
    # begins with its content chapters, so the opening is FOLDED into the body of
    # the first numbered chapter and the machine-invented `preface.title` — "The
    # Question of Leadership", "A Threshold to the Subtle Lights" — is dropped with
    # the heading it named. Nothing authored is lost: the prose itself is carried
    # over verbatim, under the chapter's own heading.
    #
    # A book whose opening is ABOUT the book rather than part of it takes the
    # no-preface path that already exists — `preface.include: false` — rather than
    # a second knob. See `al-anwaar-al-lateefah` and `asaas-al-taveel`.
    prev_emitted_prose = ""
    folded_opening = ""
    preface = toc.get("preface") or {}
    pf_ranges = preface.get("source_line_ranges") or []
    if preface.get("include") and pf_ranges:
        pf_title = str(preface.get("title") or "Preface")
        pf_source = _slice_source(lines, pf_ranges)
        if pf_source.strip():
            pf_path = chunks_dir / "preface.md"
            pf_prose = edited_body(book_dir, anchor_key(pf_title)) if anchor_key(pf_title) in authored else ""
            if pf_prose:
                log(f"      preface: {pf_title} — Composer edit, not re-translated")
            elif (
                not force and _cache_fresh(pf_path) and pf_path.exists() and pf_path.read_text(encoding="utf-8").strip()
            ):
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
            # THE GUARD. A Composer edit keyed to the front-matter heading is a
            # chapter the human authored, and the replay rewrites chapters from
            # the sidecar AFTER this assembly. Fold it into chapter 1 and the
            # replay would restore chapter 1 from the sidecar a step later and
            # delete the folded opening with it — silently, because
            # `apply_composer_edits` reports an edit whose heading is gone as
            # orphaned and never notices prose that went missing from a chapter it
            # did find. So: refuse to fold, keep the section, and say why.
            # `fold_preface_edit.py` migrates the sidecar; after that this book
            # takes `preface.include: false` and there is nothing left to fold.
            if anchor_key(pf_title) in authored:
                log(
                    f"      preface: NOT folded — a Composer edit is keyed to {pf_title!r}. "
                    "Run fold_preface_edit.py to merge it into chapter 1 first; "
                    "folding now would let the replay delete the author's opening."
                )
                parts.append(f"## {pf_title}\n\n{pf_prose}\n")
            else:
                folded_opening = pf_prose
            # Unchanged either way: this prose is still what immediately precedes
            # chapter 1, so it is still the continuity tail the first chapter's
            # compose is given and still the text its seam trim compares against.
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
        # The author's own chapter, emitted as-is. Checked BEFORE the cache and the
        # integrity gates below: those gates judge a MODEL's rendering of the
        # source, and running them over a human's prose would recompute the chapter
        # the moment they wrote something a gate did not expect.
        authored_prose = edited_body(book_dir, anchor_key(title)) if anchor_key(title) in authored else None
        if authored_prose:
            log(f"      {label}: {title} — Composer edit, not re-translated")
            prose = authored_prose
        elif (
            not force
            and cache_matches_source
            and _cache_fresh(out_path)
            and out_path.read_text(encoding="utf-8").strip()
        ):
            cached = out_path.read_text(encoding="utf-8").strip()
            cached = normalize_translation_prose(cached, title=title)
            # A CACHED chapter must clear the SAME gate as a fresh one. It used
            # to be checked without `frame=` or `source=`, which skips
            # frame_findings and narrative_person_findings entirely — BK-N1..N7,
            # the whole narrative-frame battery. Every chapter of the live book
            # was being served from a cache written before the frame was locked,
            # so the shipping prose had never faced that gate at all.
            cached_findings = translation_output_findings(
                cached, expected_title=title, frame=_frame, narrator_subject=_narrator, source=source
            )
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
                    cached_findings = translation_output_findings(
                        cached_part,
                        expected_title=title,
                        frame=_frame,
                        narrator_subject=_narrator,
                        source=part_source,
                    )
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
        # Never applied to an authored chapter: the seam is an artifact of windowed
        # MODEL composition, and this trim deletes a whole paragraph, which is not
        # something to do to a human's page on a similarity guess.
        if not authored_prose:
            prose = _trim_seam_overlap(prev_emitted_prose, prose)

        chapter_slug = f"ch{idx:02d}-{_slugify(title, label)}"
        chapter_path = chapters_dir / f"{chapter_slug}.txt"
        chapter_path.write_text(f"# {title}\n\n{prose.rstrip()}\n", encoding="utf-8")

        # The fold. The source's own opening becomes the first paragraphs of the
        # first numbered chapter, under that chapter's own heading. `manifest` is
        # appended at the bottom of this loop, so an empty one IS "this is the
        # first chapter" — no separate counter to fall out of step with it.
        #
        # Only book.md is folded, deliberately. `chapter_path` above is the
        # NotebookLM lane's upload source, which has never carried the opening;
        # putting it there would change an audio deliverable this work is not
        # about.
        body = prose
        folded_words = 0
        if folded_opening and not manifest:
            folded_words = len(folded_opening.split())
            body = folded_opening.rstrip() + "\n\n" + prose.lstrip()
            folded_opening = ""
            log(f"      {label}: source's own opening folded in ({folded_words} words)")
        parts.append(f"## {idx}. {title}\n\n{body}\n")
        previous_tail = " ".join(prose.split()[-80:])
        prev_emitted_prose = prose
        entry = {
            "index": idx,
            "title": title,
            "chapter_file": str(chapter_path.relative_to(book_dir)),
            "source_line_ranges": ch.get("source_line_ranges", []),
            "source_words": len(source.split()),
            "output_words": len(body.split()),
        }
        if folded_words:
            entry["folded_opening_words"] = folded_words
        manifest.append(entry)
        # Persist after EVERY chapter, not just at the end — see
        # _write_translation_manifest's docstring for why.
        _write_translation_manifest(book_dir, manifest)

    # A toc that declares an opening and no chapters has nothing to fold it into.
    # Emit it rather than drop it: losing the source's words to an empty chapter
    # list would be the one outcome the fold exists to prevent.
    if folded_opening:
        log("      preface: no numbered chapter to fold into — emitted as its own section")
        parts.append(f"## {str(preface.get('title') or 'Preface')}\n\n{folded_opening}\n")

    book_md = book_dir / "book" / "book.md"
    # It deletes prose on a similarity judgment, so it reports what it deleted.
    seam_removed: list[dict] = []
    assembled = dedupe_seam_paragraphs(simplify_transliteration("\n".join(parts).rstrip() + "\n"), removed=seam_removed)
    book_md.write_text(assembled, encoding="utf-8")
    record_seam_removals(book_dir, "base", seam_removed, log)
    _write_translation_manifest(book_dir, manifest)
    log(f"    translation-edition-compose: assembled book.md with {len(manifest)} chapters")
    return book_md


def _write_translation_manifest(book_dir: Path, manifest: list[dict[str, Any]]) -> None:
    """Persist the chunk-cache manifest — called after EVERY chapter, not just at
    the end of a full compose.

    Written only once, at the very end of the loop, a chapter that failed
    integrity mid-book (a real, observed case: a flaky rewrite on chapter 11 of
    15) meant the manifest never landed at all, so a retry's ``cache_matches_source``
    check found no prior entry for ANY chapter and recomposed the whole book from
    chapter 1 — redoing ten already-good chapters to get back to the one that
    failed. Writing it incrementally makes each chapter's cache valid the moment
    that chapter lands, survives a mid-book halt, and costs nothing extra: the
    shape written here is identical to the final write, just with however many
    chapters have completed so far.
    """
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
