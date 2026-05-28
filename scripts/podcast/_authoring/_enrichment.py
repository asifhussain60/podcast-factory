"""_authoring/enrichment.py — Phase 0e: per-chapter enrichment.

Extracted from _authoring.py (A4 split).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ._core import (  # noqa: E402
    AuthoringError,
    DEFAULT_TIMEOUT,
    PHASE_0E_CHAPTER_TIMEOUT,
    _run_claude_p_with_retry,
    _compute_sc_timeout,
)
from ._refine import _run  # noqa: E402

# ─── Phase 0e — Chapter enrichment ──────────────────────────────────────────
def author_phase_0e(book_dir: Path,
                    timeout: int = DEFAULT_TIMEOUT,
                    chapter_timeout: int = PHASE_0E_CHAPTER_TIMEOUT,
                    log=print) -> str:
    """Enrich each chapter with citations from the seven-tier whitelist.

    Implemented as a per-chapter loop so the LLM only enriches one chapter
    file per `claude -p` call. Idempotent: an enrichment-log.md row of the
    form `- <chapter-stem>: ENRICHED ...` marks a chapter as done; reruns
    skip those chapters. The first time this runs the log is created and
    receives one row per chapter as each completes.

    Reads:  every BOOK_DIR/chapters/ch*.txt
            content/_shared/islam/*.yml (doctrinal lineage + naming + canonical attributions)
            (the prior enrichment-sources.md handbook tree was retired 2026-05-23;
            the 7-tier source hierarchy is now inlined in this function's LLM prompt)
    Writes: enriched BOOK_DIR/chapters/ch*.txt (in place)
            BOOK_DIR/_system/enrichment-log.md (per-chapter status)
    """
    import datetime as _dt

    book_slug = book_dir.name
    chapters_dir = book_dir / "chapters"
    enrichment_log = book_dir / "_system" / "enrichment-log.md"

    chapter_files = sorted(chapters_dir.glob("ch*.txt"))
    if not chapter_files:
        raise AuthoringError(
            phase="0e",
            message=f"no chapters to enrich under {chapters_dir} (Phase 0d should have produced them)",
            manual_fallback="Run Phase 0d first.",
        )

    enrichment_log.parent.mkdir(parents=True, exist_ok=True)
    if not enrichment_log.exists():
        enrichment_log.write_text(
            f"# Enrichment log — {book_slug}\n\n"
            f"Per-chapter status. Rows with `ENRICHED` are checkpointed and skipped on resume.\n\n",
            encoding="utf-8",
        )

    existing_log = enrichment_log.read_text(encoding="utf-8")
    already_done: set[str] = set()
    for line in existing_log.splitlines():
        s = line.strip()
        if s.startswith("- ") and ": ENRICHED" in s:
            # `- ch03-foo: ENRICHED at 2025-...`
            stem = s[2:].split(":", 1)[0].strip()
            already_done.add(stem)

    log(f"  phase 0e · per-chapter loop ({len(chapter_files)} chapters, "
        f"{len(already_done)} already enriched)")

    failures: list[tuple[str, str]] = []
    for chapter_file in chapter_files:
        stem = chapter_file.stem  # e.g. ch03-foo or ch03a-foo
        if stem in already_done:
            log(f"    {stem} · skip (already enriched)")
            continue

        prompt = (
            f"You are driving Phase 0e (Chapter Enrichment from Outside Sources) of the "
            f"/podcast skill on book-slug `{book_slug}`, **chapter `{stem}` only**. Read "
            f"the canonical procedure from `skills-staging/podcast/SKILL.md` "
            f"(search `### PHASE 0e`) and apply it to THIS ONE chapter.\n\n"
            f"INPUT (the chapter file to enrich in place): `{chapter_file}`\n"
            f"AUTHORITY (the prior `content/podcast/.skill/handbook/` tree was retired in the\n"
            f"2026-05-23 restructure; the R-rules, tier-diversity rule, and Arabic manifest\n"
            f"that lived there are inlined below — proceed without trying to Read those paths):\n"
            f"  - DOCTRINAL accuracy: `content/_shared/islam/imam-lineage-ismaili.yml`,\n"
            f"    `naming-conventions.yml`, `canonical-attributions.yml` ARE source-of-truth\n"
            f"    and DO exist on disk. The literal phrase pairing the leadership-title\n"
            f"    with the personal name of the Father of Imams is FORBIDDEN — always\n"
            f"    use 'Father of Imams'. Hassan is the 1st Imam in the canonical lineage.\n"
            f"    Do NOT write the forbidden phrase anywhere — not even inside DO-NOT-SAY\n"
            f"    guards. The doctrinal scanner is substring-only and flags the guard.\n"
            f"  - ENRICHMENT-SOURCE TIERS: seven tiers ranging from Quran/Nahj/Prophetic\n"
            f"    hadith (Tier 1) down to modern Ismaili scholarship (Tier 7). Each chapter\n"
            f"    should pull from at least 3 different tiers; quotations/citations together\n"
            f"    should not exceed 60% of total wordcount; no consecutive blockquote stacks.\n"
            f"  - R-RULES: see the rule lists inlined below in this prompt; the canonical\n"
            f"    Python data lives in `scripts/podcast/_rules.py`.\n\n"
            f"OUTPUTS (write ONLY these — do NOT touch any other file):\n"
            f"  - `{chapter_file}` (enriched in place)\n\n"
            f"Constraints:\n"
            f"- Outside material ≤ 60% of THIS chapter's word count. The original author's "
            f"argument stays the spine.\n"
            f"- Tier diversity required — don't pull all enrichments from one tier.\n"
            f"- Every citation carries author, work, page or section, and translator "
            f"(for Quranic translations).\n"
            f"- Apply R-PHONETICS-OUT: no inline `*term* (PHO-NE-TIC)` parens in chapter "
            f"prose; phonetic discipline lives in the customize prompt only.\n"
            f"- Apply R-HONORIFIC-ONCE STRICTLY (F5 framework guard 2026-05-21): each "
            f"honorific FORM appears AT MOST ONCE per chapter. This includes the glyph "
            f"`ﷺ` AND the text expansions `(peace be upon him)`, `(peace be upon them)`, "
            f"`(peace and blessings be upon him)`, `(may Allah be pleased with him)`, "
            f"`(may God be pleased with him)`. On first mention of a figure, include "
            f"their honorific; on subsequent mentions, use the bare name only "
            f"('the Prophet', 'the Father of Imams', 'Moses' — NEVER the title-and-name "
            f"pairing for the Father of Imams). Before returning the chapter file, "
            f"COUNT each honorific form's occurrences — if any form appears more than "
            f"once, trim duplicates. NotebookLM vocalizes every honorific aloud; "
            f"repetition is jarring in audio.\n"
            f"- Apply R-NO-MANUSCRIPT-META (F3 framework guard 2026-05-21): the chapter "
            f"file is the SPOKEN CONTENT NotebookLM will read aloud. Do NOT include "
            f"editorial framings about the source manuscript's physical state — no "
            f"paragraphs about damaged folios, reconstructed fragments, OCR breakdowns, "
            f"translator's notes, editor's notes, manuscript provenance, or what the "
            f"text 'breaks off' at. Examples of language to AVOID emitting: 'The opening "
            f"folios are heavily damaged', 'What can be reconstructed reads', 'The text "
            f"breaks off', 'collapses in the OCR', 'A second damaged folio carries "
            f"fragments'. Only include prose the hosts should discuss as substantive "
            f"philosophical or theological content from the author's own work.\n"
            f"- Apply R-NO-ARABIC-NAMES (F20 doctrine 2026-05-22; empirically locked "
            f"across 3 audio audits). The chapter PROSE itself must contain ZERO "
            f"Arabic personal names, book titles, surah names, or concept words. "
            f"NotebookLM TTS mangles every Arabic transliteration ('al-Kirmani' → 12+ "
            f"variants in 42 min; 'al-hayuli' → sounds like 'Allah'; 'Sahih "
            f"al-Sajjadiyya' → conflated with 'Sahih al-Bukhari'). Replace with English "
            f"audio labels at the chapter level:\n"
            f"    - Person names: use stable role-labels — 'the author' for the "
            f"book's author; 'Jonathan' / 'Samuel' / 'Marcus' / etc. for figures with "
            f"no established English title; 'the Commander of the Faithful', 'the "
            f"Prophet', 'the fourth Imam' for established figures.\n"
            f"    - Book titles: wrap with 'the book' + English meaning — 'the book "
            f"*The Correction*' (al-Islah); 'the book *The Defense*' (al-Nusra); 'the "
            f"book *The Brilliant Aphorisms*' (Ghurar al-Hikam); 'the canonical hadith "
            f"collection' (Sahih al-Bukhari).\n"
            f"    - Concept words: tawhid → monotheism; hudud → the limits; da'wa → "
            f"the call; natiq → the speaker-prophet; ma'lul → the effect; al-hayuli → "
            f"prime matter; ta'wil → the inner interpretation.\n"
            f"    - Allowed Arabic-origin terms (TTS-stable, verified): the Quran, "
            f"Imam, Medina, Ismaili, Fatimid. NO OTHERS.\n"
            f"- Apply R-SURAH-ENGLISH-ONLY (F29 doctrine 2026-05-22). Quranic verse "
            f"citations in chapter prose MUST reference the surah by its English "
            f"meaning, NOT its Arabic name. Examples: al-Ahzab → 'the chapter on the "
            f"confederates'; al-Shams → 'the chapter on the sun'; al-Isra → 'the "
            f"chapter on the night journey'; Qaf → 'the chapter Qaf' (rare TTS-stable) "
            f"OR drop and lead with content. When in doubt, omit surah name entirely "
            f"and quote the verse content with the chapter and verse number ('verse "
            f"sixteen of the chapter Qaf') or just the content.\n"
            f"- Apply R-ALQAAB-FUNCTIONAL-PARAPHRASE (F24 doctrine 2026-05-22). Use "
            f"only established English alqaab (Commander of the Faithful, Lion of "
            f"God). For novel/obscure alqaab, use functional paraphrase — 'one of his "
            f"martial honorifics', 'a traditional title associated with his rank'. "
            f"NEVER literally translate alqaab in chapter prose.\n"
            f"- Do NOT modify any other chapter file, contract, or `enrichment-log.md` — "
            f"the orchestrator appends the log row after validating your output.\n\n"
            f"Exit when `{chapter_file}` has been rewritten in place with citations woven in."
        )

        # Word-count-aware timeout per chapter (2026-05-24 strategy, extended
        # from Phase 0d to Phase 0e). Enrichment is heavier-write than 0d's
        # parse-and-contract, so the same _compute_sc_timeout formula —
        # max(900, min(3600, ceil(words*0.4 + 600))) — gives ch01 (9,645 words)
        # 64 min vs. the prior flat 15 min. ch02 (11,143 words) would have hit
        # the 60-min ceiling; the flat 900s explains why it timed out.
        chapter_words = len(chapter_file.read_text(encoding="utf-8").split())
        per_chapter_timeout = _compute_sc_timeout(chapter_words)
        log(f"    {stem} · enriching ({chapter_words} words, timeout={per_chapter_timeout}s)")
        # Capture pre-enrichment mtime to detect that the file was actually rewritten.
        pre_mtime = chapter_file.stat().st_mtime
        try:
            rc, stdout, stderr = _run_claude_p_with_retry(
                prompt, timeout=per_chapter_timeout,
                book_dir=book_dir, phase="0e", step=stem,
                log=log,
            )
        except AuthoringError as e:
            if "BOTH attempts timed out" in str(e):
                # Halt-and-surface: don't continue the loop. User decides:
                # /podcast manual drive, raise PHASE_0D_SC_TIMEOUT_MAX, or skip.
                raise
            raise
        if rc != 0:
            # Transient — log + continue; resume retries.
            # P5.2: capture stdout AND stderr in the failure record.
            failures.append(
                (
                    stem,
                    f"rc={rc}: stderr={(stderr or '').strip()[:300]} | "
                    f"stdout={(stdout or '').strip()[:300]}",
                )
            )
            log(f"    {stem} · FAILED rc={rc}")
            continue
        if not chapter_file.exists() or chapter_file.stat().st_size == 0:
            # P5.2: rc=0 with missing/empty chapter file is the P5.1 failure
            # class — claude -p exited cleanly without writing. Fatal.
            raise AuthoringError(
                phase="08-enrichment",
                message=(
                    f"{stem} returned rc=0 but produced no enriched chapter "
                    f"file at {chapter_file}. P5.1 failure class — claude -p "
                    f"exited cleanly without writing. After --permission-mode "
                    f"acceptEdits this should not recur."
                ),
                manual_fallback=(
                    f"Inspect stdout/stderr on this error. If a content-filter "
                    f"refusal or quota issue, address the cause and resume. "
                    f"DO NOT silently advance."
                ),
                stdout=stdout or "",
                stderr=stderr or "",
            )
        post_mtime = chapter_file.stat().st_mtime
        touched = " (in-place rewrite)" if post_mtime > pre_mtime else " (no mtime change — verify manually)"

        # Append checkpoint row.
        ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with enrichment_log.open("a", encoding="utf-8") as f:
            f.write(f"- {stem}: ENRICHED at {ts}{touched}\n")
        log(f"    {stem} · OK")

    if failures:
        raise AuthoringError(
            phase="0e",
            message=(
                f"{len(failures)} of {len(chapter_files)} chapters failed enrichment: "
                + "; ".join(f"{s}: {m}" for s, m in failures[:3])
            ),
            manual_fallback=(
                "Inspect the chapter files of failed chapters; enrich each manually via "
                "/podcast, then add a `- <stem>: ENRICHED ...` row to enrichment-log.md "
                "and re-invoke orchestrate-book --resume."
            ),
        )

    # Baked-in safety net (2026-05-24): Phase 0e occasionally lets inline
    # phonetic guides slip into chapter files (e.g. `*Maqrub* (mak-ROOB)`)
    # despite the R-PHONETICS-OUT instruction in its prompt. The build script
    # HARD-refuses these later, blocking per-chapter authoring on every run.
    # Strip them deterministically here so the build is never blocked by the
    # leak. The phonetic data is preserved in _phonetics.md and glossary.yml;
    # the framing's Pronunciation section is the canonical surface.
    strip_msg = _bake_strip_inline_phonetics(book_dir, log=log)

    return (
        f"0e per-chapter loop: {len(chapter_files)} chapters enriched "
        f"({len(already_done)} skipped as already done, "
        f"{len(chapter_files) - len(already_done)} newly enriched){strip_msg}"
    )


def _bake_strip_inline_phonetics(book_dir: Path, *, log=print) -> str:
    """Run scripts/podcast/strip_inline_phonetics.py over BOOK_DIR/chapters/.

    Best-effort: failures log and skip; this is a safety net, not a
    pipeline-blocking step. Most runs will report 0 strips (the LLM
    usually honors R-PHONETICS-OUT); when the LLM slips, this catches it
    BEFORE the build hard-refuses.
    """
    here = Path(__file__).resolve().parent
    stripper = here / "strip_inline_phonetics.py"
    if not stripper.exists():
        return ""
    rc, _out, err = _run([sys.executable, str(stripper), "--book-dir", str(book_dir)])
    if rc != 0:
        log(f"  phase 0e · strip_inline_phonetics skipped (rc={rc}): {err.strip()[:200]}")
        return ""
    return " + strip-inline-phonetics"


