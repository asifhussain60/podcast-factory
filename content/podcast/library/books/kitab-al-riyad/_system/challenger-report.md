# Podcast Challenger Report — challenger v2.0

**Verdict:** SHIP-WITH-CAUTION
**Book:** kitab-al-riyad
**Chapter:** ch11-the-sections-of-the-world
**Episode:** EP11-the-sections-of-the-world
**Run:** 2026-05-22T01:30:00Z (challenger v2.0)
**Scope:** per-chapter: the-sections-of-the-world
**Iterations:** 2 of 5 max — intelligent-break fired (iter 2 produced no new auto-fixes; finding counts stable after iter 1 auto-fixes)
**Auto-fixes applied:** 2 (N3: Sahih Muslim Pronounce line added to framing; J2: Commander of Believers alias corrected to Commander of the Faithful in chapter)
**P0:** 0 | **P1:** 3 | **P2:** 0
**Score:** 0.40 (Unstable)

---

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | J2 | ch11-the-sections-of-the-world.txt:49 | Replaced "Commander of the Believers" with "Commander of the Faithful" to match canonical alias policy |
| 1 | N3 | EP11-the-sections-of-the-world/00-framing.md | Added `Pronounce "Sahih Muslim" as "sa-heeh mus-lim". Say it as two fluent words.` after existing Sahih al-Bukhari line |

**Note on prior-run findings resolved:**
- Prior run P0 A2 (`A2:wrong-collection:souls-conscripted-soldiers:ch11`) is **RESOLVED** — chapter line 87 now correctly reads `(Sahih Muslim, Book 45, Hadith 6376; narrated by Aisha)`.
- Prior run P1 C4 (`C4:substitution-policy-undocumented`) is **RESOLVED** — framing Pronunciation block contains explicit justification paragraph naming all retained Arabic technical terms.
- Prior run P1 N3 five terms (`jami'`, `uluhiyya`, `du'at`, `hadd`, `mukasir`) — **RESOLVED** in prior run. This run added one additional N3 entry: `Sahih Muslim` (triggered by the corrected A2 citation at line 87 now referencing Sahih Muslim where the prior framing only covered Sahih al-Bukhari). Auto-fixed iter 1.
- Prior run P2 J2 (`J2:alias-variant:commander-of-the-believers:ch11`) — **auto-fixed this run** (iter 1).

---

## Findings requiring author resolution

### P0 (blocks ship)

None. P0 clean.

---

### P1 (ship-with-caution)

#### A1: Imam Ali quote cites Diwan al-Imam Ali — not in Tier 4 enrichment whitelist

- **Signature:** `A1:non-whitelist-source:Diwan-al-Imam-Ali:ch11-the-sections-of-the-world`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch11-the-sections-of-the-world.txt`
- **Line:** 47
- **Context excerpt:** `— Imam Ali ibn Abi Talib (peace be upon him), traditionally attributed, collected in *Diwan al-Imam Ali*`
- **Rule:** A1 (Citation discipline) — every Imam Ali saying must cite `(Nahj al-Balagha, Sermon/Letter/Aphorism N)` or `(Ghurar al-Hikam, N)`. The `enrichment-sources.md` Tier 4 whitelist names only those two collections for Imam Ali attributed sayings.
- **Detail:** The verse "Your remedy is within you, but you do not perceive it..." is traditionally attributed to Imam Ali in the Ismaili and Sufi literary tradition as collected poetry (the Diwan), which is NOT in the Tier 4 whitelist. The contract's `anchor_passages` and `references` explicitly acknowledge this source as a deliberate choice. The "traditionally attributed" framing is honest. Authenticity is widely accepted in the tradition but the Diwan itself is a secondary compiled corpus.
- **Agent note:** Agent recommends escalation to P0 if the author cannot identify a specific authenticated edition with volume/page reference. Alternatively, citing a Sufi secondary source that quotes it with chain (Tier 6) would be whitelist-compliant.
- **Flagged at P1** — contract and framing both explicitly acknowledge the source as deliberate.

#### E1: Framing word count marginally over Extended-tier cap

- **Signature:** `E1:framing-marginal-over-cap:EP11:3508`
- **File:** `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP11-the-sections-of-the-world/00-framing.md`
- **Rule:** E1 (Word-count band) — framing max 3,500 words (Extended tier; contract `length_target: extended`).
- **Detail:** Framing measured at 3,508 words (8 words over the 3,500 Extended-tier cap). The N3 auto-fix applied this run (adding the `Pronounce "Sahih Muslim"` line, ~12 words) pushed the framing from 3,496 words (under cap) to 3,508 words (over cap). This is a known trade-off: N3 compliance required the addition; E1 is the marginal consequence. The overage is 8 words.
- **Suggested fix:** Trim 8–10 words from any prose section of the framing. The Sahih Muslim Pronounce line cannot be removed (N3 compliance). Candidates: one of the detailed pushback lines in `## Central tensions to reach` can lose a redundant clause; or shorten a rotation-alias entry. Minor edit requiring author judgment.

#### F5: Discussion spine has 14 unfilled [LLM-FILL] stubs

- **Signature:** `F5:discussion-spine-unfilled:EP11-the-sections-of-the-world`
- **File:** `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP11-the-sections-of-the-world/04-discussion-spine.md`
- **Context:** All 8 beats in the discussion spine contain `[LLM-FILL]` placeholders. No beat has been authored. The header declares "8 beats" but the content is entirely template scaffolding.
- **Rule:** F5 — `04-discussion-spine.md` scaffold present and well-shaped (6–12 beats).
- **Detail:** The discussion spine does NOT flow to NotebookLM (the `build_episode_txt.py` emits from `00-framing.md` only). The framing's `## Three-part focus — the six-beat dramatic arc` section is fully authored and provides the actual steering content. The unfilled spine is a pipeline hygiene gap, not an upload blocker.
- **Suggested fix:** Fill the spine beats from the framing's six-beat arc content. Beat 1 = Crisis/opening. Beats 2–3 = Failed answers. Beat 4 = Pivot (VERBATIM THESIS). Beats 5–6 = Non-bodily correction + Stakes. The framing has all this content already. Does not block upload — address before the next full-book challenger sweep.

---

### P2 (advisory)

None remaining. J2 (Commander of the Believers) was auto-fixed in iteration 1.

---

## Health metrics

| Chapter | Words | Band | Band limits | In-band | Tiers | Blockquote ratio | Phonetic gaps | Framing words | Framing cap |
|---|---|---|---|---|---|---|---|---|---|
| ch11-the-sections-of-the-world | 7,917 | extended | 5,500–9,500 | YES | 5 | ~5.7% | 0 | 3,508 | OVER by 8 (cap 3,500) |

**Word-count note:** Chapter at 7,917 words is within the Extended Deep Dive band (5,500–9,500). Chapter E1 PASS. Framing at 3,508 words exceeds the Extended-tier cap by 8 words. Framing E1 marginal FAIL (P1). The 8-word excess was introduced by the N3 auto-fix (Sahih Muslim Pronounce line added this run).

**Tier diversity (D1):** Tier 1 (al-Kirmani, *Rahat al-'Aql* — 3 quotes), Tier 1 (Quran — Q 89:27-30, Q 25:53), Tier 3 (Sahih al-Bukhari / Sahih Muslim — 2 hadiths), Tier 4 (Imam Ali, *Diwan al-Imam Ali* — 1 quote, pending whitelist clarification), Tier 5 (Imam al-Mu'izz, *Ta'wil al-Shari'a* — 1 quote). 5 tiers. D1 PASS.

**Citation audit:**
- Q 89:27-30 (Surat al-Fajr, line 97): `(Quran 89:27–30; translation rendered after Sahih International)`. A3 PASS (translator named at first occurrence). A1 PASS.
- Q 25:53 (Surah al-Furqan, line 181): `(Quran 25:53, Surah al-Furqan; translation rendered after Sahih International)`. A3 PASS (same translator confirmed). A1 PASS.
- Sahih al-Bukhari, Book 73, Hadith 5534 (line 53, perfume-seller hadith): format complete; this hadith is confirmed in Sahih al-Bukhari. A1/A2 PASS.
- Sahih Muslim, Book 45, Hadith 6376 (line 87, "souls as conscripted soldiers"): citation corrected from prior run (prior: Sahih al-Bukhari Book 60 Hadith 3336 — wrong collection). A1/A2 PASS.
- Imam Ali, *Diwan al-Imam Ali* (line 47): attribution present; source not in Tier 4 whitelist. A1 P1 (see finding).
- Imam al-Mu'izz, *Ta'wil al-Shari'a* (line 163): attribution present. A1 PASS (Tier 5).
- Al-Kirmani, *Rahat al-'Aql* (lines 29, 153, 187): Tier 1 author's own corpus. A1/A4 PASS.

**Honorific audit (O1):**
- `(peace be upon him)` at line 47 (inside blockquote attribution). First expanded form for Imam Ali — PASS.
- `(peace be upon them all)` at line 63 — prose, first occurrence of plural form. PASS.
- `(peace and blessings of Allah be upon him)` at line 67 — prose, first occurrence for the Prophet. PASS.
- All other honorific occurrences are inside verbatim source quotations (exempt per A4).
- O1 PASS.

**Phonetic coverage (N3):** All Arabic transliterations in chapter now have matching Pronounce entries in framing. 0 gaps remaining. N3 PASS.

**Build validator checks (manual):**
- R-NOHTML: no HTML comments in chapter or framing. PASS.
- Meta-prose tells: none detected. PASS.
- R-PHONETICS-OUT (N1): no inline phonetic parens in chapter. PASS.
- R-NO-ABBREVIATION (O2): no forbidden abbreviations found. PASS.
- R-PRONUNCIATION-IMPERATIVE (N2): all Pronunciation block lines begin with `Pronounce "` or `Do not`. PASS.
- R-NO-READ-PROMPT (N4): final line present and correct. PASS.
- R-NOMODERNIZE (M1): full platform-deny list present. PASS.
- R-NOSURPRISE (M2): full surprise-deny list present. PASS.
- R-RECURRING-THESIS: thesis verbatim at 3 anchor points (Opening, Beat 4, Beat 6). PASS.
- R-CHALLENGER-FRICTION: 4 pushback patterns listed + forbidden-opener catalog. PASS.
- R-ANALOGY-CAP: exactly 4 governing analogies enumerated, each bound to a beat. PASS.
- C4: Arabic §2 terms retention justified in framing Pronunciation block (explicit justification paragraph present). PASS.

**Category G (Extract Mode contracts):**
- G1: contract `the-sections-of-the-world.yml` present. PASS.
- G2: `angle: faithful_exposition`, `episode_format: deep_dive`, `length_target: extended` — consistent with framing. PASS.
- G3: No EP## refs, no meta-prose tells in contract key fields. PASS.

**Category Q (chapter-set design, book scope):**
- Q1: "The Sections of the World" — unique in 13-chapter set. PASS.
- Q2: 25 chars, 5 words — within limits. PASS.
- Q3: Not generic. PASS.
- Q4: 7,917 words; `length_target: extended` (5,500–9,500). PASS.

**Framing checks passed:** H1, H2, H3, F2, F3, F4, I1, I2, I3, I4, J1, J3, K1, K2, M1, M2, N2, N3, N4, O1, O2, R1, R2, R3, R4, R5.

**Checks skipped (no transcript):** M3, M4, N5, O3, R6, R7.

---

## Score

**P0:** 0 | **P1:** 3 | **P2:** 0 | **Chapters in scope:** 1 | **Auto-fixes this run:** 2

```
penalty = (0 × 1.0 + 3 × 0.2 + 0 × 0.05) / 1 = 0.60
score   = max(0.0, 1.0 - 0.60) = 0.40  (Unstable)
```

**Verdict: SHIP-WITH-CAUTION** — P0 clean. 3 P1 findings remain: A1 (Diwan al-Imam Ali whitelist gap), E1 (framing 8 words over Extended-tier cap — caused by N3 auto-fix), F5 (discussion spine 14 unfilled stubs — does not block upload). 2 auto-fixes applied this run (J2 alias correction, N3 Sahih Muslim Pronounce line).

**P1 items to address before SHIP-READY:**
1. **A1 (chapter line 47):** Confirm the *Diwan al-Imam Ali* citation. Add an edition reference (volume/page), or cite a Sufi secondary source with chain. "Traditionally attributed" is honest but Tier 4 whitelist requires Nahj al-Balagha or Ghurar al-Hikam for Imam Ali sayings. Escalation to P0 warranted if no edition reference can be supplied.
2. **E1 (framing 3,508 words):** Trim 8–10 words from any prose section to bring framing under the 3,500-word Extended-tier cap. Then re-run `python3 scripts/podcast/build_episode_txt.py content/podcast/library/books/kitab-al-riyad EP11-the-sections-of-the-world`.
3. **F5 (04-discussion-spine.md):** Fill 14 `[LLM-FILL]` stubs from the framing's six-beat arc. Does not block upload — address before the next full-book challenger sweep.

---

## Upload steps (SHIP-WITH-CAUTION — no P0; upload may proceed)

After addressing E1 (framing trim) and re-running the build script, the two-file deliverable for NotebookLM is:

1. **SOURCE** (uploaded to NotebookLM as a source file):
   `/Users/asifhussain/PROJECTS/journal/content/podcast/library/books/kitab-al-riyad/chapters/ch11-the-sections-of-the-world.txt`

2. **CUSTOMIZE PROMPT** (pasted into NotebookLM's customize prompt field):
   `/Users/asifhussain/PROJECTS/journal/content/podcast/library/books/kitab-al-riyad/episodes/EP11-the-sections-of-the-world.txt`

The episode `.txt` must be regenerated before upload (framing was modified this run). Run:
```
python3 scripts/podcast/build_episode_txt.py content/podcast/library/books/kitab-al-riyad EP11-the-sections-of-the-world
```

The A1 P1 (Diwan al-Imam Ali) does not block upload mechanically — it is an enrichment-source whitelist gap the author has deliberately chosen. Upload at author's discretion after reviewing the A1 note above.

---

## Run history note

Prior-run fixes now incorporated: A2 citation corrected (Sahih Muslim), C4 documented (framing justification paragraph), N3 five-term gaps filled (jami', uluhiyya, du'at, hadd, mukasir). This run additionally auto-fixed J2 (Commander of Faithful) and N3-Sahih Muslim. Remaining open: A1 (Diwan whitelist), E1 (8-word framing trim), F5 (spine stubs).
