# Ch07 v3 Audit Checklist

Use this checklist when the NotebookLM-generated v3 audio and its transcript land in `v3-results/`. Compare against BOTH the v1 transcript (`../v1-baseline/transcript.txt`) AND the v2 transcript/audio (`../v2-revised/`). Fill in each row's **Result** column with the actual count or yes/no observed in v3. The final row gives the verdict.

The framework rules under test are **F20** (no Arabic names in spoken audio — total removal doctrine), **F21** (book-title role-word wrapping), and **F16** (episode-number announcement). All three are documented in `_workspace/plan/pipeline-debt.md`. F14 + F15 (X15 name rotation, X16 challenger friction + analogy cap + dramatic arc + recurring thesis) carry forward from v2.

---

## 1. Arabic person-name occurrences in v3 audio

The v3 doctrine target: **ZERO** occurrences of any Arabic personal name in spoken content. Every figure is referenced by a generic English descriptor.

| Name | v1 count | v2 result (observed) | v3 target | v3 result | Pass? |
|---|---|---|---|---|---|
| al-Kirmani (any form / mangle) | ~30 across episode | ~10 mangles even after rotation discipline ("al-Quraymani", "Alcure Mane", "al-Khir MNA", "al-Qur'an Mayni") | 0 | | |
| Abu Hatim al-Razi (any form) | several | several (first mention) | 0 | | |
| Abu Ya'qub al-Sijistani (any form) | several | several (first mention) | 0 | | |
| Muhammad al-Nasafi (any form) | 1+ | not in v2 | 0 | | |
| Imam Ali ibn Abi Talib (Arabic form) | several | 1 first mention; "Imam Ali" alias used through episode | 0 (replaced with "the Commander of the Faithful") | | |
| Imam al-Mu'izz li-Din Allah | several | 1 first mention | 0 | | |
| Imam Ali Zayn al-Abidin | several | 1 first mention | 0 | | |
| Abd al-Wahid al-Amidi / al-Amidi | several | 1 first mention | 0 | | |
| Abdullah ibn Mas'ud / Ibn Mas'ud | several | 1 first mention | 0 | | |

**Failure mode to watch for.** Even if hosts comply with "no Arabic person-name on first mention," they may default to a recovered Arabic name when they lose track of which descriptor to use. The framing's `## No-name discipline` instructs them to use "he" / "she" / "the same scholar" instead. Audit row fails if ANY Arabic personal name is heard.

---

## 2. Arabic book-title occurrences in v3 audio

The v3 doctrine target: **ZERO** occurrences of any Arabic book title. Every book is referenced by its English title wrapped with the word "book" (F21).

| Title | v1 count | v2 result (observed) | v3 target | v3 result | Pass? |
|---|---|---|---|---|---|
| Kitab al-Riyad / al-Riyad | several | several (first mention + sporadic) | 0 (replaced with "this book") | | |
| al-Mahsul / The Harvest (bare) | several | several | 0 Arabic; English "The Harvest" only with "book" wrapper | | |
| al-Islah / The Correction (bare) | several | several (first mention + sporadic) | 0 Arabic; English only with "book" wrapper | | |
| al-Nusra / The Defense (bare) | several | several (first mention + sporadic) | 0 Arabic; English only with "book" wrapper | | |
| Rahat al-'Aql | several | several (first mention) | 0; replaced with "the master's earlier treatise" | | |
| Ghurar al-Hikam (any form / mangle "Garar al-hikm") | 1+ | 1 first mention | 0; replaced with "the book *The Brilliant Aphorisms*" | | |
| al-Sahifa al-Sajjadiyya | several | several; mangled into "Sahih al-Sajidiyya" (collision with hadith book) | 0; replaced with "the book *The Psalms of Islam*" | | |
| Ta'wil al-Shari'a | several | several (first mention) | 0; replaced with "the Fatimid caliph's interpretive treatise" | | |
| Sahih al-Bukhari / Sahih Muslim | several | several; mangled | 0; replaced with "the canonical hadith collection" | | |
| Surah al-Isra / Surah ash-Shams / Surah Qaf | several | several | 0; replaced with English meaning ("chapter on the night journey") or content-leading citation | | |

**Failure mode to watch for.** Hosts may strip Arabic but drop the "book" wrapper. Bare "The Defense" in conversation can be heard as a poem, a metaphor, an idea. The book role-word disambiguates. Audit row fails if ANY book reference is heard without "the book" / "that book" / "the earlier work" / "the corrective treatise" / "the rebuttal" — i.e., without an unambiguous book-disambiguator.

---

## 3. Book-wrap compliance

For every English book title spoken in the v3 audio, verify that the role-word "book" or an unambiguous book-descriptor appears in the same sentence.

- **v3 target:** 100% of book references wrapped with "the book" / "that book" / "the earlier work" / "the corrective treatise" / "the rebuttal" / "the supplication book" / "the collected sayings" / "the canonical hadith collection."
- **v2 result:** 0% — v2 framing did not require this; bare English titles were the rule.
- **v3 result:** [count of wrapped references / total references = ratio]
- **Pass / fail:** pass if ratio ≥ 95%.

---

## 4. Episode-number announcement (F16)

Listen to the first 90 seconds of the v3 audio. Confirm:

- The hosts announce "Episode 7" (or equivalent listener-facing reference) BEFORE any source-book chapter number.
- The source-chapter reference ("the book's Chapter Three" / "Chapter Three of this book") comes AFTER the episode number.

- **v3 target:** yes — Episode 7 announced first, then chapter context.
- **v2 result:** no — v2 framing only instructed hosts to name "Chapter Three"; listener was confused why "Episode 7" was labeled "Chapter 3."
- **v3 result:** [yes / no / both announced but out of order]
- **Pass / fail:** pass if Episode 7 announced first.

---

## 5. Analogy count

List every distinct analogy used in the v3 transcript. The v3 framing declares THREE governing analogies (footprint, messenger, light-on-glass-and-stone) and EXPLICITLY forbids the five v2 violators (cosmic ruler, crystal pitcher + silver cup, Venn diagram of reality, signet ring + wax, radio tower / antenna).

- **v3 target:** exactly 3 governing analogies. ZERO mid-episode invented analogies.
- **v1 baseline:** 14+ distinct analogies.
- **v2 baseline:** 8 distinct (3 governing + 5 invented — the specifically-named v2 violators).
- **v3 result:** [list every distinct analogy you can identify in v3]
- **Pass / fail:** pass if ≤3 distinct analogies AND no analogy outside the declared three. Specifically: zero occurrences of cosmic ruler, crystal pitcher + silver cup, Venn diagram, signet ring + wax, radio tower / antenna.

---

## 6. Recurring thesis (verbatim count)

Search the v3 transcript for the verbatim formula: *"Contact does not require resemblance — it requires rank, receptivity, and transmitted power"* (or its near-verbatim variant — minor punctuation drift OK; meaning drift NOT OK).

- **v3 target:** 3 verbatim occurrences (opening / pivot / close).
- **v1 baseline:** the formula was never stated.
- **v2 result:** 3 verbatim (passing).
- **v3 result:** [count]
- **Pass / fail:** pass if exactly 3 OR 4 verbatim occurrences; fail if 0, 1, 2, or ≥5.

---

## 7. Challenger friction (Color host pushback count)

Count Color host turns whose **first sentence** is a pushback — i.e. expresses doubt, raises a counter-question, or refuses the prior turn's claim.

- **v3 target:** ≥3 pushback openings by the Color host across the episode.
- **v1 baseline:** ~0.
- **v2 result:** 3 (passing).
- **v3 result:** [count]
- **Pass / fail:** pass if ≥3 distinct pushbacks observable.

---

## 8. Forbidden agreeable openers (Color host)

Search the v3 transcript for any forbidden agreeable opener as the **first sentence** of a Color host turn.

- **v3 target:** 0 occurrences.
- **v2 result:** 0 (passing).
- **v3 result:** [count]
- **Pass / fail:** pass if 0.

---

## 9. 6-beat arc audibility

Listen to the v3 audio and identify whether the structure follows the declared arc (same six beats as v2).

- **v3 target:** all 6 beats audible in order, with reset moments between Beat 4→5 and Beat 5→6.
- **v2 result:** yes — full pass.
- **v3 result:** [yes / partial / no, with notes per beat]
- **Pass / fail:** pass if at least Beats 1, 4, and 6 are clearly identifiable; full pass if all six are audible.

---

## 10. Honorific count

Count occurrences of each honorific form in the v3 transcript.

- **v3 target:** "peace be upon him" once (Commander of the Faithful's first mention); "peace and blessings of Allah be upon him and his family" once (the Prophet in the narration about the verse of the spirit). Each form ≤1.
- **v3 result:** [count per form]
- **Pass / fail:** pass if each form ≤1.

---

## 11. TTS-collision risk surface

In v2, "al-Kirmani" was mangled into "al-Qur'an Mayni" — a phonetic collision with the word "Quran" that introduces a theological error (the listener hears a claim that the Quran itself argues a metaphysical proposition). v3's defense: remove all Arabic names entirely, so there is no surface area for this class of collision.

Audit the v3 framing's allowed-to-speak list for any name or word that phonetically rhymes with "Quran," "Sahih," or other safety-critical English-Arabic mixed phrases:

- "Da'i" (DAA-ee) — rhymes with nothing dangerous. Safe.
- "Imam" (i-MAAM) — rhymes with nothing dangerous. Safe.
- "Yusuf Ali" (YOO-suf a-LEE) — rhymes with nothing dangerous. Safe.
- "Quran" (kur-AAN) — IS the word "Quran" — safe by construction (no collision with itself).

- **v3 target:** 0 collision-risk surface.
- **v2 result:** "al-Qur'an Mayni" collision observed.
- **v3 result:** [list any name in the v3 framing's allowed-to-speak list that phonetically rhymes with safety-critical mixed phrases]
- **Pass / fail:** pass if 0 collision-risk surface remains.

---

## Verdict

After filling in all eleven rows, score the v3 audio against v2 and v1:

**Verdict (v3 vs v2):** [dramatically better / marginally better / no change / worse]
**Verdict (v3 vs v1):** [dramatically better / marginally better / no change / worse]

- Dramatically better than v2 = rows 1, 2, 3, 4, 11 all pass (the new F20+F21+F16 disciplines hold) AND v2's already-passing metrics (5-10) hold.
- Marginally better than v2 = F20 doctrine partially holds (some Arabic names still leak); F21 / F16 may pass.
- No change = ≤3 of the new-discipline rows pass; the v3 lab failed to demonstrate the F20 doctrine.
- Worse = the v3 transcript introduces new failure modes not present in v2 (e.g., listener cannot follow the conversation because too many "the scholar" / "the master" references collapse into ambiguity).

**Each "no" / fail row becomes a new pipeline-debt entry.** For example:
- If row 1 fails (Arabic person-names still spoken): the F20 framing patch needs stronger enforcement language; consider Tier-2 validator that scans chapter/framing for Arabic name patterns.
- If row 3 fails (book references unwrapped): F21 prompt patch needs stricter examples in the framing.
- If row 4 fails (episode number not first): F16 prompt patch needs the exact opening template embedded in the framing.

**Promotion path.** If verdict (v3 vs v2) is "dramatically better", treat v3-revised/ as the new baseline for KaR Ch07 and update the production episode draft EP07 accordingly. Then mark F20, F21, F16 as resolved (or partially resolved per the row scores) in `_workspace/plan/pipeline-debt.md`. If "marginally better," iterate to v4 with whichever specific discipline failed.

**Key empirical question this lab settles.** Can the total-Arabic-removal doctrine produce a podcast episode that is (a) TTS-safe, (b) intellectually coherent without name-attribution, and (c) listenable for 30-45 minutes without the listener losing track of which scholar said what? If yes, F20 is the right framework-level fix for the rest of the series. If no, an intermediate position is needed (e.g., descriptors with role-specific tags like "the Fatimid philosopher" instead of generic "a scholar").
