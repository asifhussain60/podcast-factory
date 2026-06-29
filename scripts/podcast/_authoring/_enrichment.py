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
    ARABIC_SCHOLARLY_CATEGORIES,
    FICTION_CONTENT_PROFILES,
    SKIP_ENRICHMENT_CATEGORIES,
    _read_category,
    _read_content_profile,
)
from ._refine import _run  # noqa: E402
from _validator_constants import META_PROSE_TELLS  # noqa: E402


def build_technical_enrichment_prompt(
    book_slug: str,
    chapter_file: "Path",
    category: str = "",
) -> str:
    """Phase 0e enrichment prompt for technical/developer content.

    Replaces the Islamic 7-tier source hierarchy with technical accuracy
    verification: official documentation, version checks, real-world examples
    from case studies, and practical developer gotchas.

    Items 6–8 (editorial denoising, practical anchors, habit-mapping) are
    gated to category='explainers' only — they are harmful for interview/article
    categories where background and context are the content, not the noise.
    """
    _explainer_items = (
        f"  6. **Editorial denoising**: Identify any passage that explains the internal\n"
        f"     implementation of a mechanism — kernel-level details, benchmark statistics,\n"
        f"     release dates for a comparison tool, version-specific rollout timelines for\n"
        f"     a third-party product — and convert it to its *practical outcome* for the\n"
        f"     developer: what do they type, what do they see, what happens if they don't\n"
        f"     act. Theory that serves no hands-on purpose should be cut, not trimmed.\n"
        f"  7. **Practical anchors**: For every concept introduced (any H2-level section or\n"
        f"     named feature), ensure at least one 'type this → see this' sequence exists:\n"
        f"     a CLI command, a before/after code diff, or a session-step walkthrough.\n"
        f"     If the source material supports it, include one sequence per concept.\n"
        f"     If it does not, a concrete outcome sentence is the acceptable minimum.\n"
        f"  8. **Habit-mapping for migration audiences**: If the chapter addresses developers\n"
        f"     migrating from another tool, include at least one explicit 'old habit → new\n"
        f"     habit' mapping per major workflow. Format: 'In [old tool] you [did X]; in\n"
        f"     Claude Code you [describe Y].'\n"
    ) if category == "explainers" else ""

    return (
        f"You are driving Phase 0e (Technical Accuracy Enrichment) of the /podcast skill "
        f"on book-slug `{book_slug}`, **chapter `{chapter_file.stem}` only**.\n\n"
        f"INPUT (the chapter file to enrich in place): `{chapter_file}`\n\n"
        f"TASK — enrichment for technical developer content:\n"
        f"  1. **Accuracy verification**: For every factual claim in the chapter (feature "
        f"     capabilities, command syntax, pricing figures, performance benchmarks), "
        f"     verify it is consistent with what the source document states. Flag and "
        f"     correct any internal inconsistencies.\n"
        f"  2. **Concrete examples**: Where the chapter makes an abstract claim, add a "
        f"     short concrete before/after example if one can be derived from the source "
        f"     material. Do NOT invent examples not grounded in the source.\n"
        f"  3. **Practical gotchas**: If the chapter covers a workflow or tool, add a "
        f"     brief 'common mistake' or 'first-week pitfall' note where the source "
        f"     material gives evidence for one (e.g. API key override bug, context window "
        f"     management, rate limit behaviour).\n"
        f"  4. **Version specificity**: Where a feature is version-gated, ensure the "
        f"     version number is stated explicitly (e.g. 'available since v2.1.59+').\n"
        f"  5. **Developer voice**: Enrich in active developer voice. Prefer 'Run X to do Y' "
        f"     over 'X can be used to do Y'.\n"
        + _explainer_items +
        f"CONSTRAINTS:\n"
        f"- Outside material ≤ 40% of THIS chapter's word count. The source content is "
        f"  the spine — enrichment adds depth, not bulk.\n"
        f"- Every added claim must be derivable from the source document. No hallucinated "
        f"  features, no speculative future capabilities.\n"
        f"- No Islamic content, no Arabic terms, no scholarly citations. This is developer "
        f"  documentation.\n"
        f"- Preserve all CLI commands, code blocks, and version numbers verbatim.\n"
        f"- Do not apply honorific, personal-name substitution, or scriptural citation rules — "
        f"  those belong to religious scholarly content, not technical documentation.\n\n"
        f"OUTPUTS: `{chapter_file}` (enriched in place). No other files.\n\n"
        f"Exit when `{chapter_file}` has been enriched."
    )

# ─── Phase 0e — Chapter enrichment ──────────────────────────────────────────
# Modern-science apologetics block (gated by series.enable_modern_science_responses;
# default OFF so existing books are unchanged). Woven where relevant, corpus-grounded,
# decisive teacher voice. Lives in 0e so it appears in BOTH the podcast and the PDF
# (which share the enriched chapter as their single source).
_MODERN_SCIENCE_BLOCK = (
    "\n- Apply R-MODERN-SCIENCE-RESPONSE (Asif 2026-06-14): WHERE — and only where — "
    "this chapter's teaching touches a topic that modern science is commonly held to "
    "challenge (origins/creation, cosmology, the nature of the soul, miracles, the "
    "unseen, evolution, the age of the cosmos), add a SHORT, DECISIVE response in the "
    "teacher's own voice that resolves the apparent conflict with confidence and "
    "without defensiveness. Constraints: (a) ground it in the tradition's own framing "
    "(the inner/ta'wil reading, the limits of empirical method, the created-ness of "
    "time) — prefer reasoning the corpus already supplies; (b) keep it to a few "
    "sentences woven into the flow, NOT a separate lecture or a debate the source never "
    "had; (c) state the answer as settled teaching, never 'some might argue' hedging; "
    "(d) do NOT manufacture a science objection in chapters whose teaching does not "
    "raise one. This counts toward the ≤60% outside-material budget.\n"
)


def _modern_science_enabled(book_dir: Path) -> bool:
    """Read series.enable_modern_science_responses from series-config.yaml (default False)."""
    cfg = book_dir / "_system" / "series-config.yaml"
    if not cfg.exists():
        return False
    try:
        import yaml
        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    except Exception:
        return False
    # accept either top-level or under series:
    if bool(data.get("enable_modern_science_responses")):
        return True
    return bool((data.get("series") or {}).get("enable_modern_science_responses"))


def author_phase_0e(book_dir: Path,
                    timeout: int = DEFAULT_TIMEOUT,
                    chapter_timeout: int = PHASE_0E_CHAPTER_TIMEOUT,
                    log=print,
                    category: str | None = None,
                    content_profile: str | None = None) -> str:
    """Enrich each chapter with citations — routes to the correct strategy per category.

    Islamic/scholarly categories: 7-tier Islamic hierarchy (Quran → Hadith → … → modern scholarship).
    sites: SKIPPED — product documentation is authoritative; outside enrichment would be inaccurate.
    explainers: technical accuracy enrichment (official docs verification, gotchas, version specificity).
    fiction (content_profile): companion sidecar augmenter — NEVER modifies chapter prose,
      writes companion glossary/asides only. Detected via content_profile field, not category,
      because intake defaults category to "books" even for fiction books.

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
    if category is None:
        category = _read_category(book_dir)
    if content_profile is None:
        content_profile = _read_content_profile(book_dir)

    # Fiction profile: sidecar-only augmenter (companion glossary, never edits prose).
    # content_profile takes precedence over category because intake defaults category
    # to "books" even for fiction books; content_profile is the authoritative signal.
    if content_profile in FICTION_CONTENT_PROFILES:
        log(f"  phase 0e · content_profile={content_profile!r} → fiction sidecar augmenter")
        from augment_fiction_sidecar import author_fiction_sidecar
        return author_fiction_sidecar(
            book_dir, timeout=chapter_timeout, log=log,
        )

    # Sites category: authoritative product docs — outside enrichment would be inaccurate.
    if category in SKIP_ENRICHMENT_CATEGORIES:
        log(f"  phase 0e · SKIPPED (category={category!r} — source is already authoritative)")
        return f"0e skipped: category={category!r} does not require enrichment"

    # Wave-Fiction: narrative fiction carries no citations, Arabic terms, or doctrinal
    # tiers to enrich. Honor the registry's skip_enrichment intent for fiction WITHOUT
    # touching technical/Islamic routing below (the flag is otherwise dead for those).
    from _content_profile import resolve_content_profile  # local import: avoid circularity
    if resolve_content_profile(book_dir) == "fiction":
        log("  phase 0e · SKIPPED (content_profile='fiction' — narrative needs no citation enrichment)")
        return "0e skipped: content_profile='fiction' does not require enrichment"

    _use_technical_enrichment = category not in ARABIC_SCHOLARLY_CATEGORIES
    log(f"  phase 0e · category={category!r}, strategy={'technical' if _use_technical_enrichment else 'islamic-7-tier'}")

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

        if _use_technical_enrichment:
            prompt = build_technical_enrichment_prompt(book_slug, chapter_file, category=category or "")
        else:
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
            f"- Keep chapter prose listener-clean: Quranic and hadith quotations may carry "
            f"the concise source locator needed for trust, but wisdom/saying blockquotes "
            f"should name the speaker only. Do NOT append bibliographic tails such as "
            f"'in Nahj al-Balagha (compiled by al-Sharif al-Radi), Hikam (Saying) 147' "
            f"or translator/source-edition details to chapter prose; those are reference "
            f"noise for the audio source.\n"
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
            f"- Apply R-HEADING-CONCISE (2026-06-16): keep every concept `## H2` heading a "
            f"SHORT noun-phrase heading (<= 6 words), like a professional book heading — "
            f"NEVER expand a heading into a full statement. If a heading already reads as a "
            f"sentence, TIGHTEN it to a short noun phrase ('The veiling chain', not 'The "
            f"veiling chain that runs from the Father of Imams to the hidden Imam'); the "
            f"detail belongs in the prose. Structural frame headings keep their canonical shape.\n"
            f"- Apply R-PRESERVE-ARABIC-SOURCE (2026-06-24; supersedes R-NO-ARABIC-NAMES "
            f"/ R-SURAH-ENGLISH-ONLY / R-ALQAAB for Arabic-scholarly content under the "
            f"human phonetic/pronunciation workflow). PRESERVE every Arabic-script term "
            f"that is already present in the chapter source, and preserve every "
            f"transliterated Arabic / Islamic technical term, proper name, book title, "
            f"surah name, and honorific-title (alqaab) exactly as it appears when no "
            f"script is available. Do NOT translate, anglicize, paraphrase, romanize "
            f"Arabic script, or replace terms with English role-labels or audio "
            f"substitutes. The reader edition and the per-term review in the Astro site "
            f"('keep Arabic / fix phonetic / correct Arabic / use English translation') "
            f"depend on these terms surviving intact; the English-vs-Arabic decision is "
            f"made LATER by the human, NOT baked in here. Audio anglicization for TTS is "
            f"applied downstream from the human's decisions, never in the persisted "
            f"chapter source. Established English exonyms for the major prophets remain "
            f"(Noah, Moses, Abraham, Jesus, Adam). Established English alqaab already in "
            f"common use (Commander of the Faithful, Lion of God) may stay English, but "
            f"never STRIP an Arabic term to English on your own initiative.\n"
            f"- Apply the root denoise noise rule: front matter about who should read the "
            f"book, prefaces, descriptions of the book as a book, author biography/posture, "
            f"chain of narrations/transmission, permission-to-read, and book-object "
            f"provenance are noise. Do not restore them during enrichment; preserve only "
            f"real teaching and knowledge.\n"
            f"- Apply R-NO-EPISODE-BRIDGE (hard-gate, 2026-06-08): the chapter file is "
            f"uploaded as a STANDALONE source to NotebookLM — it has no knowledge of other "
            f"episodes. Any prose that references other episodes is rejected by the build "
            f"validator. FORBIDDEN anywhere in the chapter output: 'next episode', 'previous "
            f"episode', 'prior episode', 'earlier episode', 'episode opens', 'episode closes', "
            f"'episode lands'. Do not write bridge paragraphs that narrate what comes before "
            f"or after this chapter. End on the chapter's own content.\n"
            f"- Do NOT modify any other chapter file, contract, or `enrichment-log.md` — "
            f"the orchestrator appends the log row after validating your output.\n\n"
            f"Exit when `{chapter_file}` has been rewritten in place with citations woven in."
        )
            if _modern_science_enabled(book_dir):
                prompt = prompt.replace(
                    "Exit when `",
                    _MODERN_SCIENCE_BLOCK + "\nExit when `",
                    1,
                )

        # Word-count-aware timeout per chapter (2026-05-24 strategy, extended
        # from Phase 0d to Phase 0e). Enrichment is heavier-write than 0d's
        # parse-and-contract, so the same _compute_sc_timeout formula —
        # max(900, min(3600, ceil(words*0.4 + 600))) — gives ch01 (9,645 words)
        # 64 min vs. the prior flat 15 min. ch02 (11,143 words) would have hit
        # the 60-min ceiling; the flat 900s explains why it timed out.
        _pre_enrichment_text = chapter_file.read_text(encoding="utf-8")
        chapter_words = len(_pre_enrichment_text.split())
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

        # Post-enrichment tells check (R-NO-EPISODE-BRIDGE, 2026-06-08).
        # Catch bridge paragraphs early — before per-chapter framing spend.
        _chapter_lower = chapter_file.read_text(encoding="utf-8").lower()
        _found_tells = [t for t in META_PROSE_TELLS if t in _chapter_lower]
        if _found_tells:
            _tell_list = ", ".join(repr(t) for t in _found_tells)
            failures.append((stem, f"episode-bridge tells found: {_tell_list}. "
                             f"Remove all 'next/previous/prior/earlier episode' paragraphs "
                             f"before per-chapter authoring."))
            log(f"    {stem} · FAIL — episode-bridge tells: {_tell_list}")
            continue

        # Shift-left deterministic pre-check (Phase A). Compares the enriched
        # chapter against its pre-enrichment text — flags dropped source
        # (U0E-SHRANK) or burial (U0E-BALLOON) to the human gate + ledger.
        # Flag-and-proceed: NEVER raises, NEVER blocks enrichment. Zero LLM cost.
        try:
            from ._artifact_convergence import run_0e_chapter_precheck
            run_0e_chapter_precheck(
                book_dir, stem, _pre_enrichment_text,
                chapter_file.read_text(encoding="utf-8"),
                file=str(chapter_file), log=log,
            )
        except Exception as _e:  # noqa: BLE001 — a precheck must never break 0e
            log(f"    {stem} · precheck skipped (non-fatal: {_e!r})")

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
    strip_msg += _bake_strip_reference_attribution_noise(book_dir, log=log)
    strip_msg += _bake_inject_chapter_arabic(book_dir, log=log)

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
    here = Path(__file__).resolve().parents[1]
    stripper = here / "strip_inline_phonetics.py"
    if not stripper.exists():
        return ""
    rc, _out, err = _run([sys.executable, str(stripper), "--book-dir", str(book_dir)])
    if rc != 0:
        log(f"  phase 0e · strip_inline_phonetics skipped (rc={rc}): {err.strip()[:200]}")
        return ""
    return " + strip-inline-phonetics"

def _bake_strip_reference_attribution_noise(book_dir: Path, *, log=print) -> str:
    """Run scripts/podcast/strip_reference_attribution_noise.py over chapters/.

    Best-effort: this is a post-enrichment hygiene pass that removes bibliographic
    tails from wisdom/saying blockquotes while preserving the quote and speaker.
    """
    here = Path(__file__).resolve().parents[1]
    stripper = here / "strip_reference_attribution_noise.py"
    if not stripper.exists():
        return ""
    rc, out, err = _run([sys.executable, str(stripper), "--book-dir", str(book_dir)])
    if rc != 0:
        log(f"  phase 0e · strip_reference_attribution_noise skipped (rc={rc}): {err.strip()[:200]}")
        return ""
    if "stripped: 0 reference tails" not in out:
        log("  phase 0e · strip_reference_attribution_noise applied")
    return " + strip-reference-attribution-noise"


def _bake_inject_chapter_arabic(book_dir: Path, *, log=print) -> str:
    """Run scripts/podcast/inject_chapter_arabic.py over Islamic chapters.

    This promotes Arabic from reader overlay metadata into the persisted chapter
    source while keeping phonetic pronunciation guidance in the glossary /
    Customize prompt.
    """
    here = Path(__file__).resolve().parents[1]
    injector = here / "inject_chapter_arabic.py"
    if not injector.exists():
        return ""
    rc, out, err = _run([sys.executable, str(injector), "--book-dir", str(book_dir)])
    if rc != 0:
        log(f"  phase 0e · inject_chapter_arabic skipped (rc={rc}): {err.strip()[:200]}")
        return ""
    if "0 injections" not in out:
        log("  phase 0e · inject_chapter_arabic applied")
    return " + inject-chapter-arabic"
