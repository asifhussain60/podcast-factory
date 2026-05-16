# Expected Output Shape — Synthetic Fixture Verification

This document describes what the `/podcast` skill should produce when run against `fixtures/synthetic-chapter.md`. It is the acceptance criterion for the end-to-end verification.

## Invocation

```
/podcast file:skills-staging/podcast/fixtures/synthetic-chapter.md
```

No flags. The skill should use all defaults.

## Expected metadata detection

The skill should derive (with high confidence):

- **title:** "The Apprentice and the Maker" (from `# Chapter 1 — The Apprentice and the Maker` heading)
- **author:** UNKNOWN — synthetic fixture has no attribution. Skill must stop and ask.

This is a deliberate test of the no-fabrication rule. The skill should write `WORK_DIR/missing-metadata.md` asking the user for an author. For the test, supply: `author: Synthetic Fixture (anonymous)`.

After supplying author, the skill should derive:

- **content_type:** book (Chapter heading + Roman numeral chapter pattern). Confidence ≥ 0.8.
- **period:** undetermined; recorded as "unknown" with confidence 0.
- **genre:** narrative, instructional. Multi-label.
- **audience:** general.
- **tradition:** none (synthetic content has no tradition markers).

## Expected directory structure after run

```
JOURNAL_DIR/_workspace/podcast/the-apprentice-and-the-maker/
  00-source/
    synthetic-chapter.md (copy of fixture)
    MANIFEST.txt
  _extracted/
    raw-text.md
    extraction-log.md
  _metadata.yml
  _cleaned/
    normalized.md
    cleaning-log.md
  _lexicon/
    detected-terms.yml          (empty — no non-Latin script)
    script-summary.md           (notes: no non-Latin scripts detected)
    phonetic-generation-log.md  (empty — no new terms)
  _segments/
    segments.yml                (1 section)
    section-01-the-apprentice-and-the-maker.md
  _enriched/
    section-01-the-apprentice-and-the-maker-enriched.md
  _analogized/
    section-01-the-apprentice-and-the-maker-analogized.md
  _editorial-notes-draft.md
  _quality-gates-report.md
  _apply-review.md              (not yet written until apply)
  01-refined/
    section-01-the-apprentice-and-the-maker.md
  02-instructions/
    podcast-instructions.md
  03-pronunciation.md           (sparse — no foreign terms)
  04-editorial-notes.md
  06-library-proposals.md       (may have clinic proposals; quotes likely 0; glossary 0)
  06b-borderline.md             (may exist if any borderline candidates)
  missing-metadata.md           (initial prompt; can be deleted after author supplied)
```

No `05-export.zip` because it is a single-section source.

## Expected instruction file content

`02-instructions/podcast-instructions.md` should contain:

```
# Podcast Instructions — The Apprentice and the Maker

Source: The Apprentice and the Maker by Synthetic Fixture (anonymous)
Format: Single-section source — one episode below.
Sections: 1

---

Chapter 1 — The Apprentice and the Maker [Deep Dive]
Opening: "Welcome to this episode on _The Apprentice and the Maker_, where today we examine Chapter 1, The Apprentice and the Maker."

Focus on three things only:
  Key concepts:
    – The three levels of mastery: form, function, judgment
    – The discipline of admitting ignorance instead of inventing reasons
    – The difference between competence and mastery
  Teachings:
    – When you do not know, say so — fabrication blocks learning
    – Form without function produces hands; function without judgment produces useful workers; judgment produces makers
  Practical modern applications:
    – Engineers who learn frameworks (form) vs. those who learn architecture principles (function) vs. those who design new systems (judgment)
    – Apprenticeship in medical residency, trades, and other fields where adaptive judgment matters
    – Knowledge work where "I don't know yet" is more valuable than a plausible-sounding guess

Stay on these three. Do not introduce trivial background, biographical filler, or contextual padding unless the section directly demands it.

Format: Deep Dive — single trajectory. One host leads the unfolding of the section's argument; the other interrupts only to clarify, challenge, summarize, or introduce a useful analogy.

---

============================================================
Global episode behavior — every episode, every section
============================================================

[Eight-rule anti-noise block, verbatim from templates/anti-noise-block.md]

Pronunciation: use the English phonetic spellings in the pronunciation
guide that accompanies this instruction file. Do not pronounce any
non-Latin script directly.
```

## Verification checks

After running the skill against this fixture, verify:

### Structural checks

- [ ] All expected files exist in the WORK_DIR.
- [ ] `02-instructions/podcast-instructions.md` opens with the single-sentence opening using "examine" (single-piece verb).
- [ ] The opening mentions both "The Apprentice and the Maker" (italicized) and "Chapter 1, The Apprentice and the Maker".
- [ ] The Focus directive contains key concepts, teachings, AND practical modern applications.
- [ ] The format tag is `[Deep Dive]` (single trajectory, no opposing dialogue).
- [ ] The eight-rule anti-noise block appears once at the end.
- [ ] No bracketed commentary headings anywhere in `01-refined/`.
- [ ] No non-Latin script anywhere in `01-refined/` or `02-instructions/`.

### Quality gate checks

- [ ] Gate 1 (no non-Latin script): PASS
- [ ] Gate 2 (no bracketed commentary): PASS
- [ ] Gate 3 (citation provenance): PASS (no external citations expected)
- [ ] Gate 4 (section order preserved): PASS
- [ ] Gate 5 (word count discipline): PASS (refined within 70-140% of source)

### Content checks

- [ ] Refined text preserves dialogue structure (the maker / apprentice exchange).
- [ ] Refined text preserves the maker's three-levels teaching verbatim or near-verbatim.
- [ ] Modern analogies are woven in without labels (no `[Modern Example]`).
- [ ] Pronunciation guide is sparse (no foreign terms to project).
- [ ] Library proposals: clinic-library may have proposals (psychological pattern: admitting ignorance vs. fabrication); quotes-library likely 0 (no recognized historical figure); glossary 0 (no new terms).

### Generic-only checks

- [ ] No reference to "The Master and the Disciple" anywhere in skill output.
- [ ] No reference to Ismaili tradition (since `source-tradition` resolved to `none`).
- [ ] No Ismaili-specific figures or terms in output.
- [ ] Detected tradition recorded as `none` with confidence note.

## Pass criteria

All of the above checks pass → end-to-end verification PASSES.
Any check fails → fix the implementation and re-run.

## Pre-flight verification of the skill itself

Before running the skill against the fixture, verify the skill's own files are well-formed:

- [ ] `SKILL.md` exists at `journal/skills-staging/podcast/SKILL.md`.
- [ ] All 16 playbooks exist at `playbooks/`.
- [ ] All 5 templates exist at `templates/`.
- [ ] All 6 tradition files + README exist at `traditions/`.
- [ ] No skill file contains the strings "Master and the Disciple", "Saa-lih", "Aboo Maa-lik", or "Al-Bakh-ta-ree" (generic-only audit).
- [ ] Master lexicon has the 11 seed terms in `JOURNAL_DIR/reference/translations-glossary.md`.
