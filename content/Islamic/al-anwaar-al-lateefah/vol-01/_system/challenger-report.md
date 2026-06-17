# Podcast Challenger Report

**Book:** al-anwaar-al-lateefah / vol-01
**Run:** 2026-06-17 (challenger v2.5)
**Scope:** per-chapter the-ladder-of-tawhid (ch08e / EP08)
**content_profile:** islamic_scholarly  ← detected from work.yml (full check catalog, no skips)
**source_tradition:** ismaili → islam pack
**episode_format:** deep_dive (Category P skipped)
**Transcript present:** no (Loop M3/M4, N5, O3, Q5, R6/R7 vacuous)
**Iterations:** 1 (of 5 max; intelligent-break — iteration 2 would yield zero new auto-fixes)
**Verdict:** SHIP-WITH-CAUTION

> Pipeline-internal invocation: Category S1 (async-safety) bypassed per orchestrator parent-process directive (the visible orchestrate_book.py process is THIS pipeline's parent, not a concurrent run).
> CHALLENGER_VERSION read at run time from scripts/podcast/_rules.py = 2.5.

## Hard gates (PASS)

- **build_episode_txt.py** (structural + B/N/O/T gate): exit 0. Chapter (3,402 words) validated and uploaded-as-is; episode CUSTOMIZE PROMPT (716 words) emitted. Two non-blocking P1 advisories from the build script (see below).
- **extract_chapter.py --force** (Category G1/G2/G3 contract gate): contract `the-ladder-of-tawhid.yml` validates; slug parity OK; angle `faithful_exposition` + adaptation_mode `faithful` in enums; meta-prose lint clean.
- **_doctrinal.run_doctrinal_checks** (Category T1–T5): CLEAN (0 findings). "Ali ibn Abi Talib, the Father of Imams" is the canonical naming; no forbidden leadership-title+name pairing. Imam lineage references absent/correct.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | (recovery) | _system/episode-drafts/EP08-the-ladder-of-tawhid/00-framing.md | Restored authored framing after an accidental `extract_chapter.py --force` overwrote it with the contract stub; recovered byte-for-byte from the already-built `episodes/EP08-the-ladder-of-tawhid.txt` (built moments earlier from the authored framing, no stripping needed). 716 words, identical to original. Episode txt re-built clean from the restored framing. |

No catalog auto-fixes (B2/B5/C/E4/H/I/K/M/N/O/R deterministic insertions) were needed: the authored framing already carries the welcome clause, the MODERNIZE + SURPRISE DENY blocks, the formal-transition DENY (Firstly/Furthermore/In conclusion), the no-read-aloud guard (x2), correct host-role declarations, and a Pronunciation block in say-once form. The chapter carries zero inline phonetic parens, zero terse Quran citations, and exactly one honorific (ﷺ, first mention).

## Findings requiring author resolution

### P0 (blocks ship)
None.

### P1 (ship-with-caution)

#### F25-APPARATUS-TABLE: 99-show-notes.md missing the Name and Title Preservation Table
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/_system/episode-drafts/EP08-the-ladder-of-tawhid/99-show-notes.md
- **Context:** build script flags absence of `## Name and Title Preservation Table` (F20/F25 written-layer apparatus crosswalk). NOTE: 99-show-notes.md was regenerated to a stub during this run's extract; it is the published-library written apparatus and does NOT flow to NotebookLM audio. Out of this agent's edit scope (Section 8). Pre-existing authoring gap.
- **Suggested fix:** Author the apparatus table in 99-show-notes.md before the publish gate (preserved Arabic / transliteration → audio-label crosswalk for al-Balagha / al-Lateefah / al-Salat, ilah, alif/lam/ha, Mukathir, tanzih, tajrid, da'wah).

#### R-NO-ARABIC-TRANSLITERATION (F20): 3 Arabic transliterations in chapter SOURCE
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch08e-the-ladder-of-tawhid.txt
- **Context:** `al-Balagha`, `al-Lateefah`, `al-Salat` — all inside verbatim citation lines (`*Nahj al-Balagha*`, the episode-title italic `Al-Anwaar al-Lateefah`, and `Kitab al-Salat` in the Sahih Muslim citation). These are inside bibliographic citations, not spoken doctrinal exposition. The build gate treats this as a non-blocking P1 advisory (exit 0).
- **Suggested fix (author judgment):** These are standard work-title/collection citations; converting them to English audio labels risks obscuring the source. Recommend leaving as-is and relying on the framing's "render Arabic citations as their accurate English meaning only" steering plus the show-notes apparatus. Surfaced for author decision, not auto-fixed (citations are never auto-edited).

#### CS8 (P8): shared 12-word passages with sibling chapters (book-scope)
- **File:** book-scope, n-gram shingle scan via check_chapter_set.py
- **Context (the-ladder-of-tawhid pairs):**
  - vs `the-trust-and-the-science-of-realities`: 31 shared passages — the **Rumi reed-flute** quote ("Listen to the reed, how it tells a tale...") reused as enrichment in two episodes.
  - vs `equal-but-not-infallible` (12) and `the-unknowable-originator-and-the-first-intellect` (8): the **Nahj al-Balagha Sermon 1** attribute-stripping quote ("...the perfection of His purity is to deny Him attributes because every attribute is a proof...").
  - vs `naming-the-unnameable` (3): the **"I cannot enumerate Your praise"** hadith.
- **Assessment:** All four are shared *verbatim quoted citations / liturgical formulae*, which the CS8(b) spec explicitly excludes from the duplication test ("frames + liturgical formulae excluded"). The shingle scanner does not exclude blockquotes, so these lean false-positive. They are NOT re-taught concept prose. The genuine (mild) concern is enrichment-coherence (D3): the same Rumi reed / Sermon 1 quote anchoring multiple episodes weakens its per-episode distinctiveness.
- **Suggested fix (author judgment, book-scope):** Decide whether the reed-flute quote and the Sermon 1 quote should each anchor ONE episode and be referenced (not re-quoted) elsewhere. Never auto-stripped.

#### CS10 (P10): chapter density 6 concept sections (target ≤ 3)
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch08e-the-ladder-of-tawhid.txt
- **Context:** H2 concept sections: The chain of bewilderment / Negating divinity, affirming Allah / The circles of the da'wah / Created gods and the true God / The tranquil soul / The Originator in the Qur'an = 6 (frame headings "Where this episode picks up" + "What this teaching lands" excluded). Target ≤3 per docs/standards/chapter-density.md.
- **Assessment:** Advisory at book scope (CS10). The chapter is `length_target: longer` (2800–4500 band; actual 3,402) and the contract names a deliberate 6-beat walk-in-order exposition. The $0 preflight smoke gate owns halting for `density_standard: 2` books; this book is not flagged that way.
- **Suggested fix (author judgment):** Either accept the density for this climactic "longer" episode or re-split via Phase 0d. Not blocking.

### P2 (advisory)

#### B5: em-dashes in chapter prose (40 in prose, 3 inside verbatim blockquotes)
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch08e-the-ladder-of-tawhid.txt
- **Context:** 40 em-dashes in authored prose; 3 inside verbatim quotes (Nahj al-Balagha line 37, Rumi line 47) which must never be altered.
- **Assessment:** The build gate (the current hard contract) does NOT flag em-dashes for chapters — exit 0 with all 45 present. The spec's B5 auto-fix predates this reconciliation. Mechanically converting 40 prose em-dashes to commas would degrade deliberately authored parenthetical asides (several are grammatically load-bearing em-dash pairs). Per "when in doubt, flag" + "do not corrupt voice," surfaced as P2 advisory rather than auto-fixed.
- **Suggested fix:** If NotebookLM prosody is later observed to stumble, run the normalizer (not a hand-edit) to rebalance the heaviest em-dash sentences.

#### V3: thin modern-relevance bridging in chapter prose
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch08e-the-ladder-of-tawhid.txt
- **Context:** Pure doctrinal exposition; only faint contemporary bridging ("our own", "still"). The framing's Landing supplies the modern hook ("which rank in my life have I let stand in for the One above all") so the conversation will carry it.
- **Assessment:** Softest of the V signals. V1 (opening rhetorical-question hook) and V5 (rhetorical-question cadence throughout) both PASS strongly; V2 (challenge-defeat arc — the danger of mistaking a rank for the Creator, resolved by negation-affirmation) PASS; V4 (no strawman) PASS.

### Non-findings (scanned, cleared)

- **U1 (AI-cliché):** the only substring hit, "today we'll discuss", appears in the framing as a *negated instruction* (`No "today we'll discuss."`) — the framing FORBIDS it. Semantic judgment overrides the substring scanner. CLEAN.
- **A1/A2/A3/A4/A6:** all 4 blockquotes fully cited (Quran 2:32 plain-English + Nasr/Study Quran translator; Nahj al-Balagha Sermon 1 + Sayed Ali Reza; Rumi Mathnawi Book I + Nicholson; Sahih Muslim Kitab al-Salat no. 486 + narrator Aisha). Inline Quran refs (89:27-28, 7:43, 1:2, 1:6-7) all plain-English. No fabricated numbers, no VERIFY/CONTEXT markers.
- **B1–B4, B6:** no meta-prose tells, no cross-episode refs, no file-length self-refs, no translator-apparatus prefixes; all quotes attributable.
- **N1:** zero inline phonetic parens in chapter. **O1:** single honorific (ﷺ) at first mention only.
- **Q1/Q2/Q3:** Host A = scholar/male, Host B = seeker/female; parity holds across EP05/EP07/EP08/EP09/EP10 sibling framings.
- **H1/M1/M2/N4/R4:** welcome + MODERNIZE-DENY + SURPRISE-DENY + no-read-aloud guard + formal-transition DENY all present in framing.

## Health metrics

| Chapter | Words | Enrichment ratio | Tier diversity | Citations | Phonetic gaps |
|---|---|---|---|---|---|
| ch08e-the-ladder-of-tawhid | 3,402 | ~12% (4 blockquotes + bridges) | 4 tiers (Quran, Nahj al-Balagha/Imami, Sufi/Rumi, Sahih Muslim/Sunni — annotated as parallel) | 8 (4 blockquote + 4 inline Quran refs) | 0 |
