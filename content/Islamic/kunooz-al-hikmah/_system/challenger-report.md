# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 (challenger v2.5)
**Scope:** per-chapter ch06a-authors-posture-and-the-line / EP06
**Iterations:** 1 (of 5 max — converged; no auto-fixable findings)
**content_profile:** islamic_scholarly (default — series-config.yaml absent on disk)
**Verdict:** SHIP-WITH-CAUTION

## Auto-fixes applied

None this run. All flagged findings require authoring judgment (framing section pattern compliance + show-notes table schema), not deterministic substitution.

## Findings requiring author resolution

### P0 (blocks ship)

None. Doctrinal gate (T1–T5) clean. No forbidden phrases, no Imam-lineage violations, no fabricated attributions. Meta-prose tells absent. No HTML comments. No inline phonetic parens. No cross-episode references. No AI clichés.

### P1 (ship-with-caution)

#### R-NAMEDISCIPLINE — Rotation triplet on edge of validator threshold
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP06-authors-posture-and-the-line/00-framing.md:15
- **Context:** Line 15 reads `Rotation: the author → the writer of the appendix → the seeker who hastened.` Three aliases separated by →, which should satisfy the rule. Build-script validator nonetheless flagged "no rotation set with 3+ aliases" — likely a pattern-detection edge (validator expects newline-separated rotation lines or a stricter form).
- **Suggested fix:** Add a second rotation triplet for another high-frequency proper noun the hosts will repeat (e.g. `Rotation: the Father of Imams / the master of the line / the leader of the believers`). Two rotation lines unambiguously satisfy the validator and give the hosts more lexical variation.

#### R-CHALLENGER-FRICTION — Pushback patterns absent from Host dynamic
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP06-authors-posture-and-the-line/00-framing.md:33
- **Context:** Host dynamic says "Host B challenges at least 3 times and concedes once" — directive present but no concrete pushback exemplars. Validator wants ≥2 of: "I don't buy that yet…", "That sounds like wordplay…", "Isn't this just replacing…", "How is this different…".
- **Suggested fix:** Add 2-3 exemplar pushback lines Host B can use, anchored to the chapter's actual tensions. Suggested for this chapter: "Isn't 'sin as intended-good-undone' just expanding the word until it loses meaning?" and "How is the closed door at origination different from telling the believer to stop thinking?"

#### R-ANALOGY-CAP — Governing analogies present but not formatted as enumeration
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP06-authors-posture-and-the-line/00-framing.md:37
- **Context:** Tone constraints line 37 names three governing analogies in prose (mountains and sands / treasure with its key / open window at the grave), each correctly tied to a beat. Validator wants explicit enumerated list format (numbered or bulleted).
- **Suggested fix:** Reformat as a bulleted enumeration directly under `## Tone constraints`. Example:
  ```
  Governing analogies (use only these three):
  - mountains and sands — the master's lament (Beat 2)
  - the treasure with its key — the book and the chief teacher's permission (Beat 4)
  - the open window at the grave — three days for the lower marks (Beat 6)
  ```

#### F25-APPARATUS-TABLE — Show-notes table missing required columns
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP06-authors-posture-and-the-line/99-show-notes.md:31
- **Context:** A 2-column "Name and Title Preservation Table" was added (Audio label / Preserved name). Build-script validator requires the canonical 5-column schema: Original/Transliteration | Category | Written Form | Audio Label | First Audio Use.
- **Suggested fix:** Expand the table to the 5-column schema. Existing rows extend naturally — e.g. row 1 becomes `al-Sharif al-Radi | person | Sayyid Sharif al-Radi | the compiler of the Peak of Eloquence | line 21`.

### P2 (advisory)

#### E1 — Chapter word count 6,433 exceeds default soft band
- **File:** content/Islamic/kunooz-al-hikmah/chapters/ch06a-authors-posture-and-the-line.txt
- **Context:** 6,433 words. Contract declares `length_target: 5500-6000` (Extended tier) and framing targets a 50-60 minute conversation. The chapter is 433 words above the contract's upper bound and 933 above the default 5,500 hard cap.
- **Note:** Build script in `--check` mode validated the chapter — the tier-relax setting honored the contract. Surfaced for human judgment: if hard cap at publish time bites, trim ~500 words; otherwise the long form is congruent with the contract's stated target.

## Health metrics

| Artifact | Words | Status |
|---|---|---|
| ch06a-authors-posture-and-the-line.txt (SOURCE) | 6,433 | Above default band — contract `length_target: 5500-6000` |
| EP06 00-framing.md (CUSTOMIZE PROMPT) | 691 | Within band (200–2,000) |

**Structural pass (per category):**

- **A (Authenticity):** Citations carry plain-English Quran refs (chapter/verse + translator), full hadith provenance (collection, book, number, translator), Peak of Eloquence sermon citation with compiler attribution, Pillars of Islam jurist + page range, Daftary academic reference. No `[VERIFY]` or `[CONTEXT NEEDED]` markers. Multi-tier enrichment (Quran, Sunni hadith, Shia/Ismaili sermon, jurist codification, modern scholarship). Tradition-coherence preserved.
- **B (NotebookLM literalness):** No meta-prose tells, no cross-episode references, no file-length self-refs, no translator-apparatus prefixes. 19 em-dashes in chapter prose (would normally B5 auto-fix, but build-script gate did not block; left in place pending tier-relax review).
- **C/O (Pronunciation + honorifics):** First-mention honorific discipline holds (one `(peace be upon him)` for the Prophet, exact phrase once). No inline phonetic parens (R-PHONETICS-OUT clean). No abbreviated work titles in chapter prose.
- **F (Framing integrity):** 8 H2 sections (welcome, name discipline, pronunciation, three-part focus, host dynamic, tone constraints, landing, do-not). Audience concrete (Ismaili-Tayyibi seekers). Tensions named (5 in contract). R-RECURRING-THESIS placements marked 1/2/3 at opening, pivot, close.
- **H/I (Welcome + anti-repetition):** Welcome clause present (line 6, one-sentence intro naming book title + episode pursuit). Anti-repetition signaled through `R-RECURRING-THESIS` discipline (verbatim 3× by design, not free repetition). Landing forbids tidy resolution.
- **K (Interruption):** No bare-affirmation forbidden vocabulary in `## Do not`. "wow" and "right?" explicitly forbidden.
- **M/N (Modernization + phonetic-as-content):** DENY-modernize block present (Twitter, social media, algorithm). No inline phonetic parens. No legacy passive Pronunciation list — uses imperative "Say each term ONCE."
- **Q (Host role parity):** Host A = male, scholar; Host B = female, seeker. Consistent with book-wide pair.
- **R (Conversation choreography):** Cadence implied through "doctrinal and unflinching" tone; no formal-transition DENY phrases explicitly named (Firstly/Secondly/etc not in `## Do not`) — advisory.
- **T (Doctrinal):** Clean. Father of Imams used throughout; forbidden title-and-name pairing absent; Imam lineage references all canonical; no weak/fabricated hadith attributions.
- **U (Scholarly-conversation rubric):** No AI clichés, no faux-profundity opener, no premature-closure tells, no deep-dive self-reference. No external-tradition essentialism.
- **V (Interest):** Strong opening hook (rhetorical question line 3), challenge-defeat arcs in Beats 4-5 (covenant severity / closed door), modern-relevance signal in domestic-edge framing of the three-day window (lines 87+).

