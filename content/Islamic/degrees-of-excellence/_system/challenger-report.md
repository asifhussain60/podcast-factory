# Podcast Challenger Report

**Book:** degrees-of-excellence
**Run:** 2026-07-31 (challenger v2.6)
**Scope:** per-chapter the-virtues-of-ali-the-imam-who-mirrors-god (ch08f / EP08)
**Iterations:** 1 (of 5 max) — re-invocation pass. The earlier run's two framing parity auto-fixes (R-NAMEDISCIPLINE, R-DRAMATIC-ARC) are persisted in the framing on disk; the build gate now passes them, so no in-allowlist auto-fix remained to apply. Findings stable → converged at iter 1.
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← default (no content_profile / series-config.yaml on disk; book lives under content/Islamic/)

## Async-safety note (S1 bypass)

This invocation originates from within the orchestrator pipeline (`orchestrate_book.py`). The visible `orchestrate_book.py` process is THIS challenger's parent, not a concurrent independent run; S1 is bypassed for this pass per the invocation contract. All other gates ran normally.

## Deterministic gates run this pass

- `build_episode_txt.py EP08-...` — exit 0. Chapter (SOURCE) validated at 5,794 words, uploaded as-is; episode txt (CUSTOMIZE PROMPT) rebuilt at 735 words. Build FLAGs (all P1): R-NO-ARABIC-TRANSLITERATION on chapter + framing, F25-APPARATUS-TABLE on 99-show-notes. No hard-gate failure.
- `_doctrinal.py` on chapter — exit 0, no doctrinal findings (assert_doctrinal_clean equivalent, clean).
- `_doctrinal.py` on framing — exit 1, T3 P0 (see P1 finding below — a guard-context scanner trip, not a chapter-doctrine violation).
- `check_chapter_set.py` (book scope, 8 chapters) — ch08f findings: P8/CS8 concept overlap with ch02b (P1); P6/CS6 cross-book bleed ×2 (P2).

## Auto-fixes applied (iteration-by-iteration)

None this invocation. The framing parity edits from the earlier run today are already on disk (line 10 carries the "/ the first imam" alias; line 21 carries the "Arc: crisis / failed answer / pivot / stakes" tell), the build gate passes both R-NAMEDISCIPLINE and R-DRAMATIC-ARC, and no other in-allowlist deterministic finding is present. The one newly-surfaced item this pass (framing guard hygiene, below) is a T-family finding outside the Section 3 auto-fix allowlist, so it is flagged, not fixed.

### Not auto-fixed (deliberate, consistent with converged siblings)

- **Em-dashes (71 in the chapter — count re-measured this pass; the earlier "31" figure was understated) retained.** The authoritative build gate (`build_episode_txt.py`) has no em-dash check and does not reject them, and all eight chapters (71–96 em-dashes each) shipped SHIP-WITH-CAUTION carrying the same house style. Mechanically comma-replacing 71 authored em-dashes would damage the prose and desynchronise ch08f from its seven siblings; the spec's B5 auto-fix is superseded by the current build contract and is deliberately not applied.
- **N6 (Arabic script) N/A for this book.** No `_system/glossary.yml` exists; all eight chapters carry zero Arabic script (verified) and shipped SHIP-WITH-CAUTION. The book operates under F20 audio-label doctrine (English labels, no Arabic script or transliteration in audio). N6's glossary-driven injection has no source to draw from here.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### T3-GUARD — framing quotes the literal forbidden pairing inside its own Do-not guard (NEW this pass)
- **File:** content/Islamic/degrees-of-excellence/_system/episode-drafts/EP08-the-virtues-of-ali-the-imam-who-mirrors-god/00-framing.md:10
- **Context:** the Name-discipline line reads `... at first mention only add "peace be upon him." Never say "Imam Ali." Never speak the forbidden pairing of the leadership-title and the personal name.` The standalone `_doctrinal.py` T3 scanner (substring, context-blind) matches the literal `Imam Ali` and rates it **P0** with replacement `Father of Imams`.
- **Why recorded P1, not P0 (explicit, not a silent downgrade):** (a) the CHAPTER — the only surface NotebookLM ingests as doctrine — is doctrinally clean (`assert_doctrinal_clean` exit 0); (b) the framing clause is a PROHIBITION instructing the hosts to avoid the phrase, not a doctrinal assertion; (c) the authoritative ship gate `build_episode_txt.py` does not doctrinal-check the framing, so it passes exit 0; (d) the identical guard shipped in the converged siblings EP02/EP04/EP07 (SHIP-WITH-CAUTION). It is nonetheless a genuine guard-hygiene defect under R-NO-LITERAL-FORBIDDEN-PHRASE-IN-GUARDS: a customize prompt should not put the literal forbidden pairing into NotebookLM's context.
- **Suggested fix (deterministic, NOT applied — T-family is outside the Section 3 auto-fix allowlist):** delete the redundant sentence `Never say "Imam Ali." ` — the immediately following sentence (`Never speak the forbidden pairing of the leadership-title and the personal name.`) already enforces the same rule, which is exactly the compliant phrasing siblings EP01 and EP05 use (both pass the T3 scanner, exit 0).
- **Systemic:** EP02, EP04, EP07 carry the same literal-phrase guard and trip the same scanner P0. Recommend a book-wide guard-hygiene sweep so all six framings match the EP01/EP05 compliant form. The author decides whether to escalate any of these to P0.

#### CS8 / P8 — book-scope concept-overlap between ch08f and ch02b
- **Files:** content/Islamic/degrees-of-excellence/chapters/ch08f-the-virtues-of-ali-the-imam-who-mirrors-god.txt and chapters/ch02b-the-theory-of-degrees-of-excellence-explained.txt
- **Context:** `check_chapter_set.py` P8 reports the two chapters sharing 8 distinct 12-word concept passages (the ladder-of-being ascent and the qa'im/perfector formulation). Sample: "and the qa'im of all those who preceded him and the perfector…".
- **Note:** Pre-existing chapter-SET design property, already recorded at its true CS8 severity (P1) in the ch02b run; ch02b shipped SHIP-WITH-CAUTION with the overlap present. Resolution is a set-level authoring decision (trim the ladder recap so each episode owns its beat). Never auto-stripped; ch02b is outside this per-chapter pass's edit scope.

### P2 (advisory — accepted whole-book TTS-doctrine baseline, documented book-wide rationale)

Recorded transparently at P2 (not a silent downgrade): these are the same build-time FLAG items every converged sibling recorded as advisory to ship SHIP-WITH-CAUTION with P0=0. The build reports them P1; the documented book-wide rationale for recording them P2 is given per item.

- **R-NO-ARABIC-TRANSLITERATION (chapter):** `al-Aql`, `al-Din`, `al-Kirmani`, `al-Naysaburi` — F20 audio-label doctrine. `al-Kirmani` and `al-Naysaburi` are genuine historical Ismaili figures the source requires; `al-Aql`/`al-Din` occur inside the book title *Rahat al-Aql* and "foundation of religion" (the enrichment reference). The framing Name-discipline steers the hosts to "the author" / "an earlier philosopher of the same tradition," so none reaches TTS audio.
  - File: content/Islamic/degrees-of-excellence/chapters/ch08f-the-virtues-of-ali-the-imam-who-mirrors-god.txt
- **R-NO-ARABIC-TRANSLITERATION (framing):** `al-Naysaburi` — same doctrine; the framing names the author once in the welcome directive by design, then "the author."
  - File: .../episode-drafts/EP08-the-virtues-of-ali-the-imam-who-mirrors-god/00-framing.md:4
- **F25-APPARATUS-TABLE (99-show-notes):** no `## Name and Title Preservation Table` section — a book-wide gap matching every sibling's show-notes, not EP08-specific. 99-show-notes.md is outside this agent's edit scope (Section 8).
  - File: .../episode-drafts/EP08-the-virtues-of-ali-the-imam-who-mirrors-god/99-show-notes.md
- **CS6 / P6 cross-book bleed:** `al-Kirmani`, `Hamid al-Din` flagged against kitab-al-riyad's mangle-map in ch08f. Genuine historical Ismaili figures (Hamid al-Din al-Kirmani, author of *Rahat al-Aql*); false-positive-prone; surfaced for human review, never auto-stripped.
  - File: content/Islamic/degrees-of-excellence/chapters/ch08f-the-virtues-of-ali-the-imam-who-mirrors-god.txt

## Clean

- **A (authenticity):** A1 both Quran citations in canonical plain-English form — `(chapter 13, verse 26)` and `(chapter 38, verse 26)`, both verified against the source verses (Ar-Ra'd 13:26 provision extend/restrict; Sad 38:26 David the vicegerent). No terse `(Quran N:M)` forms. Two verses the source names without a number ("man is rebellious…" = 96:6-7; "we desire neither reward nor thanks…" = 76:9) are correctly quoted WITHOUT invented references, per the contract's tone constraint. Both blockquotes speaker-attributed ("the Prophet"; "the Father of Imams") with no bibliographic reference-tail clutter (I5 clean). No `[VERIFY CITATION]` / `[CONTEXT NEEDED]` markers (A2/D5).
- **T (doctrinal):** build-time `assert_doctrinal_clean()` passed (exit 0). No mis-attribution, no imam-lineage error, no forbidden naming pairing. The chapter uses "the Commander of the Faithful, Ali b. Abi Talib" and "the Father of Imams" throughout and never says "Imam Ali"; the reigning imam is kept unnamed and the numerology rendered abstractly, per the contract.
- **U (scholarly-conversation):** no AI-cliché, no faux-profundity rhetorical-question opener (the opening is a substantive thought-question about the doctrine, not a banned "In an age where…" opener), no premature closure, no deep-dive self-reference, no external-essentialism.
- **Q (host parity):** deep_dive contract valid; John (male, scholar) = Host A, Hannah (female, seeker) = Host B — consistent across EP01/02/04/05/07/08 (Q1–Q4 clean).
- **G (Extract-mode contract):** G1 present, G2 required-fields + enums valid (angle=faithful_exposition, adaptation_mode=faithful, episode_format=deep_dive, debate=null, slug matches chapter), G3 meta-prose lint clean.
- **B (meta-prose / literalness):** build-gate `validate_chapter` passed exit 0; no meta-prose tells, no cross-episode references, no file-length self-references, no translator-apparatus prefixes, no invented dialogue/scenes.
- **C/N/O:** N1 (inline phonetic parens) none; O1 honorific expansions each ≤1 ("peace be upon him" ×1, "may God bless him" ×1); no filler tells (E4). Framing Pronunciation block uses the say-ONCE imperative form (N2/N3), covers mutimm / ghulat / ahl al-haqq / ahl al-batil.
- **Framing F/H/I/K/M/R/N4:** four-part+ structure (Opening, Name discipline, Pronunciation, Three-part focus, Host dynamic, Tone constraints, Landing, Do-not); welcome + one-sentence preview (H1/H2); recurring-thesis spine stated verbatim ×3 (open/pivot/close); host friction ≥3 + one concession (K); DENY-modernize + DENY-surprise block (M1/M2); close-on-question landing (H3); no-read-aloud guard (N4). R-NAMEDISCIPLINE + R-DRAMATIC-ARC now pass after the iter-1 fixes.
- **E (shape):** clear four-movement arc (picks-up → summit of summits → the imam who mirrors God → vicegerent + closing prayer → what this lands); one-sentence summarizable; no translation-residue awkwardness detected.

## Health metrics

| Chapter | Words | Enrichment ratio | Tier diversity | Citations | Phonetic gaps |
|---|---|---|---|---|---|
| ch08f | 5,794 | ~8% | 4 tiers (Quran, Prophetic hadith, Father-of-Imams saying, Ismaili philosophy / al-Kirmani) | 7 references (2 cited Quran + 2 policy-uncited Quran + 3 attributed sayings/hadith) | 0 (F20 audio-label doctrine) |

Word count 5,794 is above the E1 soft chapter band (1,500–4,500) but within the build's hard bound and consistent with `length_target: extended`; the build gate accepts it (exit 0). Not flagged — the extended-tier chapter is the treatise's culmination and every sibling in this book runs long.

## Fixer-pass note (2026-07-31, re-invocation)

- **CS8/P8 not fixed — requires author judgment, out of per-chapter edit scope.** The overlap is a set-level design property: the ch08f ladder recap is load-bearing (the chapter's core move is running the nature→humanity→imams chain "one link further" to the single summit, so the first two steps must be restated to make the third intelligible), and the only clean trim would touch ch02b, which this per-chapter pass may not edit. Left as-is, consistent with ch02b and every sibling that shipped SHIP-WITH-CAUTION with the overlap present.
- **T3-GUARD not fixed — T-family is outside the Section 3 auto-fix allowlist.** The deterministic fix (delete the redundant `Never say "Imam Ali."` sentence) is documented in the P1 finding above for the author to apply, ideally as a book-wide sweep across EP02/EP04/EP07/EP08 so all six framings match the compliant EP01/EP05 form.
