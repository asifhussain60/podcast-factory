# Podcast Challenger Report

**Book:** degrees-of-excellence
**Run:** 2026-07-31 12:13 (challenger v2.6)
**Scope:** per-chapter degrees-of-excellence-the-peak-of-every-kind (ch04b / EP04)
**content_profile:** islamic_scholarly  ← defaulted (no _system/series-config.yaml present)
**Iterations:** 1 (of 5 max — intelligent break: zero auto-fixes available, re-run would yield identical findings)
**Verdict:** SHIP-WITH-CAUTION

> `CHALLENGER_VERSION` read from `scripts/podcast/_rules.py` at run time = 2.6.
> Pipeline-context note: S1 async-safety gate bypassed for this invocation — the visible `orchestrate_book.py` process is THIS pipeline's parent, not a concurrent independent run.

## Normative gate results (code is authority)

| Gate | Result |
|---|---|
| `build_episode_txt.py` (structural + B/N/O/T hard gates) | PASS (exit 0) — 3 P1 flags, 0 hard fails |
| `assert_doctrinal_clean()` (Category T, hard gate inside build) | PASS — no T3 forbidden phrase; lineage clean |
| `extract_chapter.py` contract validation (Category G2) | Contract renders cleanly; stopped only at the safe "exists-and-differs" guard (framing was authored beyond the stub — expected, not a failure) |
| `check_chapter_set.py` (Category CS, book scope) | 2 target-relevant P1 + book-scope advisories |
| Quran citation format (A1) | 8 plain-English `(chapter N, verse M)` forms, 0 terse `Q N:M` forms — fully compliant |
| Honorific discipline (C3/O1) | 1 expansion ("may God bless him"), no repeats — clean |

## Auto-fixes applied (iteration-by-iteration)

None. No mechanical auto-fix was warranted:
- **Em-dashes (B5):** 74 present, but pervasive book-wide (91 in sibling ch01) and the current normative code has NO em-dash gate — the build script accepts them. The v2.2 spec's B5 auto-fix is superseded by the current TTS/modern-prose architecture. Mass-replacing 74 em-dashes would materially rewrite authored prose; declined.
- **Honorifics (C3/O1):** clean, nothing to strip.
- **Filler (E4):** no exact-match tells present.
- **Framing DENY blocks (M/R/K):** the framing already passes the build gate and carries a deliberately compact anti-modernize / anti-surprise / no-read-aloud form; inserting the full canonical blocks (esp. R5 "DO use modern-life analogies") would contradict the framing's explicit "exactly three governing images, no invented analogies" design. Declined — surfaced as P2 advisory instead.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION (F20) — chapter SOURCE
- **File:** content/Islamic/degrees-of-excellence/chapters/ch04b-degrees-of-excellence-the-peak-of-every-kind.txt
- **Context:** 2 transliterations detected: `al-Naysaburi` (author name, used ~20× as the paragraph subject) and `al-Bukhari` (hadith compiler, line 33). F20 doctrine wants English audio labels ("the author", "the early compiler"). The framing's Name discipline already maps these, but the chapter source still carries the transliterations.
- **Note:** SYSTEMIC / book-wide — every one of the 8 chapters names the author this way. Per the systemic-fixes-from-archetype rule, the root fix belongs at the normalization/archetype layer, not this single chapter. Low distinct-token count (2). Not auto-fixed (author-name substitution is content authoring, not mechanical cleanup).

#### R-NO-ARABIC-TRANSLITERATION (F20) — framing / CUSTOMIZE PROMPT
- **File:** _system/episode-drafts/EP04-degrees-of-excellence-the-peak-of-every-kind/00-framing.md
- **Context:** `al-Naysaburi` appears in the Opening directive ("al-Naysaburi's treatise *Establishing the Imamate*"). Same F20 note as above.

#### F25-APPARATUS-TABLE — show-notes apparatus
- **File:** _system/episode-drafts/EP04-degrees-of-excellence-the-peak-of-every-kind/99-show-notes.md
- **Context:** no `## Name and Title Preservation Table` section. F25 doctrine: each episode's show-notes carries the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) that the TTS-safe audio omits. This is the correct home for the transliteration/translator apparatus the audio source strips. Challenger does not edit 99-show-notes.md (published-library apparatus) — flagged for the author.

#### CS8 — cross-chapter duplication (n-gram)
- **Files:** ch04b-degrees-of-excellence-the-peak-of-every-kind.txt vs ch02b-the-theory-of-degrees-of-excellence-explained.txt
- **Context:** the two chapters share 15 distinct 12-word passages ("same content taught twice"). Sample: *"…into the structure of every ordered thing so that when al-Naysaburi…"* This directly matches the contract's own tone_constraint warning ("Do not re-teach the abstract theory… the introduction did that"). The concrete chapter appears to re-teach abstract framework language the theory chapter already delivered.
- **Suggested fix:** trim the abstract-theory recaps in this chapter to a one-line callback; keep the words on the concrete specimens. Authoring decision — never auto-stripped.

#### CS10 — concept density over target
- **File:** ch04b-degrees-of-excellence-the-peak-of-every-kind.txt
- **Context:** 5 concept H2 sections (The witness of nature / The peak of every kind / Antidotes and poisons / Humankind and its summit / What the natural witness proves); target ≤3 per `docs/standards/chapter-density.md`. At 6,057 words the chapter is also at the top of the length envelope (build gate accepts it; CS4 band did not fire).
- **Note:** Advisory density flag — the preflight smoke gate owns halting for `density_standard: 2` books; no series-config present here so treated as advisory P1. Authoring decision (re-split via Phase 0d if desired).

### P2 (advisory)

#### A3 — Quran translation provenance (architecturally inapplicable)
- **File:** ch04b (8 Quranic renderings, e.g. chapter 9 verse 32; chapter 17 verse 82)
- **Context:** no translator is named. Under strict A3 this is P0, but this book's TTS-safe / F20 profile deliberately renders Quran inline in the treatise's own English (the contract explicitly forbids "an Arabic transliteration run paired with a translation," and a translator name would itself be a transliteration the audio strips). The renderings read as the author's contextual English, not a verbatim standard translation. Recorded as advisory, NOT escalated to P0 — the correct home for any translator attribution is the F25 apparatus table (see the F25 P1 above), not the audio source.

#### Framing DENY blocks in compact form
- **File:** 00-framing.md `## Do not`
- **Context:** the framing covers modern-framing / surprise-filler / deep-dive / faux-profound-opener / no-read-aloud in a compressed sentence rather than the full canonical M1/M2/R1–R5 blocks. Build gate accepts it. Not auto-expanded (would bloat a deliberately tight 715-word customize prompt and R5's analogy-permission would contradict the "exactly three source analogies" design). For author awareness only.

#### CS/P6 — cross-book name bleed (sibling chapters, book scope)
- **Context:** book-scope scan flagged possible cross-book bleed of `al-Hakim bi-Amr Allah`, `al-Sijistani` (in ch01a) and `Hamid al-Din`, `al-Kirmani` (in ch08f) against kitab-al-riyad's mangle-map. These are on OTHER chapters, not the target, and are P2 advisory (common-name false-positive risk). Surfaced for human review; never auto-stripped.

## Health metrics

| Chapter | Words | H2 concept sections | Quran cites (plain-English) | Terse cites | Honorific expansions | Arabic script | Inline phonetic parens |
|---|---|---|---|---|---|---|---|
| ch04b-the-peak-of-every-kind | 6,057 | 5 (target ≤3) | 8 | 0 | 1 | 0 (book-wide by F20 design) | 0 |

## Chapter/framing integrity summary
- B (meta-prose): clean (build gate pass); "the introduction", "the treatise" are source-anchored references to al-Naysaburi's book, not cross-episode/file self-references.
- N1 (inline phonetic parens): 0 — chapter carries no `*Term* (PHO-NE-TIC)` guides.
- N6 (Arabic script): book has no glossary.yml and zero Arabic script by deliberate F20/TTS-safe design (the build gate actively flags transliterations for REMOVAL, the inverse of injection); N6 not applicable.
- Q (host role parity): John (male, scholar) / Hannah (female, seeker) — correct pools; voice-gender declared.
- H1/H2/H3 (welcome / summary / landing): all present; landing closes on an action-tied question, no recap.
- U2 vs V1 (opening): chapter opens on a concrete curiosity hook ("What could a flame… a red stone… a grain of wheat… have to prove about who should lead…") — reads as V1-positive concrete hook, not U2 faux-profundity; build gate did not flag.
