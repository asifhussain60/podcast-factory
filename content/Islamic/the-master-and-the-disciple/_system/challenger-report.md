# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-10 (challenger v2.2)
**Scope:** per-chapter `hawl-quwwa-and-josephs-dream`
**Iterations:** 1 (of 5 max)
**Verdict:** SHIP-WITH-CAUTION
**content_profile:** islamic_scholarly (from _system/series-config.yaml)

## Auto-fixes applied (iteration-by-iteration)

None. All findings are either author-judgment (out of auto-fix scope) or book-wide archetype patterns recurring across all sibling episodes.

## Findings requiring author resolution

### P0 (blocks ship)

None. `build_episode_txt.py --check` validates cleanly; chapter at 2,315 words sits inside the 1,800–2,800 default-deep-dive band; framing at 749 words sits inside the soft band.

### P1 (ship-with-caution)

#### R-NAMEDISCIPLINE — Name discipline section lacks rotation set
- **File:** `_system/episode-drafts/EP09-hawl-quwwa-and-josephs-dream/00-framing.md`, `## Name discipline` (lines 6–16)
- **Context:** Section uses stable single labels (the Imam, the gateway, the speaker-prophet, the executor, the proof, the twelve chiefs, the callers) but does not declare a `Rotation: a / b / c` line with 3+ aliases per term.
- **Assessment:** Book-wide archetype pattern; the same shape recurs across all sibling episodes already shipped on this branch. Single-label stability has been the deliberate design choice for this dialogue — the master/disciple register depends on the listener locking each role to one English label.
- **Suggested fix:** Archetype-level decision; not a per-chapter fix.

#### R-DRAMATIC-ARC — Three-part focus has 3 Beat markers, only 1/4 structure tells
- **File:** `_system/episode-drafts/EP09-hawl-quwwa-and-josephs-dream/00-framing.md`, `## Three-part focus` (lines 32–35)
- **Context:** Three beats present (Absurdity of literal readings → Hawl/quwwa as Imam/gateway → Joseph's dream and the king's vision). Build rule wants a 6-beat arc with crisis / failed answer / pivot / stakes markers.
- **Assessment:** Book-wide archetype; all sibling episodes use the three-beat shape that matches the source's doctrinal-exposition register. The dialogue's natural rhythm does not take a 6-beat dramatic structure.
- **Suggested fix:** Archetype-level decision; not a per-chapter fix.

#### R-HONORIFIC-BOTH-BOUNDS — `peace be upon him` 0 occurrences in framing (required: 1)
- **File:** `_system/episode-drafts/EP09-hawl-quwwa-and-josephs-dream/00-framing.md`, `## Name discipline` line 15
- **Context:** Framing uses `peace and blessings of Allah be upon him and his family` (the full Shia/Ismaili honorific form) at first mention of the Prophet. Build rule expects literal substring `peace be upon him` exactly once.
- **Assessment:** Sectarian-register choice — the longer Shia/Ismaili honorific is doctrinally appropriate for this book. The rule was written for general Islamic register. Chapter body line 9 carries `(peace be upon him)` exactly once on the Prophet as required, so the chapter passes; the gate triggers only on framing.
- **Suggested fix:** Author may add the shorter form at first mention, OR archetype-level rule relaxation for Shia/Ismaili books.

#### F25-APPARATUS-TABLE — `99-show-notes.md` missing `## Name and Title Preservation Table`
- **File:** `_system/episode-drafts/EP09-hawl-quwwa-and-josephs-dream/99-show-notes.md`
- **Context:** F25 doctrine requires every episode's show-notes to carry the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) that the TTS-safe audio omits.
- **Assessment:** Book-wide archetype pattern; apparatus generator scope item.
- **Suggested fix:** Archetype-level decision; not a per-chapter fix.

### P2 (advisory)

None.

## Categories scanned

- **A (Authenticity):** Chapter cites Bukhari for the hadith of the formula (vol. 9, p. 281, Khan/Darussalam 1997), Arberry for Quran 12:4 + 12:8, Daftary (Cambridge 2007 pp. 138–141), Corbin (Kegan Paul 1983 pp. 60–64), and Schimmel (UNC 1985 pp. 64–67). Multi-tier (Tier 1 Quran, Tier 3 hadith, Tier 5 Ismaili secondary, Tier 6 scholarship). Translator named on first Quranic translation. ✓
- **B (NotebookLM literalness):** No meta-prose tells, no cross-episode references, no em-dashes in violation, no translator-apparatus prefixes. ✓
- **C (Pronunciation discipline):** Framing carries imperative `## Pronunciation` block. Honorific applied once at first mention in chapter line 9. ✓
- **D (Enrichment & depth):** 3+ tiers, enrichment ratio ~22%, all citations bind to the chapter's tensions (chain of intermediaries, esoteric reading of dream-numerology). No `[CONTEXT NEEDED]` markers. ✓
- **E (Articulation & shape):** Word count 2,315 inside default-deep-dive band. Beginning-middle-end arc present. No filler tells. ✓
- **F (Framing integrity):** Four-part structure present. Audience inferred from book-wide profile. 2 tensions named. ✓
- **G (Extract Mode contracts):** Not applicable for this book (no `chapter-contracts/` directory).
- **H (Welcome opening + closing landing):** Welcome present in Opening; close turns listener outward to weekly practice. ✓
- **I (Anti-repetition):** R-RECURRING-THESIS placement 1/2/3 declared. ✓
- **J (Name aliasing):** Name discipline block present. ✓ (one P1 noted above on rotation set)
- **K (Interruption avoidance):** Host dynamic carries friction script with explicit "concedes once" cadence. ✓
- **M (Modernization + surprise-noise audit):** `## Do not` block names Twitter, social media, algorithm, "wow", "right?", "deep dive", "today's episode", "let's dive in", "buckle up", "mind blown". ✓
- **N (Phonetic-as-content):** Chapter contains zero inline phonetic parens. Framing uses imperative `Pronounce` directives ("Say each term ONCE. Never say the original spelling and the English form back-to-back."). No-read-aloud guard present at line 49. ✓
- **O (Honorific repetition + abbreviation):** "peace be upon him" appears once in chapter line 9. Forbidden abbreviations absent. ✓
- **Q (Host role parity book-wide):** Host A = male/John/scholar; Host B = female/Hannah/seeker. Consistent with sibling episodes on this branch. ✓
- **R (Conversation choreography):** Tone block locks 3 governing analogies. R-RECURRING-THESIS spine repeats verbatim three times. ✓
- **S (Safety + Boundary):** S1 bypassed per pipeline-context instruction (parent orchestrator is THIS pipeline). S2–S6 clean. ✓
- **T (Doctrinal accuracy):** Build-time `assert_doctrinal_clean()` passed during `--check`. No mis-attribution; no Imam-lineage violation; no forbidden naming-convention phrases. Joseph's-dream reading remains in the Ismaili exegetical lineage already attested by Daftary/Corbin/Schimmel. ✓
- **U (Scholarly-conversation rubric v2.2):** No AI-cliché smells, no faux-profundity opening, no premature-closure wrap-up, no deep-dive self-reference, no external essentialism. ✓
- **V (Interest & engagement):** Curiosity hook (the absurdity move at the open) + challenge-defeat arc + modern-relevance signal (the "every line you recite without hearing" close). ✓
- **W (Augmentation quality):** No augmentation ledger entries for this episode — base chapter ships unmodified. ✓
- **CS (Chapter-set design):** Single-chapter scope; not re-run at book level for this invocation.

## Health metrics

| Chapter | Words | Enrichment ratio | Tier diversity | Citations | Phonetic gaps |
|---|---|---|---|---|---|
| ch09b-hawl-quwwa-and-josephs-dream | 2,315 | ~22% | 4 tiers | 5 | 0 |

## Verdict

**SHIP-WITH-CAUTION.** Zero P0 findings. Four P1 findings are all book-wide archetype patterns shared with the eight sibling episodes already shipped on this branch (see recent commits e3d4514, 261cf43, b407413, 43ac6be). The chapter and framing are upload-ready for NotebookLM under the established archetype.
