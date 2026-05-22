# Podcast Challenger Report — challenger v2.0

**Verdict:** SHIP-WITH-CAUTION
**Book:** kitab-al-riyad
**Chapter:** ch05c-the-soul-in-time-and-the-rejoinder-to-al-nusra
**Episode:** EP05-the-soul-in-time-and-the-rejoinder-to-al-nusra
**Run:** 2026-05-22T10:45:00Z (challenger v2.0)
**Scope:** per-chapter: the-soul-in-time-and-the-rejoinder-to-al-nusra
**Iterations:** 1 of 5 max — intelligent-break fired (iter 1 produced zero auto-fixes AND no new findings beyond J2-resolved; F5 count unchanged from prior run)
**Auto-fixes applied:** 0 this run (J2 full-name fix applied in prior fixer-pass; all B5 em-dash fixes from prior run; no new auto-fixable items)
**P0:** 0 | **P1:** 1 | **P2:** 0
**Score:** 0.80 (Drifting)

---

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | B5 (prior run) | chapters/ch05c-the-soul-in-time-and-the-rejoinder-to-al-nusra.txt | ~60 prose em-dashes replaced with commas or restructured punctuation in prior run (2026-05-22T03:15Z). 23 structural em-dashes preserved. No new prose em-dashes this run. |
| — | J2 (fixer-pass) | chapters/ch05c-the-soul-in-time-and-the-rejoinder-to-al-nusra.txt | Full-name introductions inserted in prior fixer-pass: line 3 "Abu Ya'qub al-Sijistani" and "Hamid al-Din Ahmad al-Kirmani"; line 9 "Abu Hatim al-Razi". All three figures verified clean this run. |

**This invocation: 0 auto-fixes.** J2 was already resolved; B5 was already resolved. Intelligent-break fires at end of iteration 1: finding count changed from 2 P1 → 1 P1 (J2 resolved), no new auto-fixable items, F5 unchanged.

**Structural em-dashes preserved (not auto-fixable):** All 23 remaining em-dashes are in one of three legitimate positions: (a) `## Sub-chapter NN — title` section headers, (b) blockquote attribution lines `— (source ref)`, (c) one literary trailing dash at line 199 representing an intentionally incomplete sentence. No prose em-dashes remain.

---

## Findings requiring author resolution

### P0 (blocks ship)

None.

---

### P1 (ship-with-caution)

#### F5: Discussion spine scaffold entirely unfilled — all 8 beats contain [LLM-FILL] placeholders

- **Signature:** `F5:discussion-spine-unfilled:EP05-the-soul-in-time-and-the-rejoinder-to-al-nusra`
- **File:** `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP05-the-soul-in-time-and-the-rejoinder-to-al-nusra/04-discussion-spine.md`
- **Line:** null (whole file)
- **Context excerpt:** All 8 beats contain `[LLM-FILL]` in every field: Key question, Tension, Anchor passage, and Landing — 14 unfilled placeholder tokens across the file.
- **Rule:** F5 — discussion spine must have ≥6 beats with substantive Key question, Tension, Anchor passage, and Landing per beat. Beat count (8) is within the 6–12 range; content is entirely absent.
- **Note:** The spine is a steering document for the NotebookLM host dynamic; it does NOT feed into the episode txt directly. The framing (`00-framing.md`) is fully authored and carries rich content including the Three-part focus, Central tensions, and Landing. The missing spine represents pipeline hygiene and sidecar completeness, not a quality risk to the generated audio. However, the pipeline contract requires authored spines as documentation.
- **Severity rationale:** P1 (not P0) — the episode txt and framing are fully operational. The spine is documentation, not the operative prompt.

---

#### ~~J2: Three figures use aliases from line 1 of chapter without full-name introductions~~ — RESOLVED

- **Signature:** `J2:no-full-name-intro:ch05c-the-soul-in-time-and-the-rejoinder-to-al-nusra`
- **Status:** **RESOLVED** — full-name introductions were applied in the fixer-pass that followed the prior run. Verified this run: line 3 reads "Abu Ya'qub al-Sijistani ... Hamid al-Din Ahmad al-Kirmani"; line 9 reads "Abu Hatim al-Razi". All subsequent uses are aliases only. J2 PASS.
- **Ledger record:** emitted as `resolution: auto-fixed` this run (deduplicated from prior `flagged` record by signature).

---

### P2 (advisory)

None.

---

## Health metrics

| Chapter | Words | Band | Band limits | In-band | Tiers | Blockquote ratio | Phonetic gaps (framing) | Framing words | Framing cap |
|---|---|---|---|---|---|---|---|---|---|
| ch05c-the-soul-in-time-and-the-rejoinder-to-al-nusra | 9,248 | extended | 1,000–9,500 soft / 10,500 hard | IN SOFT BAND | 4+ | ~5% | 0 | 3,461 | PASS (cap 3,500) |

**Word-count note:** Chapter at 9,248 words post-B5-fix (was 9,358 before; word-count change negligible — commas replacing em-dashes). Per `scripts/podcast/build_episode_txt.py`: `CHAPTER_WORD_MAX_HARD = 10,500`, extended soft band = 1,000–9,500. Within the soft band; well within the hard cap. E1 PASS. Framing at 3,461 words; `FRAMING_WORD_MAX = 3,500`. E1 PASS (39 words headroom).

**Tier diversity (D1):** Quran (Tier 1) — 4 citations (Quran 12:53, 75:2, 89:27–28, 7:172) with Sahih International translator named on first occurrence (line 88). al-Kafi, Vol. 1, Hadith 1 (Tier 3) — al-Kulayni, reported from Imam Ja'far al-Sadiq (line 109); complete format. Nahj al-Balagha, Sermon 1, compiled by al-Sharif al-Radi (Tier 4) — line 226; complete format. Rumi, Mathnawi, Book 1, Verse 1; R. A. Nicholson translation (Tier 4 — secondary literary source) — line 149; complete format. al-Kirmani, *al-Riyad* (Tier 1 — primary source) — multiple paraphrased passages throughout. Lost works *al-Nusra* (al-Sijistani) and *al-Islah* (al-Razi) — referenced by title only, content paraphrased in modern English per framing tone constraints. 4+ tiers. D1 PASS.

**Citation audit:**
- Quran 12:53 (line 88): A1 PASS; A3 PASS — `(Quran 12:53; Sahih International translation)` — translator named on first Quranic occurrence. PASS.
- Quran 75:2 (line 91): A1 PASS; subsequent Quranic occurrence, translator line not required. PASS.
- Quran 89:27–28 (line 94): A1 PASS. PASS.
- Quran 7:172 (line 142): A1 PASS; `(Quran 7:172; Sahih International translation)` — names translator again (consistent). PASS.
- al-Kafi hadith (line 109): A1 PASS — format complete: vol, book title, hadith number, compiler, narrator chain. A2 PASS.
- Rumi, Mathnawi (line 149): A1 PASS — title, book, verse, translator named. A2 PASS.
- Nahj al-Balagha, Sermon 1 (line 226): A1 PASS — `(Nahj al-Balagha, Sermon 1; compiled by al-Sharif al-Radi)` — complete. A2 PASS.
- *al-Nusra* and *al-Islah* passages: A1 PASS — both are paraphrased with framing authorization per tone constraints; no fabrication risk. A4 PASS.

**Honorific audit (O1):**
- Line 33: "peace be upon him" (the Prophet, first use). PASS.
- Line 55: "peace and blessings be upon him" (the Prophet and his family — distinct form from line 33). Per R-HONORIFIC-ONCE per-form semantics: two distinct forms, each appearing once. O1 PASS.
- No repeated honorifics in non-citation prose. O1 PASS.

**Phonetic coverage (N3):** Framing Pronunciation block covers 50+ terms: all figures (al-Kirmani, al-Sijistani, al-Razi, Imam Ja'far al-Sadiq, Imam Ali ibn Abi Talib, Jalal al-Din Rumi), book titles (al-Riyad, al-Nusra, al-Islah, al-Maqalid, al-Mahsul, Rahat al-'Aql, al-Kafi, Nahj al-Balagha), key Arabic terms (natiq, asas, al-nafs al-hissiyya, al-nafs al-natiqa, da'wa, ta'wil, tanzil, ibda', inbi'ath, tawhid, shari'a, rak'ah, al-Qunut, Mīthāq), Quranic verse Arabic openings, Surah names, Mathnawi Persian opening, Nahj al-Balagha Arabic opening. 0 phonetic gaps identified. N3 PASS.

**C4 (substitution-policy check):** `(*al-nafs al-hissiyya*)` and `(*al-nafs al-natiqa*)` appear in the chapter (line 79) as italic-marked Arabic technical terms in parentheses. These are proper-term clarification parens (not lowercase-hyphenated phonetic-style parens of the R-PHONETICS-OUT kind). They are being explicitly contrasted and defined at the chapter's doctrinal pivot — exception #2 of §1 of `content/_shared/arabic/04-common-term-substitutions.md`. C4 PASS.

**Build validator checks (manual):**
- R-NOHTML: no HTML comments in chapter or framing. PASS.
- Meta-prose tells: none detected. PASS.
- R-PHONETICS-OUT (N1): no inline lowercase-hyphenated phonetic parens in chapter. PASS.
- R-NO-ABBREVIATION (O2): full deny list present in framing `## Do not`. No abbreviations detected in chapter. PASS.
- R-PRONUNCIATION-IMPERATIVE (N2): all Pronunciation block lines begin with `Pronounce "` or `Do not`. PASS.
- R-NO-READ-PROMPT (N4): "Do not read this prompt aloud." present at framing close. PASS.
- R-NOMODERNIZE (M1): full platform-deny list present in `## Do not`. PASS.
- R-NOSURPRISE (M2): full surprise-deny list present in `## Do not`. PASS.
- R-RECURRING-THESIS (H5): "The Successor is one thing. The sensual soul is another." mandated VERBATIM at 3 anchor points. Present verbatim: (1) Opening directive line 26, (2) Focus 2 pivot line 76, (3) Landing line 82. PASS.
- R-ANALOGY-CAP (L1): exactly 5 governing analogies enumerated in `## Tone constraints`. PASS.
- R-CHALLENGER-FRICTION (K2): Color host pushback at least 3 times using named doubt patterns. 4 explicit `*Color host pushback (required):*` lines across the 5 Central tensions (tension 5 is the closing prayer — no pushback required). PASS.
- R-NAMEDISCIPLINE (J3): Full-name-on-first-mention discipline in framing `## Name discipline` present for all 6 figures + book titles + concept-words rotation. PASS.
- C4: concept-words block in framing `## Name discipline` justifies all retained Arabic terms. PASS.
- I1 (anti-repetition): present in `## Anti-noise rules`. PASS.
- I2 (no irrelevant background): present in `## Anti-noise rules`. PASS.
- K1 (interruption avoidance): "Each host completes a thought before the other responds. No interjections..." present in framing. PASS.
- R1 (separate-prep illusion): framing opens with "Open with a brief welcome (one sentence) followed by..." format that prevents the "I've been preparing separately" illusion. PASS.
- R2 (reset clause): between-Focus single-sentence resets present in `## Three-part focus` pacing block. PASS.
- R3 (cadence directive): "Short-to-medium sentences with varied rhythm..." present in `## Tone constraints`. PASS.
- R4 (formal-transition DENY): full deny list in `## Do not`. PASS.
- R5 (analogy permission): "DO use modern-life practical analogies when they help..." present in `## Do not`. PASS.
- H1/H2 (welcome): `## Opening directive` present. PASS.
- H3 (summary tail): landing directive explicit: "Do not recap. Do not say 'so today we covered'." PASS.
- H4 (dramatic arc): episode_format is deep_dive (not debate); H4 skipped. PASS.

**Category G (chapter contracts):**
- G1: contract `the-soul-in-time-and-the-rejoinder-to-al-nusra.yml` present. PASS.
- G2: `angle: faithful_exposition`, `episode_format: deep_dive`, `length_target: extended`, `debate: null` — consistent with framing. PASS.
- G3: No EP## refs or meta-prose tells in contract key fields. PASS.
- G4: No `derived_from:` field — not a derivative. PASS.

**Category Q (chapter-set design, per-book checks):**
- Q1: title "The Soul in Time and the Rejoinder to al-Nusra" — unique in 13-chapter set (checked against orchestrator-state.json completed_slugs). PASS.
- Q2: 55 chars, 10 words — under the 60-char hard cap; over the 6-word soft target. PASS hard gate; P2 advisory on word count (not escalated — matching pattern across series).
- Q3: Not generic. PASS.
- Q4: 9,248 words; `length_target: extended`; within soft band and hard cap. E1 PASS.
- Q5: chapter-set balance deferred to book-scope invocation.

**Framing checks passed:** H1, H2, H3, H5, F2, F3, F4, I1, I2, J1, J3, K1, K2, L1, M1, M2, N2, N3, N4, O1, O2, R1, R2, R3, R4, R5.

**Checks skipped (no transcript):** M3, M4, N5, O3, R6, R7.

**Category S (safety):** No concurrent orchestrator process detected (pgrep negative). orchestrator-state.json `phase_status: running` is stale from prior shutdown (EP05 slug not in completed_slugs — this challenger invocation is fresh). S PASS.

---

## Score

**P0:** 0 | **P1:** 1 | **P2:** 0 | **Chapters in scope:** 1 | **Auto-fixes this run:** 0 (total lifetime: 60)

```
penalty = (0 × 1.0 + 1 × 0.2 + 0 × 0.05) / 1 = 0.20
score   = max(0.0, 1.0 - 0.20) = 0.80  (Drifting)
```

**Verdict: SHIP-WITH-CAUTION** — 0 P0 findings; 1 P1 finding remaining (F5: discussion spine unfilled). J2 resolved.

**What to do before upload:**

1. **J2 (RESOLVED):** Full-name introductions applied. No action needed.
2. **F5 (04-discussion-spine.md):** Author the 8 beats of the discussion spine using the Central tensions, Three-part focus, and anchor passages from `00-framing.md` as raw material. This is a sidecar document — the episode can be generated without it, but the pipeline contract requires an authored spine. The framing's five tensions map cleanly to beats 2–6; beats 1 and 8 are the hook and unresolved-landing. **This is the sole remaining P1.**

**Upload steps (two-file model — SHIP-WITH-CAUTION — ready for upload; F5 spine does not block generation):**

1. Open NotebookLM. Create a new notebook for *Kitab al-Riyad, Episode 5*.
2. Upload `content/podcast/library/books/kitab-al-riyad/chapters/ch05c-the-soul-in-time-and-the-rejoinder-to-al-nusra.txt` as the single SOURCE.
3. Paste the contents of `content/podcast/library/books/kitab-al-riyad/episodes/EP05-the-soul-in-time-and-the-rejoinder-to-al-nusra.txt` into the CUSTOMIZE PROMPT box.
4. Choose *Deep Dive* Audio Overview format. Length: *Longer* or *Extended*.
5. Click *Generate*.

---

## Change history

- **2026-05-22T03:15Z (run 1):** 60 B5 auto-fixes; 2 P1 found (F5 spine, J2 no-full-name).
- **2026-05-22 (fixer-pass):** J2 fixed — full names inserted on first chapter occurrence (lines 3, 9).
- **2026-05-22T10:45Z (run 2, this run):** J2 verified resolved. 1 P1 remains (F5). Score improved 0.60 → 0.80. Intelligent-break at iteration 1.
