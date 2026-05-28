"""_authoring/chapter_design.py — Phase 0d: chapter design / map-reduce.

Extracted from _authoring.py (A4 split).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ._core import (  # noqa: E402
    AuthoringError,
    DEFAULT_TIMEOUT,
    PHASE_0D_TOC_TIMEOUT,
    PHASE_0D_SC_TIMEOUT,
    _run_claude_p,
    _run_claude_p_with_retry,
    _assert_artifact,
    _compute_sc_timeout,
)

# ─── Phase 0d — Chapter design (map-reduce by source chapter) ────────────────
def author_phase_0d(book_dir: Path, *, length_tier: str = "extended",
                    unit_mode: str = "auto",
                    timeout: int = DEFAULT_TIMEOUT,
                    toc_timeout: int = PHASE_0D_TOC_TIMEOUT,
                    sc_timeout: int = PHASE_0D_SC_TIMEOUT,
                    log=print) -> str:
    """Segment the refined source into meaningful, balanced **episode units**.

    Implemented as a 2-step map-reduce so the LLM never has to author the
    entire book's chapter set in a single shellout:

      Step 1 (TOC + plan, one small call):
          Read refined-english.md, identify source-chapter boundaries
          (by heading or thematic break), and emit a JSON plan to
          `_chunks/0d/source-toc.json`. Each entry pins start_line +
          end_line (1-indexed, inclusive) into refined-english.md, the
          chosen `unit_mode` for that source chapter, the episode count,
          and the kebab-case slug for each episode.

      Step 2 (per-source-chapter loop, one call each):
          For each source chapter in the plan, slice the refined text,
          pass it to a focused `claude -p` call that writes ONLY this
          source chapter's episode files + contracts (with episode
          numbers already pre-assigned from the plan, so the global
          numbering is monotonic). Per-source-chapter rationale +
          source-map rows are written to
          `_chunks/0d/sc-NNN.{rationale,source-map}.md`. A
          `_chunks/0d/sc-NNN.done` marker file makes the loop
          resume-safe — if the orchestrator crashes mid-way, re-running
          only retries the not-yet-done source chapters.

      Step 3 (stitch, deterministic):
          Concat all sc-NNN.rationale.md → chapters-rationale.md.
          Concat all sc-NNN.source-map.md (under one shared pipe-table
          header) → source-chapter-map.md (when unit_mode != chapter).

    `unit_mode` controls how source structure maps to episodes:
      - `chapter` — each source chapter becomes exactly one episode
      - `section` — each source chapter is split into multiple episodes
      - `auto` (default) — Step 1 decides per-chapter based on tier band

    Reads:  BOOK_DIR/_system/source/text/refined-english.md
            BOOK_DIR/_system/source/text/_phonetics.md
    Writes: BOOK_DIR/chapters/ch##[a-z]?-<slug>.txt
            BOOK_DIR/chapter-contracts/<slug>.yml (one per episode)
            BOOK_DIR/_system/source/text/chapters-rationale.md
            BOOK_DIR/_system/source/text/source-chapter-map.md
                (when unit_mode != 'chapter')
            BOOK_DIR/_system/source/text/_chunks/0d/source-toc.json
            BOOK_DIR/_system/source/text/_chunks/0d/sc-NNN.{rationale,source-map}.md
            BOOK_DIR/_system/source/text/_chunks/0d/sc-NNN.done
    """
    import json as _json

    book_slug = book_dir.name
    in_refined = book_dir / "_system" / "source" / "text" / "refined-english.md"
    in_phonetics = book_dir / "_system" / "source" / "text" / "_phonetics.md"
    out_rationale = book_dir / "_system" / "source" / "text" / "chapters-rationale.md"
    out_source_map = book_dir / "_system" / "source" / "text" / "source-chapter-map.md"
    chapters_dir = book_dir / "chapters"
    contracts_dir = book_dir / "chapter-contracts"
    chunks_dir = book_dir / "_system" / "source" / "text" / "_chunks" / "0d"
    toc_path = chunks_dir / "source-toc.json"

    if unit_mode not in ("chapter", "section", "auto"):
        raise AuthoringError(
            phase="0d",
            message=f"unit_mode must be one of chapter|section|auto (got {unit_mode!r})",
        )

    for p in (in_refined, in_phonetics):
        if not p.exists():
            raise AuthoringError(
                phase="0d",
                message=f"prerequisite missing: {p}",
                manual_fallback="Run prior phases (0b, 0c) first.",
            )

    chunks_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    contracts_dir.mkdir(parents=True, exist_ok=True)

    tier_band = {
        "default_deep_dive": "1,800–2,800 words per episode",
        "longer": "2,800–4,500 words per episode",
        "extended": "5,500–9,500 words per episode",
    }.get(length_tier, "5,500–9,500 words per episode (extended)")

    unit_directive = {
        "chapter": (
            "UNIT MODE: **chapter** — every source chapter MUST become exactly ONE episode "
            "(unit_mode='chapter', episode_count=1). Do NOT split any source chapter even if "
            "its word count overflows the tier band."
        ),
        "section": (
            "UNIT MODE: **section** — every source chapter MUST be split into 2 or more "
            "thematic sections (unit_mode='sections', episode_count>=2). Aim for tier-band "
            "compliance per resulting episode."
        ),
        "auto": (
            "UNIT MODE: **auto** — for each source chapter, decide individually: "
            "if its word count is within ±50% of the tier band midpoint, set "
            "unit_mode='chapter' (episode_count=1). If it exceeds 1.5× the tier band's upper "
            "bound, set unit_mode='sections' and pick episode_count so each resulting episode "
            "lands inside the band. Aim for all episodes within ~30% of each other."
        ),
    }[unit_mode]

    # ── STEP 1: TOC + plan ───────────────────────────────────────────────────
    log("  phase 0d · step 1/3 · TOC + segmentation plan")

    if toc_path.exists() and toc_path.stat().st_size > 0:
        log(f"    skip toc (already on disk: {toc_path.name})")
    else:
        toc_prompt = (
            f"You are driving Phase 0d STEP 1 (TOC + segmentation plan) of the /podcast "
            f"skill on book-slug `{book_slug}`. This is a small read-mostly call: you will "
            f"NOT write any chapter or contract files in this step — only one JSON plan.\n\n"
            f"INPUT:  `{in_refined}` (the refined English source)\n"
            f"OUTPUT: `{toc_path}` (machine-readable plan; valid JSON only, no markdown)\n\n"
            f"TASK:\n"
            f"1. Read `{in_refined}` and identify the EPISODE units that serve the\n"
            f"   listener best — NOT the source author's chapter list. The source's own\n"
            f"   chapter breaks are ADVISORY, not authoritative. You are reconfiguring\n"
            f"   the material into episodes; you are not transcribing a table of contents.\n"
            f"   Specifically, you should:\n"
            f"   (a) MERGE adjacent source chapters whose content shares one narrative or\n"
            f"       doctrinal arc that a listener should hear as a single unit (e.g. an\n"
            f"       editor's preface + the opening doctrinal chapter often belong together).\n"
            f"   (b) SPLIT a long source chapter into multiple episodes when it carries\n"
            f"       multiple distinct teachings that would each support a full episode.\n"
            f"   (c) DROP editorial side-matter that wouldn't make a good standalone episode\n"
            f"       (manuscript history, philological appendices) — flag via `essential:\n"
            f"       skip` in the per-chapter contract so Asif can confirm at Phase 0f.\n"
            f"   (d) RE-DRAW boundaries when a thematic seam falls inside a source chapter —\n"
            f"       cut at the seam, not at the source's heading.\n"
            f"   Reflect your reconfiguration in `split_reason` per source chapter.\n"
            f"2. For each output episode unit, compute its line range in `{in_refined}` "
            f"(1-indexed, inclusive — use `wc -l` style counting; lines are separated by "
            f"`\\n`). Also compute its word count (whitespace-split).\n"
            f"3. Apply the following segmentation directive PER SOURCE-OR-RECONFIGURED CHAPTER:\n"
            f"   {unit_directive}\n"
            f"4. Assign monotonically increasing episode numbers (`ep_num`) across the whole "
            f"book starting at 1. Each episode gets a short kebab-case `episode_slug` "
            f"(distinct across the whole book). When a source chapter splits into multiple "
            f"episodes (unit_mode='sections'), each episode's slug must reflect its OWN "
            f"theme, not the source chapter's overall theme.\n\n"
            f"Length tier: **{length_tier}** — target {tier_band}.\n\n"
            f"OUTPUT FORMAT — write to `{toc_path}`, valid JSON, no surrounding text:\n"
            f"```json\n"
            f"{{\n"
            f'  "length_tier": "{length_tier}",\n'
            f'  "unit_mode_input": "{unit_mode}",\n'
            f'  "source_chapters": [\n'
            f'    {{\n'
            f'      "sc_index": 1,\n'
            f'      "source_title": "Introduction",\n'
            f'      "start_line": 12,\n'
            f'      "end_line": 487,\n'
            f'      "word_count": 4280,\n'
            f'      "unit_mode": "chapter",\n'
            f'      "episode_count": 1,\n'
            f'      "episodes": [\n'
            f'        {{ "ep_num": 1, "episode_slug": "the-question-of-authority", '
            f'"section_index": null }}\n'
            f'      ],\n'
            f'      "split_reason": "fits tier band"\n'
            f'    }},\n'
            f'    {{\n'
            f'      "sc_index": 2,\n'
            f'      "source_title": "On the Imamate",\n'
            f'      "start_line": 488,\n'
            f'      "end_line": 1820,\n'
            f'      "word_count": 11400,\n'
            f'      "unit_mode": "sections",\n'
            f'      "episode_count": 2,\n'
            f'      "episodes": [\n'
            f'        {{ "ep_num": 2, "episode_slug": "the-claim-to-succession", '
            f'"section_index": 1 }},\n'
            f'        {{ "ep_num": 3, "episode_slug": "the-tests-of-legitimacy", '
            f'"section_index": 2 }}\n'
            f'      ],\n'
            f'      "split_reason": "1.7x upper bound; thematic seam at the legitimacy tests"\n'
            f'    }}\n'
            f'  ]\n'
            f"}}\n"
            f"```\n\n"
            f"Constraints:\n"
            f"- Write ONLY `{toc_path}`. Do NOT touch any other file.\n"
            f"- The output MUST be valid JSON (parseable by Python's json.loads).\n"
            f"- ep_num starts at 1 and is strictly monotonic across the whole array.\n"
            f"- end_line of source_chapter N must be < start_line of source_chapter N+1.\n"
            f"- episode_slug must be unique across the whole book.\n"
            f"- For unit_mode='chapter', episodes[*].section_index MUST be null.\n"
            f"- For unit_mode='sections', episodes[*].section_index is 1..episode_count.\n\n"
            f"Exit when `{toc_path}` is non-empty and valid JSON."
        )
        rc, stdout, stderr = _run_claude_p(
            toc_prompt, timeout=toc_timeout,
            book_dir=book_dir, phase="0d", step="toc",
        )
        _assert_artifact(
            phase="0d-toc",
            path=toc_path,
            rc=rc,
            stdout=stdout,
            stderr=stderr,
            manual_fallback=(
                f"Author `{toc_path}` manually (see prompt structure in _authoring.py), "
                f"then re-invoke orchestrate-book --resume."
            ),
        )

    # Validate + parse plan.
    try:
        plan = _json.loads(toc_path.read_text(encoding="utf-8"))
    except _json.JSONDecodeError as e:
        raise AuthoringError(
            phase="0d-toc",
            message=f"source-toc.json is not valid JSON: {e}",
            manual_fallback=(
                f"Fix or delete `{toc_path}` and retry Phase 0d "
                f"(--resume --retry-phase 0d)."
            ),
        ) from e

    source_chapters = plan.get("source_chapters") or []
    if not source_chapters:
        raise AuthoringError(
            phase="0d-toc",
            message="source-toc.json has no source_chapters",
            manual_fallback=f"Edit `{toc_path}` to add source_chapters then retry.",
        )

    refined_lines = in_refined.read_text(encoding="utf-8").splitlines()

    # ── STEP 2: per-source-chapter loop ──────────────────────────────────────
    log(f"  phase 0d · step 2/3 · per-source-chapter loop ({len(source_chapters)} chapters)")

    sc_failures: list[tuple[int, str]] = []
    for sc in source_chapters:
        sc_idx = int(sc["sc_index"])
        sc_title = str(sc.get("source_title", f"source chapter {sc_idx}"))
        start_line = int(sc["start_line"])
        end_line = int(sc["end_line"])
        sc_unit_mode = str(sc.get("unit_mode", "chapter"))
        episode_count = int(sc.get("episode_count", 1))
        episodes = sc.get("episodes") or []
        if len(episodes) != episode_count:
            sc_failures.append((sc_idx, f"plan inconsistent: episodes={len(episodes)} != episode_count={episode_count}"))
            continue

        done_marker = chunks_dir / f"sc-{sc_idx:03d}.done"
        rationale_path = chunks_dir / f"sc-{sc_idx:03d}.rationale.md"
        source_map_path = chunks_dir / f"sc-{sc_idx:03d}.source-map.md"
        slice_path = chunks_dir / f"sc-{sc_idx:03d}.in.md"

        if done_marker.exists():
            log(f"    sc {sc_idx:03d}/{len(source_chapters)} · skip (done)")
            continue

        # Slice the refined text for this source chapter.
        if start_line < 1 or end_line > len(refined_lines) or start_line > end_line:
            sc_failures.append((sc_idx, f"bad line range {start_line}-{end_line} (refined has {len(refined_lines)} lines)"))
            log(f"    sc {sc_idx:03d}/{len(source_chapters)} · BAD RANGE")
            continue
        slice_text = "\n".join(refined_lines[start_line - 1:end_line])
        slice_wc = len(slice_text.split())
        slice_path.write_text(slice_text, encoding="utf-8")

        # Expected output filenames for THIS source chapter's episodes.
        expected_chapter_files: list[Path] = []
        expected_contract_files: list[Path] = []
        episode_lines: list[str] = []
        for ep in episodes:
            ep_num = int(ep["ep_num"])
            ep_slug = str(ep["episode_slug"])
            section_index = ep.get("section_index")
            # Naming: chNN-<slug>.txt for whole-chapter; chNN<letter>-<slug>.txt for sections.
            if sc_unit_mode == "sections" and section_index is not None:
                # section_index 1 → 'a', 2 → 'b', etc.
                suffix = chr(ord("a") + int(section_index) - 1)
                fname_base = f"ch{ep_num:02d}{suffix}-{ep_slug}"
            else:
                fname_base = f"ch{ep_num:02d}-{ep_slug}"
            expected_chapter_files.append(chapters_dir / f"{fname_base}.txt")
            expected_contract_files.append(contracts_dir / f"{ep_slug}.yml")
            episode_lines.append(
                f"  - ep_num={ep_num}  slug={ep_slug}  "
                f"chapter_file=`chapters/{fname_base}.txt`  "
                f"contract=`chapter-contracts/{ep_slug}.yml`"
                + (f"  section_index={section_index}" if section_index is not None else "")
            )

        sc_prompt = (
            f"You are driving Phase 0d STEP 2 (per-source-chapter authoring) of the /podcast "
            f"skill on book-slug `{book_slug}`, **source chapter {sc_idx} of "
            f"{len(source_chapters)}** (`{sc_title}`). Read the canonical procedure from "
            f"`skills-staging/podcast/SKILL.md` (search `### PHASE 0d`) for episode-authoring "
            f"discipline.\n\n"
            f"INPUT (the refined English for THIS source chapter only): `{slice_path}`\n"
            f"  · word_count: {slice_wc}  ·  source_line_range: {start_line}-{end_line}\n"
            f"AUTHORITY:\n"
            f"  - `{in_phonetics}` (consult for Arabic terms appearing in this slice)\n"
            f"  - `content/_shared/islam/imam-lineage-ismaili.yml` (canonical Imam lineage —\n"
            f"    Hassan=1st; the literal phrase pairing the leadership-title with the\n"
            f"    personal name of the Father of Imams is FORBIDDEN — always say 'Father\n"
            f"    of Imams') and `naming-conventions.yml`. Do NOT write the literal\n"
            f"    forbidden phrase anywhere — not even inside DO-NOT-SAY guards. The\n"
            f"    doctrinal scanner is substring-only and flags the guard itself.\n"
            f"  - Contract shape: every episode contract under `chapter-contracts/` follows\n"
            f"    the same fields seen in earlier shipped books (see `content/published/books/*/`)\n\n"
            f"PLAN FOR THIS SOURCE CHAPTER (from `{toc_path}`):\n"
            f"  unit_mode: {sc_unit_mode}\n"
            f"  episode_count: {episode_count}\n"
            f"  length_tier: {length_tier} ({tier_band})\n"
            f"  episodes:\n" + "\n".join(episode_lines) + "\n\n"
            f"OUTPUTS (write exactly these files — DO NOT touch any other path):\n"
            + "".join(f"  - `{p}`\n" for p in expected_chapter_files)
            + "".join(f"  - `{p}`\n" for p in expected_contract_files)
            + f"  - `{rationale_path}` (one paragraph per episode in this source chapter; "
            f"each paragraph starts with the episode's filename in backticks)\n"
            + (
                f"  - `{source_map_path}` (pipe-table rows for THIS source chapter, "
                f"NO header — the orchestrator stitches headers later. Format per row: "
                f"`| {sc_idx} | {sc_title} | <comma-sep chapter filenames> | <split_reason> |`)\n"
                if unit_mode != "chapter" else ""
            )
            + f"\nConstraints:\n"
            f"- Use the EXACT episode filenames listed above. Do NOT invent slugs or "
            f"renumber. Pre-assigned ep_num + section_index come from the global plan.\n"
            f"- F4 (2026-05-25): EXCLUDE editorial frontmatter from the episode array. "
            f"If a source-chapter is the editor's introduction, translator's preface, "
            f"publisher's note, manuscript history, biographical sketch of the editor's "
            f"team, or any other non-authorial paratext (signals: not authored by the "
            f"primary source's author; refers to the book in third person as a published "
            f"object; talks about the editor/translator's methodology; reads as scholarly "
            f"apparatus rather than primary content) — DO NOT emit a `chapter-contracts/` "
            f"file for it. Instead include it in `series-plan.md` under a `frontmatter:` "
            f"list with one-line descriptions, so the operator can optionally script an "
            f"intro episode from the apparatus by hand. The PRIMARY-SOURCE chapters "
            f"(numbered abwab, fusul, sections, kandas, books-of-the-X) are what become "
            f"episodes; the apparatus is operator-discretion content.\n"
            f"- Each `chapter-contracts/<slug>.yml` carries: chapter_ref, slug, source_type, "
            f"book_slug=`{book_slug}`, episode_number, title, audience, angle, "
            f"episode_format, format_rationale, essential, essential_rationale, "
            f"host_dynamic, host_dynamic_rationale, length_target, key_tensions, "
            f"tone_constraints, anchor_passages, adaptation_mode=faithful, "
            f"phonetic_overrides, show_notes, "
            f"thesis_relevance.\n"
            f"- F23 (2026-05-25): `thesis_relevance` is a 1-2 sentence statement "
            f"connecting THIS chapter to the BOOK's central thesis (which the "
            f"series-plan declares). Format: 'This chapter advances the book's "
            f"central claim that <THESIS> by <SPECIFIC CONTRIBUTION>.' If the "
            f"chapter does not advance the central thesis (it is digression, "
            f"appendix, supplementary apparatus, or fundraising), set `thesis_relevance: "
            f"\"out-of-scope\"` and EXCLUDE the chapter from the episode array; "
            f"move it to series-plan's `frontmatter:` list with the reason. This "
            f"prevents the F23 failure mode (chapters that don't serve the listener's "
            f"reason for choosing the book getting shipped as full episodes).\n"
            f"\n"
            f"CONTENT-AWARE FIELD ASSIGNMENTS — analyze the source-chapter's rhetorical "
            f"structure to set these fields. Do NOT default blindly.\n"
            f"\n"
            f"  episode_format — one of (decide PER CHAPTER from content; never default\n"
            f"  to a book-wide pattern):\n"
            f"    * deep_dive: chapter unfolds ONE position layer-by-layer. Use ONLY when\n"
            f"      there is NO named opposing voice running through the chapter — i.e.,\n"
            f"      editor's introductions, monological cosmology, narrative-without-dispute,\n"
            f"      synthesis chapters that gather earlier threads without re-opening them.\n"
            f"    * debate: chapter contains two or more NAMED voices in extended back-and-\n"
            f"      forth on a discernible proposition. The QUALIFYING signal is sustained\n"
            f"      NAMED-OPPOSITION-WITH-DIALOGUE (>=40% of chapter word count voiced by the\n"
            f"      opposing party, with the chapter's spine being the contest itself).\n"
            f"      CRITICAL: A chapter is STILL debate when one side concedes by the close.\n"
            f"      Concession-arcs are NOT teaching dialogues — they are debates with\n"
            f"      `resolution: host_b_concedes` (or `host_a_concedes`). The challenger's\n"
            f"      Category P2 explicitly accepts those resolution enums. Examples:\n"
            f"      Salih+Abu-Malik dialogues in *Master and Disciple*; al-Kirmani's named\n"
            f"      adjudication of al-Islah vs al-Nusra. Do NOT downgrade to deep_dive just\n"
            f"      because the foil-voice eventually consents.\n"
            f"    * interview: chapter is Q&A structured (rare in primary sources).\n"
            f"    * narrative: chapter is pure historical/biographical exposition (no\n"
            f"      doctrinal dispute, no exposition-of-position — just events).\n"
            f"  format_rationale: 2-3 sentences — name the textual evidence that drove the\n"
            f"    choice. For debate, name (1) the opposing party, (2) the proposition under\n"
            f"    contest, (3) the resolution enum that matches the chapter's outcome. For\n"
            f"    deep_dive, name the one unfolding doctrine + confirm NO sustained named\n"
            f"    opposition runs through the chapter. Do not default to a book-wide pattern;\n"
            f"    if 5 of 7 chapters are deep_dive and 2 are debate, that diversity is the\n"
            f"    correct answer when the content shape varies.\n"
            f"\n"
            f"  essential — one of:\n"
            f"    * core: required for the doctrinal/argumentative arc; cannot be removed\n"
            f"      without breaking the listener's understanding.\n"
            f"    * optional: useful context but the listener can skip it without losing\n"
            f"      the thread (e.g., an editor's overview of who the protagonists are).\n"
            f"    * bonus: scholarly bookkeeping (manuscript history, philological notes,\n"
            f"      footnote material). Listeners gain little; keep accessible for completists.\n"
            f"    * skip: editorial side-matter with minimal listener value; recommend\n"
            f"      cutting from the main series.\n"
            f"  essential_rationale: ONE sentence — what content drives the verdict (e.g.,\n"
            f"    'Pure manuscript-history bookkeeping by the 20th-century editor; no source\n"
            f"    doctrine present').\n"
            f"\n"
            f"  host_dynamic — derive from episode_format:\n"
            f"    * deep_dive → 'curious_mind + scholar_companion' (Mentor + Student)\n"
            f"    * debate (3+ voices) → 'advocate_a + advocate_b + arbiter'\n"
            f"    * debate (2 voices) → 'advocate + arbiter'\n"
            f"    * narrative → 'narrator + companion'\n"
            f"    * interview → 'interviewer + subject'\n"
            f"  host_dynamic_rationale: ONE sentence naming who-plays-what for THIS chapter\n"
            f"    (e.g., 'advocate_a voices al-Islah's gentle/dense proportion, advocate_b\n"
            f"    voices al-Nusra's structural parallel, arbiter delivers al-Kirmani's\n"
            f"    settlement that opposites do not meet in the same place').\n"
            + (
                "  - When this episode is a section of a longer source chapter, also include "
                "`source_chapter_ref` (the sc_index) and `section_index` (1-based) in the "
                "contract.\n"
                if sc_unit_mode == "sections" else ""
            )
            + f"- Each chapter txt MUST land inside the tier band ({tier_band}).\n"
            f"- Do NOT modify any file outside the named outputs (in particular, do NOT "
            f"touch other source-chapter slices or other episodes' files).\n"
            f"- Do NOT write `{toc_path}` or `{chapters_dir.parent / '_system' / 'source' / 'text' / 'chapters-rationale.md'}` — "
            f"the orchestrator stitches those.\n\n"
            f"Exit when every output file above exists and is non-empty."
        )

        # Word-count-aware timeout per source chapter (2026-05-24 strategy).
        # Replaces the prior global sc_timeout. Tracks slice_wc so dense
        # chapters get the budget they need without short ones overpaying.
        per_sc_timeout = _compute_sc_timeout(slice_wc)
        log(f"    sc {sc_idx:03d}/{len(source_chapters)} · authoring "
            f"({episode_count} ep, {slice_wc} src words, timeout={per_sc_timeout}s) · "
            f"`{sc_title[:50]}`")
        try:
            rc, stdout, stderr = _run_claude_p_with_retry(
                sc_prompt, timeout=per_sc_timeout,
                book_dir=book_dir, phase="0d", step=f"sc-{sc_idx:03d}",
                log=log,
            )
        except AuthoringError as e:
            # Halt-and-surface path: both attempts timed out. Don't continue
            # the loop — propagate so the orchestrator surfaces the decision
            # to the user via the standard AuthoringError flow.
            if "BOTH attempts timed out" in str(e):
                raise
            # Other AuthoringError shapes (e.g. claude binary missing)
            # also propagate — they're not transient.
            raise
        if rc != 0:
            # Transient (network/API/quota) — log + continue; resume retries.
            # P5.2: capture stdout AND stderr in the failure record.
            sc_failures.append(
                (
                    sc_idx,
                    f"rc={rc}: stderr={(stderr or '').strip()[:300]} | "
                    f"stdout={(stdout or '').strip()[:300]}",
                )
            )
            log(f"    sc {sc_idx:03d}/{len(source_chapters)} · FAILED rc={rc}")
            continue

        # Validate this source chapter's outputs.
        missing = [str(p) for p in expected_chapter_files + expected_contract_files
                   if not p.exists() or p.stat().st_size == 0]
        if not rationale_path.exists() or rationale_path.stat().st_size == 0:
            missing.append(str(rationale_path))
        if unit_mode != "chapter" and (not source_map_path.exists() or source_map_path.stat().st_size == 0):
            missing.append(str(source_map_path))
        if missing:
            # P5.2: rc=0 with missing artifacts is the P5.1 failure class —
            # LLM exited cleanly without writing. Fatal, not retryable.
            raise AuthoringError(
                phase="07-chapter-design",
                message=(
                    f"sc {sc_idx:03d}/{len(source_chapters)} ({sc_title!r}) "
                    f"returned rc=0 but produced no artifacts for: {missing[:5]}. "
                    f"P5.1 failure class — claude -p exited cleanly without "
                    f"writing the expected files. After --permission-mode "
                    f"acceptEdits, this should not recur; surfaces here "
                    f"indicate a content-filter refusal, quota hit, or prompt "
                    f"issue."
                ),
                manual_fallback=(
                    f"Inspect stdout/stderr attached to this error. If the "
                    f"prompt needs adjusting, edit and resume. If transient "
                    f"quota, retry. DO NOT silently advance."
                ),
                stdout=stdout or "",
                stderr=stderr or "",
            )

        # All good → checkpoint.
        done_marker.write_text(
            f"sc_index={sc_idx}\nsource_title={sc_title}\nepisode_count={episode_count}\n",
            encoding="utf-8",
        )
        log(f"    sc {sc_idx:03d}/{len(source_chapters)} · OK")

    if sc_failures:
        raise AuthoringError(
            phase="0d",
            message=(
                f"{len(sc_failures)} of {len(source_chapters)} source chapters failed: "
                + "; ".join(f"sc {i}: {m}" for i, m in sc_failures[:3])
            ),
            manual_fallback=(
                f"Inspect _chunks/0d/sc-NNN.in.md for failed source chapters; "
                f"drive each manually via /podcast, then re-invoke "
                f"orchestrate-book --resume (already-done source chapters are skipped via "
                f"the .done marker file)."
            ),
        )

    # ── STEP 3: stitch ────────────────────────────────────────────────────────
    log("  phase 0d · step 3/3 · stitch rationale + source-map")

    rationale_parts: list[str] = []
    for sc in source_chapters:
        sc_idx = int(sc["sc_index"])
        rp = chunks_dir / f"sc-{sc_idx:03d}.rationale.md"
        if rp.exists() and rp.stat().st_size > 0:
            sc_title = str(sc.get("source_title", f"source chapter {sc_idx}"))
            rationale_parts.append(f"## Source chapter {sc_idx} — {sc_title}\n\n{rp.read_text(encoding='utf-8').strip()}\n")
    out_rationale.write_text("\n".join(rationale_parts) + "\n", encoding="utf-8")

    if unit_mode != "chapter":
        header = (
            "| source chapter | source title | episode(s) | split reason |\n"
            "|---|---|---|---|\n"
        )
        sm_rows: list[str] = []
        for sc in source_chapters:
            sc_idx = int(sc["sc_index"])
            smp = chunks_dir / f"sc-{sc_idx:03d}.source-map.md"
            if smp.exists() and smp.stat().st_size > 0:
                sm_rows.append(smp.read_text(encoding="utf-8").strip())
        out_source_map.write_text(header + "\n".join(sm_rows) + "\n", encoding="utf-8")

    # Final sanity check — at least one chapter + contract present.
    if not list(chapters_dir.glob("ch*.txt")):
        raise AuthoringError(
            phase="0d",
            message=f"Phase 0d produced no chapter files under {chapters_dir}",
            manual_fallback="Inspect _chunks/0d/sc-NNN.done markers and chapters/ dir.",
        )
    if not list(contracts_dir.glob("*.yml")):
        raise AuthoringError(
            phase="0d",
            message=f"Phase 0d produced no contracts under {contracts_dir}",
            manual_fallback="Inspect _chunks/0d/sc-NNN.done markers and chapter-contracts/ dir.",
        )

    total_episodes = sum(int(sc.get("episode_count", 1)) for sc in source_chapters)
    return (
        f"0d map-reduce: {len(source_chapters)} source chapters → "
        f"{total_episodes} episodes (chapters + contracts written)"
    )


