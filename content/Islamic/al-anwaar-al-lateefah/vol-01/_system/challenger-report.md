# Podcast Challenger Report

**Book:** al-anwaar-al-lateefah/vol-01
**Run:** 2026-06-17 (challenger v2.5)
**Scope:** per-chapter `origination-from-nothing` (ch09f + EP09)
**Iterations:** 1 (of 5 max — intelligent break: zero safe auto-fixes available, finding set stable)
**Verdict:** SHIP-WITH-CAUTION (P0=0 · P1=3 · P2=2)
**content_profile:** islamic_scholarly  ← detected from work.yml / orchestrator-state.json (full 30-check catalog applies)

> Prior run was BLOCKED on a T2 framing ordinal error (line 10). That P0 is now RESOLVED: the framing labels Imam Zayn al-Abidin as "the third Imam," which is correct in the Nizari/Mustaali Ismaili lineage (Hassan=1, Hussain=2, Zayn al-Abidin=3 per content/_shared/islam/imam-lineage-ismaili.yml). T1/T2/T3 all re-run clean on both chapter and framing.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | None. No deterministic auto-fix was applicable this run. |

Notes on the auto-fix scan:
- **B5 (em-dashes):** the chapter uses em-dashes throughout. The live build contract (`build_episode_txt.py::validate_chapter`, the authority per Section 0) does NOT gate on em-dashes, and the entire vol-01 corpus uses them by design. Auto-stripping every em-dash would corrupt authored prose against the live contract, so B5 is treated as superseded by the build-script reality and was NOT applied.
- **B2 (cross-episode refs):** the only regex hit ("do not announce a next chapter", framing line 39) is an instruction *forbidding* such a reference, not a reference. False positive — no fix.
- **N1 (inline phonetics):** none present (build N1 gate passed).
- **O1 (honorific repeats):** `(peace be upon him)` appears exactly once (first mention of Imam Zayn al-Abidin) — correct, no strip.
- **O2 (abbreviations), E4/U1 (filler / AI-cliche):** clean.

## Findings requiring author resolution

### P0 (blocks ship)

None. The chapter is authentic, doctrinally clean, and the prior framing ordinal P0 is resolved.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION (F20) — 9 transliterations in the chapter SOURCE
- **File:** chapters/ch09f-origination-from-nothing.txt
- **Context:** Build-gate flagged 9 transliterations — sample: `Ibn Ata`, `al-Sahifa al-Sajjadiyya`, `al-Abidin`, `al-Badi'`, `Kitab al-Hikam`, `al-Iskandari`. Every one sits inside an attribution/citation line or a proper book/author title (the divine name al-Badi' is glossed inline as "the Originator"). F20 doctrine: the uploaded SOURCE is read aloud, so Arabic names should carry English audio labels with the Arabic preserved in the written-layer apparatus.
- **Disposition:** Flag (P1), not auto-fixed. The author decides per-token which to relabel vs. preserve as a canonical citation; citation lines are an authoring decision (the challenger never edits citations).

#### F25-APPARATUS-TABLE — 99-show-notes.md missing the Name & Title Preservation Table
- **File:** _system/episode-drafts/EP09-origination-from-nothing/99-show-notes.md
- **Context:** No `## Name and Title Preservation Table` header. F25 doctrine: the written-layer apparatus carries the preserved Arabic / transliteration → audio-label crosswalk that the TTS-safe audio omits.
- **Disposition:** Flag (P1). 99-show-notes.md is out of the challenger's edit scope (Section 8); this belongs to the show-notes generator. Pairs with the R-NO-ARABIC-TRANSLITERATION finding above — adding the table is the written-layer home for those preserved names.

#### R-DRAMATIC-ARC — framing uses a 3-beat focus, not a 6-beat arc
- **File:** _system/episode-drafts/EP09-origination-from-nothing/00-framing.md:19-23
- **Context:** `## Three-part focus` is a 3-beat walk (world of origination → favor not need → luminous forms made equal). The build gate's R-DRAMATIC-ARC wants a 6-beat crisis/failed-answer/pivot/stakes arc.
- **Disposition:** Flag (P1), advisory. The contract is `episode_format: deep_dive`, `angle: faithful_exposition` over monological cosmology — the deliberate 3-beat exposition is the authored shape, and the framing carries strong steering (spine-verbatim x3, three governing analogies, host-friction script). Author may keep the 3-beat structure or restructure to 6 beats; not a content defect.

### P2 (advisory)

#### R-NAMEDISCIPLINE — regex expects a rotation set; framing uses one-label-per-figure
- **File:** _system/episode-drafts/EP09-origination-from-nothing/00-framing.md:6-12
- **Context:** The build regex looks for a `a / b / c` rotation set with 3+ aliases. The framing instead applies the stricter and correct discipline — ONE English label per figure, never rotating ("the Originator", "the master expositor", "the third Imam", "a Sufi master"). The framing follows the right rule; the regex shape is a known false positive for the one-label-per-figure pattern.
- **Disposition:** Advisory. No action; the framing's name discipline is correct.

#### R-HONORIFIC-BOTH-BOUNDS — expects a Prophet first-mention honorific
- **File:** _system/episode-drafts/EP09-origination-from-nothing/00-framing.md
- **Context:** The gate wants `peace and blessings of Allah...` to occur exactly once (first mention of the Prophet). This chapter and framing do not mention the Prophet at all — the content is origination cosmology and Imam Zayn al-Abidin. The honorific correctly does not appear.
- **Disposition:** Advisory / false positive for this chapter's content. The one honorific that IS present — `(peace be upon him)` on the third Imam — is correctly placed once.

### Book-scope context (CS — NOT findings against this chapter)

`check_chapter_set.py` reports 25 book-scope P1s (15× CS8/P8 shared-passage, 10× CS10/P10 over-dense). **None name `origination-from-nothing`** — this chapter appears in zero duplication pairs and is not in the over-dense list. The shared-passage hits are mostly repeated citation formulae ("nahj al balagha compiled by...") across OTHER chapters; CS10 density is advisory. Out of scope for this per-chapter focus run; surfaced here for awareness only.

## Health metrics

| Chapter | Words | Citations | Tiers | Translators named | Phonetic gaps | Doctrinal |
|---|---|---|---|---|---|---|
| ch09f-origination-from-nothing | 3,296 | 5 (3 Quran, 1 Sajjadiyya du'a, 1 Sufi hikam) | 4+ (Quran / Imami du'a / Sufi / Ismaili expositors) | 3/3 (Study Quran, Chittick, Danner) | 0 | clean (T1/T2/T3 = 0) |

Framing: 745 words (within band). Enrichment ratio well under 60%. Citation discipline (A1–A6), translation provenance (A3), and cross-tradition annotation (A6 — Sufi + Imami sources each framed in their own tradition) all pass.
