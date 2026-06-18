# Podcast Challenger Report

**Book:** vol-01 (al-anwaar-al-lateefah / The Subtle Lights, Volume One)
**Run:** 2026-06-18 (challenger v2.5)
**Scope:** per-chapter — the-word-of-allah-and-the-greatest-name (EP11 / ch11h)
**content_profile:** islamic_scholarly (from book-root work.yml → full 30-check catalog applies)
**Mode:** Extract Mode (chapter-contracts/ populated). episode_format: deep_dive.
**Transcript present:** no (Loop M3/M4, N5, O3, P12/P13, Q5, R6/R7 transcript-empirical checks vacuous)
**Iterations:** 1 (of 5 max) — intelligent break: zero auto-fixes applicable under current doctrine; all remaining findings are P1 flag-only/authoring. A second pass would reproduce identical (P0,P1) counts.
**Verdict:** SHIP-WITH-CAUTION

> S1 (async-safety) bypassed per pipeline context — the visible orchestrate_book.py process is this invocation's own parent, not a concurrent independent run.

## Auto-fixes applied (iteration-by-iteration)

None. No deterministic auto-fix conditions were present:
- B5 (em-dashes): 23 present, but the em-dash rejection rule is OBSOLETE under v2.5 (the build gate accepts em-dashes; the old auto-strip would corrupt current TTS-tolerant prose). Not fixed by design.
- C3/O1 (honorific repeats): "(peace be upon him)" appears exactly once — already clean.
- N1 (inline phonetic parens): none present.
- B2 (cross-episode refs): none in chapter prose.
- E4 (filler exact tells): none.
- H/I/K/M/N4/R framing clauses: all already present in 00-framing.md.

## Findings requiring author resolution

### P0 (blocks ship)

None. The build-time hard gates (doctrinal T1–T5, T3 forbidden phrases, meta-prose, word-count band) all pass. `run_doctrinal_checks` → 0 findings. `build_episode_txt.py` exit 0.

### P1 (ship-with-caution)

#### A1 / TTS-literalness: Quran citations use colon form "Quran 36:82" rather than the contract's own plain-English target
- **File:** chapters/ch11h-the-word-of-allah-and-the-greatest-name.txt:17, :33, :43
- **Context:** `— Quran 36:82 (Surat Ya Sin)`, `— Quran 74:30 (Surat al-Muddaththir)`, `— Quran 35:28 (Surat Fatir)`. The deterministic validator does NOT flag the unparenthesized attribution-line form, so the build passes; but NotebookLM reads "36:82" as an opaque number run. The contract's own tone_constraints (line 46) specifies the plain-English form "(chapter 35, verse 28)".
- **Why flag, not fix:** changing citation text is an authoring decision (Section 3 — never alter citations). Mitigation: the framing's Name discipline already steers hosts to "Cite the Quran by verse content and English chapter meanings."
- **Suggested fix:** in the chapter SOURCE, render references as "(chapter 36, verse 82)" etc., keeping translator + work attribution.

#### R-NO-ARABIC-TRANSLITERATION (F20): 13 Arabic transliterations in the chapter SOURCE
- **File:** chapters/ch11h-...txt — samples: Abu Ya'qub al-Sijistani, al-Qushayri, al-Risala al-Qushayriyya, Nahj al-Balagha, Junayd al-Baghdadi, al-Muddaththir, Fatir, al-Lateefah.
- **Context:** These are almost entirely citation author/work names required by Category A3 (translation provenance) and A1 (citation discipline). This is the known, deliberate tension: the written SOURCE carries them for citation authenticity; F20 wants them out of AUDIO. The framing resolves the audio side ("Never speak Arabic names or book titles; say 'the book'").
- **Suggested fix:** none required at chapter level — citation provenance must remain. The audio-label crosswalk belongs in the F25 apparatus table (see below).

#### R-SURAH-ENGLISH-ONLY (F29): Arabic surah names in parenthetical citation glosses
- **File:** chapters/ch11h-...txt:33, :43 — "(Surat al-Muddaththir)", "(Surat Fatir)".
- **Context:** same citation-authenticity-vs-TTS tension as above. The framing instructs English-chapter-meaning citation in audio.
- **Suggested fix:** optionally drop the parenthetical Arabic surah gloss from the SOURCE (the verse number already identifies the chapter), or keep for written provenance and rely on framing for audio.

#### F25-APPARATUS-TABLE: 99-show-notes.md lacks the "## Name and Title Preservation Table"
- **File:** _system/episode-drafts/EP11-.../99-show-notes.md
- **Context:** SYSTEMIC / archetype-level — the shipped EP10 show-notes has the identical gap. The show-notes template does not emit the apparatus table that should carry the preserved-Arabic ↔ audio-label crosswalk. Per Section 8, 99-show-notes.md is OUT OF SCOPE for challenger edits.
- **Suggested fix:** fix at the show-notes template/generator root (systemic-fixes-from-chapter-archetype), not per-episode.

#### CS10 (chapter density): 6 concept sections (target ≤3)
- **File:** chapters/ch11h-...txt (book-scope check_chapter_set P10)
- **Context:** the-word-of-allah-and-the-greatest-name has 6 concept H2s. ADVISORY at challenger layer. AUTHORING-JUSTIFIED: this is the volume-closing keystone chapter that deliberately gathers the whole cosmology to its close (contract essential_rationale: "the structural keystone that closes the volume"). Re-splitting would break the closing arc.
- **Suggested fix:** accept as the deliberate keystone density, or relabel/re-split via Phase 0d if density_standard:2 halting becomes binding.

### P2 (advisory)

#### R-HONORIFIC-BOTH-BOUNDS (build flag, downgraded to P2-advisory note)
- **File:** _system/episode-drafts/EP11-.../00-framing.md
- **Context:** the validator unconditionally expects exactly one "peace and blessings of Allah" (Prophet honorific). EP11 neither cites nor mentions the Prophet (figures cited: Ali / Father of Imams, Muhammad Taher, Sadiq, Amir al-Din al-Sadiq, Junayd). Zero is CORRECT here — this is a false-positive of an unconditional check, consistent with O1 (honorific expanded at most once; zero when the figure is absent).
- **Suggested fix:** none. No Prophet honorific should be inserted where the Prophet is not invoked.

#### P8 (cross-chapter n-gram duplication — book-scope, NOT EP11-specific)
- **Context:** 15 P8 findings book-wide, dominated by repeated Nahj al-Balagha citation boilerplate ("...the father of imams nahj al balagha compiled by al sharif al radi sermon trans sayyid ali reza..."). The target chapter (the-word-of-allah-and-the-greatest-name) appears in ZERO P8 findings — no significant prose duplication with siblings.
- **Suggested fix:** none required for EP11; the book-wide citation-boilerplate echo is expected apparatus, not re-taught concept.

## Health metrics

| Chapter | Words | Quran cites | Attributed sayings | Translator named | Phonetic gaps | Honorific repeats | Doctrinal findings |
|---|---|---|---|---|---|---|---|
| ch11h | 3,561 | 3 (36:82, 74:30, 35:28) | 2 (Nahj al-Balagha S.193; al-Qushayri/Junayd) | yes (all 5 quotes) | 0 | 0 | 0 |

| Framing | Words | Welcome | Landing-on-question | Host roles | Do-not block | No-read guard |
|---|---|---|---|---|---|---|
| EP11 00-framing.md | 750 (episode txt) | yes | yes | A=scholar / B=seeker (book-wide parity OK) | yes | yes |

- Word-count band: chapter 3,561 within Longer band (2,800–4,500). PASS.
- Category A (authenticity): all PASS — references present, translators named, no fabricated citations, Sufi (Junayd) annotated as parallel tradition.
- Category Q (host-role parity): PASS across all 10 episodes (A=male/scholar, B=female/seeker, no swaps).
- Category T (doctrinal): PASS — "The Father of Imams, Ali ibn Abi Talib (peace be upon him)" is the canonical form; leadership-title NOT paired with personal name.
- Category B/N/O (NotebookLM literalness): PASS — no meta-prose, no inline phonetics, single honorific, no abbreviations.

## Verdict rationale

SHIP-WITH-CAUTION. No P0. Five P1 findings, all either (a) the deliberate citation-authenticity-vs-TTS tension already handled by the framing's audio steering (A1/F20/F29), (b) a systemic archetype-level show-notes-template gap out of challenger scope (F25), or (c) an authoring-justified keystone density (CS10). None blocks upload. The two NotebookLM upload artifacts are present and build-clean:
- SOURCE: chapters/ch11h-the-word-of-allah-and-the-greatest-name.txt (upload as single source)
- CUSTOMIZE PROMPT: episodes/EP11-the-word-of-allah-and-the-greatest-name.txt (paste into Customize box)
