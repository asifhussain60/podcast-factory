"""Phase 0d step 1's prompt: the TOC and segmentation plan.

Split out of `_chapter_design.py` (2026-08-31, DR-005): that file is a
grandfathered over-limit module — "split, never grow" — and this is the largest
thing in it that is not orchestration. The move completes an intent the function
already stated about itself: it was "extracted verbatim from author_phase_0d so
prompt wording is maintained apart from the phase orchestration", and a separate
module is where that separation actually holds.

ONE BEHAVIOURAL DIFFERENCE, and it is deliberate: `episode_max_concepts` is now
a parameter. It used to be read from `_chapter_design.EPISODE_MAX_CONCEPTS`, a
module global that `author_phase_0d` REASSIGNS per book. Read from here that
would have frozen at the import-time default of 3 and silently ignored every
book's override — so the caller passes the value it just computed instead of
this module reaching for it.
"""

from __future__ import annotations

from _authoring._supplied_chapters import _supplied_chapters_block


def _build_phase_0d_toc_prompt(
    *,
    book_slug,
    in_content,
    toc_path,
    _gap_context_block,
    consolidation_directive,
    tier_band,
    unit_directive,
    inventory_block,
    density_advisory_block,
    density_ceiling_hint,
    length_tier,
    unit_mode,
    supplied_chapters=None,
    episode_max_concepts=None,
) -> str:
    """STEP 1 TOC + segmentation-plan prompt. Extracted verbatim from
    author_phase_0d (audit Spec 2) so prompt wording is maintained apart from
    the phase orchestration. EPISODE_MAX_CONCEPTS is a module global.
    """
    return (
        f"You are driving Phase 0d STEP 1 (TOC + segmentation plan) of the /podcast "
        f"skill on book-slug `{book_slug}`. This is a small read-mostly call: you will "
        f"NOT write any chapter or contract files in this step — only one JSON plan.\n\n"
        f"INPUT:  `{in_content}` (the refined English source)\n"
        f"OUTPUT: `{toc_path}` (machine-readable plan; valid JSON only, no markdown)"
        f"{_gap_context_block}\n\n"
        f"TASK:\n"
        f"{_supplied_chapters_block(supplied_chapters)}"
        f"1. Read `{in_content}` and identify the EPISODE units that serve the\n"
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
        f"{consolidation_directive}"
        f"   Reflect your reconfiguration in `split_reason` per source chapter.\n"
        f"2. For each output episode unit, compute its line range in `{in_content}` "
        f"(1-indexed, inclusive — use `wc -l` style counting; lines are separated by "
        f"`\\n`). Also compute its word count (whitespace-split).\n"
        f"3. Apply the following segmentation directive PER SOURCE-OR-RECONFIGURED CHAPTER:\n"
        f"   {unit_directive}\n"
        f"3b. HARD DENSITY FLOOR — ARITHMETIC, NOT JUDGEMENT (no exceptions unless the\n"
        f"   directive above is the forced single-episode 'chapter' mode): for EVERY\n"
        f"   source-or-reconfigured chapter, `episode_count` MUST be >= ceil(word_count /\n"
        f"   {density_ceiling_hint}). A chapter whose word_count exceeds {density_ceiling_hint:,} is\n"
        f"   NEVER one episode — e.g. a {density_ceiling_hint + 218:,}-word chapter REQUIRES\n"
        f"   episode_count >= 2 (set unit_mode='sections', cut at the nearest thematic\n"
        f"   seam). 'It is one coherent teaching' is NOT a valid reason to exceed the\n"
        f"   floor. A plan that violates this floor is rejected and you will be re-run, so\n"
        f"   compute ceil(word_count / {density_ceiling_hint}) for each chapter and honour it.\n"
        f"3c. CONCEPT CEILING — SECOND FLOOR, SAME DISCIPLINE (R-MAX-CONCEPTS, MANDATORY):\n"
        f"   each episode covers AT MOST {episode_max_concepts} distinct concept-level topics. ENUMERATE the\n"
        f"   distinct teachings of each source chapter in a `topics` string array on that\n"
        f"   source chapter's plan entry (one short title per topic), and require\n"
        f"   episode_count >= ceil(len(topics) / {episode_max_concepts}). A 5,400-word chapter that carries 9\n"
        f"   distinct teachings is THREE episodes even though it fits one episode by word\n"
        f"   count. Both floors are enforced by deterministic gates: the plan parser\n"
        f"   computes ceil(len(topics) / {episode_max_concepts}) per source chapter and REJECTS any plan\n"
        f"   whose episode_count is lower, and a post-write gate rejects chapters that\n"
        f"   come out with more than {episode_max_concepts} concept sections. Merging several teachings\n"
        f"   under one umbrella heading does NOT reduce the topic count — count at the\n"
        f"   grain a listener experiences: one teachable unit = one topic.\n"
        f"   When splitting by topic, keep each concept WHOLE inside one episode — never\n"
        f"   leave a concept's argument straddling an episode boundary — and order the\n"
        f"   episodes so each one's closing hands off naturally to the next one's opening.\n"
        f"{inventory_block}"
        f"{density_advisory_block}"
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
        f"    {{\n"
        f'      "sc_index": 1,\n'
        f'      "source_title": "Introduction",\n'
        f'      "start_line": 12,\n'
        f'      "end_line": 487,\n'
        f'      "word_count": 4280,\n'
        f'      "topics": ["The question of authority", "Why a living guide", '
        f'"The covenant"],\n'
        f'      "unit_mode": "chapter",\n'
        f'      "episode_count": 1,\n'
        f'      "episodes": [\n'
        f'        {{ "ep_num": 1, "episode_slug": "the-question-of-authority", '
        f'"section_index": null }}\n'
        f"      ],\n"
        f'      "split_reason": "fits tier band"\n'
        f"    }},\n"
        f"    {{\n"
        f'      "sc_index": 2,\n'
        f'      "source_title": "On the Imamate",\n'
        f'      "start_line": 488,\n'
        f'      "end_line": 1820,\n'
        f'      "word_count": 11400,\n'
        f'      "topics": ["The claim to succession", "The designation texts", '
        f'"The tests of legitimacy", "The counter-claims answered", '
        f'"The unbroken chain", "The seal of the argument"],\n'
        f'      "unit_mode": "sections",\n'
        f'      "episode_count": 2,\n'
        f'      "episodes": [\n'
        f'        {{ "ep_num": 2, "episode_slug": "the-claim-to-succession", '
        f'"section_index": 1 }},\n'
        f'        {{ "ep_num": 3, "episode_slug": "the-tests-of-legitimacy", '
        f'"section_index": 2 }}\n'
        f"      ],\n"
        f'      "split_reason": "1.7x upper bound; thematic seam at the legitimacy tests"\n'
        f"    }}\n"
        f"  ]\n"
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
