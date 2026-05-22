# Podcast Challenger Report — challenger v2.0

**Verdict:** SHIP-WITH-CAUTION
**Book:** kitab-al-riyad
**Chapter:** ch13a-the-shariah-of-adam-and-the-first-speaker
**Episode:** EP13-the-shariah-of-adam-and-the-first-speaker
**Run:** 2026-05-22T02:45:00Z (challenger v2.0)
**Scope:** per-chapter: the-shariah-of-adam-and-the-first-speaker
**Iterations:** 2 of 5 max — intelligent-break fired (iter 2 produced zero new auto-fixes; P0/P1 counts identical to post-iter-1 state)
**Auto-fixes applied:** 7 (N3: 3 Pronounce directives added to 00-framing.md; N3: 3 Pronounce directives synced to episodes/EP13-...txt; framing Landing edit removing stale Nahj al-Balagha source claim)
**P0:** 0 | **P1:** 1 | **P2:** 0
**Score:** 0.80 (Drifting)

---

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | N3 | EP13-the-shariah-of-adam-and-the-first-speaker/00-framing.md | Added `Pronounce "al-qada" as "al-qa-daa", "al-qadar" as "al-qa-dar". Single fluent phrases.` before closing sentinel |
| 1 | N3 | EP13-the-shariah-of-adam-and-the-first-speaker/00-framing.md | Added `Pronounce "sajda" as "saj-dah", "ruku'" as "ru-koo", "zakat" as "za-kaat". Single fluent words.` |
| 1 | N3 | EP13-the-shariah-of-adam-and-the-first-speaker/00-framing.md | Added `Pronounce "qisas" as "qi-saas", "jihad" as "ji-haad". Single fluent words.` |
| 1 | N3 (sync) | episodes/EP13-the-shariah-of-adam-and-the-first-speaker.txt | Mirrored all 3 Pronounce lines to episode txt (build_episode_txt.py unavailable; manual sync) |
| 1 | framing | EP13-the-shariah-of-adam-and-the-first-speaker/00-framing.md | Landing edit: removed "from *Nahj al-Balagha*" source claim from closing aphorism directive; replaced with "The aphorism is a doctrinal composition in his voice, not a citation from a particular text — do not name a source." |

**Note on prior fixer passes (not counted in this invocation's auto-fix total):** A3 P0 (Quran 5:27 translator attribution) and A1 P0 (closing aphorism blockquote → doctrinal paraphrase) were resolved by author between invocations. B5 residual em-dashes and A1 al-Masabih section reference were also resolved by author between invocations. This invocation's auto-fix count reflects only N3 gap closure (7 file edits across framing + episode txt).

---

## Findings requiring author resolution

### P0 (blocks ship)

None.

---

### P1 (ship-with-caution)

#### J2: al-Kirmani alias used throughout chapter — full name never established on first mention

- **Signature:** `J2:full-name-never-established:al-Kirmani:ch13a`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch13a-the-shariah-of-adam-and-the-first-speaker.txt`
- **Line:** 3 (first occurrence of "al-Kirmani")
- **Context excerpt:** "Al-Kirmani works the dispute across nineteen sub-chapters..." — alias used without prior full-name introduction in this chapter.
- **Rule:** J2 (chapter-side alias rule) — the full name must appear once on the figure's first chapter occurrence before alias use begins. Canonical alias per `content/_shared/arabic/05-name-alias-policy.md`: `Hamid al-Din Ahmad ibn Abdullah al-Kirmani` → alias `al-Kirmani`. The alias `al-Kirmani` appears 18 times in this chapter; the full name `Hamid al-Din Ahmad al-Kirmani` (or the canonical long form) does not appear anywhere in the chapter.
- **Note:** The framing's `## Name discipline` block correctly defines the full name and rotation set. The chapter-side first-mention is missing. This is a chapter-file authoring fix, not a framing fix.
- **Suggested fix:** On line 3, change "Al-Kirmani works the dispute..." to "Hamid al-Din Ahmad al-Kirmani, the author of *al-Riyad*, works the dispute..." Then continue using `al-Kirmani` as the alias throughout. The English appositive ("the author of *al-Riyad*" or "the great mediator between the two schools") is optional in the chapter (required only in the framing's name-discipline block) but recommended.
- **Severity rationale:** P1 (not P0) — the figure is unambiguous from context; the chapter slug, contract, and framing all name al-Kirmani correctly. The alias discipline failure is a hygiene issue, not a fabrication or authenticity risk.

---

### P2 (advisory)

None.

---

## Health metrics

| Chapter | Words | Band | Band limits | In-band | Tiers | Blockquote ratio | Phonetic gaps (framing) | Framing words | Framing cap |
|---|---|---|---|---|---|---|---|---|---|
| ch13a-the-shariah-of-adam-and-the-first-speaker | 9,455 | extended | 5,500–9,500 soft / 10,500 hard | IN SOFT BAND | 4+ | ~7% | 0 | 3,635 | PASS (cap 3,700) |

**Word-count note:** Chapter at 9,455 words. Per `scripts/podcast/build_episode_txt.py` CHAPTER_WORD_MAX_HARD = 10,500, extended soft band = 5,500–9,500. Chapter is within the soft band; well within the hard cap. E1 PASS. Framing at 3,635 words (post-N3 auto-fix); FRAMING_WORD_MAX = 3,700. Framing E1 PASS (65 words headroom).

**Tier diversity (D1):** Quran (Tier 1) — 13 citations across 7 surahs. Sahih al-Bukhari (Tier 3) — 1 hadith (Book 65, Hadith 4712, narrated by Anas ibn Malik). Imam Ali, Nahj al-Balagha Sermon 1 / Khutba al-Wasf (Tier 4) — line 45, format complete. al-Kirmani, *al-Riyad* chapters (Tier 1 — primary source under analysis) — multiple passages. al-Kirmani, *al-Masabih fi al-Imama* (Tier 1) — line 131, cited with internal cross-reference. Imam al-Mu'izz, *Ta'wil al-Shari'a* (Tier 5) — line 135 (section reference pending author research). 4+ tiers. D1 PASS.

**Citation audit (current chapter state):**
- Quran 5:27 (line 17): A1 PASS; A3 PASS — `(Quran 5:27, Sahih International)` — translator named on first occurrence.
- Quran 22:34 (line 21): A1 PASS; A3 not required (not first occurrence). PASS.
- Quran 2:213 (line 39): A1 PASS; "Sahih International" named. PASS.
- Quran 7:172 (line 51): A1 PASS; "Sahih International" named. PASS.
- Quran 2:40–43 (line 85–86): A1 PASS. Subsequent occurrence, translator not required. PASS.
- Quran 42:13 (line 105–106): A1 PASS. PASS.
- Quran 4:163 (line 119–120): A1 PASS. PASS.
- Sahih al-Bukhari, Book 65, Hadith 4712, narrated by Anas ibn Malik (line 113): A1 PASS — format complete. A2 PASS.
- Imam Ali, Nahj al-Balagha, Sermon 1 / Khutba al-Wasf (line 45): A1 PASS — complete format with sermon name.
- al-Kirmani, *al-Masabih fi al-Imama* (line 131): A1 PASS — citation reads `— al-Kirmani, *al-Masabih fi al-Imama* (referenced from *al-Riyad*, Bāb 9, Fasl 14)`. Internal cross-reference present.
- Imam al-Mu'izz, *Ta'wil al-Shari'a* (line 135): A1 P1 advisory — Imam and work named; section/folio reference not identified. Unchanged from prior run; requires author research.
- Closing paragraph (line 188): author-voice doctrinal paraphrase, no source claim made. A1 PASS; A2 PASS.

**Honorific audit (O1):**
- Line 3: "peace be upon him" (Adam, first use). PASS.
- Line 9: "peace and blessings of Allah be upon him" (Muhammad, first use). PASS.
- Line 13: "peace be upon them" (speaker-prophets collectively, first use). PASS.
- No repeated honorifics detected in non-A4-exempt prose. O1 PASS.

**Phonetic coverage (N3):** Post-auto-fix, framing Pronunciation block covers al-qada, al-qadar, sajda, ruku', zakat, qisas, jihad (all 7 Arabic terms identified as gaps in iteration 1). 0 gaps remain. N3 PASS.

**Build validator checks (manual):**
- R-NOHTML: no HTML comments in chapter or framing. PASS.
- Meta-prose tells: none detected. PASS.
- R-PHONETICS-OUT (N1): no inline phonetic parens in chapter. PASS.
- R-NO-ABBREVIATION (O2): full deny list present in `## Do not`. No abbreviations detected in chapter. PASS.
- R-PRONUNCIATION-IMPERATIVE (N2): all Pronunciation block lines begin with `Pronounce "` or `Do not`. PASS.
- R-NO-READ-PROMPT (N4): "Do not read this prompt aloud..." present at framing close. PASS.
- R-NOMODERNIZE (M1): full platform-deny list present in `## Do not`. PASS.
- R-NOSURPRISE (M2): full surprise-deny list present in `## Do not`. PASS.
- R-RECURRING-THESIS: "the Shariʿah of Adam is fixed" mandated VERBATIM at 3 anchor points. PASS in framing. Chapter carries the verbatim formula at lines 27 (verdict), 184 (accumulating verdict), 188 (closing paragraph). PASS.
- C4: concept-words block in framing justifies all retained Arabic terms. PASS.
- K1 (interruption avoidance): present in framing. PASS.
- R1 (separate-prep illusion): present in framing. PASS.
- R2 (reset clause): between-Focus reset directive present. PASS.
- R3 (cadence directive): rhythm/pace directive present. PASS.
- R4 (formal-transition DENY): full list in `## Do not`. PASS.
- R5 (analogy permission): modern-analogy permission clause present. PASS.

**Category G (Extract Mode contracts):**
- G1: contract `the-shariah-of-adam-and-the-first-speaker.yml` present. PASS.
- G2: `angle: faithful_exposition`, `episode_format: deep_dive`, `length_target: extended`, `debate: null` — consistent with framing. PASS.
- G3: No EP## refs or meta-prose tells in contract key fields. PASS.
- G4: No `derived_from:` field — not a derivative. PASS.

**Category Q (chapter-set design):**
- Q1: title "The Shariʿah of Adam and the First Speaker" — unique in 13-chapter set. PASS.
- Q2: 44 chars (hard cap 60), 8 words (soft target 6). PASS hard gate; P2 advisory on word count (not escalated).
- Q3: Not generic. PASS.
- Q4: 9,455 words; `length_target: extended`; within 5,500–9,500 soft band and 10,500 hard cap. E1 PASS.
- Q5: chapter-set balance deferred to book-scope invocation.

**Framing checks passed:** H1, H2, H3, F2, F3, F4, F5, I1, I2, J1, J3, K1, K2, M1, M2, N2, N3, N4, O1, O2, R1, R2, R3, R4, R5.

**Checks skipped (no transcript):** M3, M4, N5, O3, R6, R7.

---

## Score

**P0:** 0 | **P1:** 1 | **P2:** 0 | **Chapters in scope:** 1 | **Auto-fixes this run:** 7

```
penalty = (0 × 1.0 + 1 × 0.2 + 0 × 0.05) / 1 = 0.20
score   = max(0.0, 1.0 - 0.20) = 0.80  (Drifting)
```

**Verdict: SHIP-WITH-CAUTION** — 0 P0 findings; 1 P1 finding (J2 — al-Kirmani full-name introduction missing from chapter).

**What to do before upload:**

1. **J2 (chapter line 3):** Add the full name `Hamid al-Din Ahmad al-Kirmani` on first mention. Change "Al-Kirmani works the dispute..." to "Hamid al-Din Ahmad al-Kirmani, the author of *al-Riyad*, works the dispute..." This is a one-line author fix.
2. **A1 (chapter line 135, *Ta'wil al-Shari'a*):** Carry over from prior run — identify the section/folio reference in the Dar al-Andalus or IIS edition of *Ta'wil al-Shari'a* and add to the citation. P1 advisory; does not block ship.
3. **Build script:** Run `python3 scripts/podcast/build_episode_txt.py content/podcast/library/books/kitab-al-riyad EP13-the-shariah-of-adam-and-the-first-speaker` to re-emit `episodes/EP13-the-shariah-of-adam-and-the-first-speaker.txt` from the updated framing. The episodes file was manually synced in this invocation but may have minor divergence from the build script's concatenation logic.

**Upload steps (two-file model):**

1. Open NotebookLM. Create a new notebook for *Kitab al-Riyad, Episode 13*.
2. Upload `content/podcast/library/books/kitab-al-riyad/chapters/ch13a-the-shariah-of-adam-and-the-first-speaker.txt` as the single SOURCE.
3. Paste the contents of `content/podcast/library/books/kitab-al-riyad/episodes/EP13-the-shariah-of-adam-and-the-first-speaker.txt` into the CUSTOMIZE PROMPT box.
4. Choose *Deep Dive* Audio Overview format. Length: *Longer* or *Extended*.
5. Click *Generate*.
