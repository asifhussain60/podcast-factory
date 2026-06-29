# Ch07 v2 Audit Checklist

Use this checklist when the NotebookLM-generated v2 audio and its transcript land in `v2-results/`. Compare against the v1 transcript in `../v1-baseline/transcript.txt`. Fill in each row's **Result** column with the actual count or yes/no observed in v2. The final row gives the verdict.

The framework rules under test are **F14** (X15 name-rotation discipline) and **F15** (X16 dramatic arc, challenger friction, analogy cap, recurring thesis). Both are documented in `_workspace/plan/pipeline-debt.md`.

---

## 1. Name mangle frequency

Count how many times each form of "al-Kirmani" (and its mangled variants) appears in the v2 transcript. v1 transcript exhibited 12+ distinct garbled variants (`al-Quraymani`, `alkyr M a knee`, `I'll carry many`, `Alcure MNE`, `al-kheir MNE`, `I'll care ma me`, `Alkur Emini`, `Alkyr a main knee`, `al-kheira may has`, `Al-cure Mane`, `Alkira main`, `al-kiramain`).

- **Target:** ≤2 total occurrences of any "al-Kirmani"-shaped word in v2 (only the first mention should be Arabic; the rest should be English aliases).
- **v1 baseline:** 12+ distinct mangle variants, total occurrences ~30 across the 30-minute episode.
- **v2 result:** [count here]
- **Pass / fail:** [yes / no]

Repeat the same audit for:
- `al-Hayuli` (v1: 24+ mangle variants such as `al-hayyullah`, `all how you law`, `alayullah`, `al-hi you la`) — v2 target: 1 occurrence on first mention, then "prime matter" thereafter.
- `al-Islah` (v1: `all is La H`) — v2 target: 1 occurrence; thereafter "The Correction" or "Abu Hatim's book".
- `al-Nusra` (v1: `an NUS raw`, `NUS Rob`, `NUS Ross`) — v2 target: 1 occurrence; thereafter "The Defense" or "al-Sijistani's book".
- `ma'lul` (v1: `ma. Lol`) — v2 target: 1 occurrence on first technical introduction; thereafter "the effect".
- `Ghurar al-Hikam` (v1: `Garar al-hikm`) — v2 target: 1 occurrence on first mention.

| Name | v1 count | v2 target | v2 result | Pass? |
|---|---|---|---|---|
| al-Kirmani (any form) | ~30 | ≤2 | | |
| al-Hayuli (any form) | 24+ | 1 | | |
| al-Islah | several | 1 | | |
| al-Nusra | several | 1 | | |
| ma'lul | 2 | 1 | | |
| Ghurar al-Hikam | 1 | 1 | | |

---

## 2. Analogy count

List every distinct analogy used in the v2 transcript. The v2 framing declares THREE governing analogies; the test is whether the hosts stayed inside that envelope.

- **v2 target:** exactly 3 governing analogies (footprint, messenger, light-on-glass-and-stone). ZERO mid-episode invented analogies.
- **v1 baseline:** 14+ distinct analogies — footprint, political map/border, messenger, white-coat doctor, glass-and-stone, fulcrum, sphere, pie chart, cathedral, ladder/mountain/valley, seven seas, solar panels, wax-seal, blue-and-red countries.
- **v2 result:** [list every distinct analogy you can identify in v2]
- **Pass / fail:** pass if ≤3 distinct analogies AND no analogy outside the declared three.

---

## 3. Recurring thesis (verbatim count)

Search the v2 transcript for the verbatim formula: *"Contact does not require resemblance — it requires rank, receptivity, and transmitted power"* (or its near-verbatim variant — minor punctuation drift OK; meaning drift NOT OK).

- **v2 target:** 3 verbatim occurrences (opening / pivot / close).
- **v1 baseline:** the formula was never stated; the closest v1 paraphrase was "contact does not require resemblance" (stated once in the middle of the episode).
- **v2 result:** [count]
- **Pass / fail:** pass if exactly 3 OR 4 verbatim occurrences; fail if 0, 1, 2, or ≥5.

---

## 4. Challenger friction (Color host pushback count)

Count Color host turns whose **first sentence** is a pushback — i.e. expresses doubt, raises a counter-question, or refuses the prior turn's claim. Pushback patterns from the framing:
- "I don't buy that yet…"
- "That sounds like wordplay…"
- "Isn't this just replacing X with Y…"
- "How is this different from hiding the problem under a different word…"

- **v2 target:** ≥3 pushback openings by the Color host across the episode (the framing requires 3 of 4 patterns).
- **v1 baseline:** ~0 — the Color host was almost entirely supportive ("That is a remarkably precise analogy", "That beautifully maps al-Kirmani's intent", "That is the perfect translation").
- **v2 result:** [count of pushback openings]
- **Pass / fail:** pass if ≥3 distinct pushbacks observable.

---

## 5. Forbidden agreeable openers (Color host)

Search the v2 transcript for any of the following as the **first sentence** of a Color host turn:
- "That is a remarkably precise…"
- "That beautifully maps…"
- "That is the perfect translation…"
- "That captures the essence…"
- "Exactly" (single-word)
- "Perfect way to put it"
- "That is fascinating"
- "That is brilliant"

- **v2 target:** 0 occurrences. Each occurrence is a violation of R-CHALLENGER-FRICTION.
- **v1 baseline:** ~5 — the v1 transcript shows "That is a remarkably precise analogy for what is happening", "That beautifully maps al-Kirmani's intent", "That is the perfect translation of this concept into modern mechanics", "That is the perfect way to frame the error", "That is a fantastic way to visualize it".
- **v2 result:** [count]
- **Pass / fail:** pass if 0; fail if ≥1.

---

## 6. 6-beat arc audibility

Listen to the v2 audio and identify whether the structure follows the declared arc:
1. **Crisis** — does the open foreground the rebutter's universe-disconnection fear with emotional weight, BEFORE any solution?
2. **Failed answer A** — is the chief preacher's trace-not-birth doctrine presented as reasonable (not pre-emptively refuted)?
3. **Failed answer B** — is the master of the school's mixed-edges counter presented as reasonable (not pre-emptively refuted)?
4. **Pivot** — does the author deliver the central thesis as the move that escapes both failed answers? Is the verbatim thesis present here?
5. **Non-bodily correction** — do sub-chapters 2-5 (no parts, no sides, no distance, no diminution) land as a sequence of body-category refusals, not as a flat list of doctrines?
6. **Stakes + question** — does the close ground the stakes in the *ta'wil* of the trust and bridge to *Chapter Four* with an open question?

- **v2 target:** all 6 beats audible in order, with reset moments between Beat 4→5 and Beat 5→6.
- **v1 baseline:** explanations were interleaved without a clear arc; the crisis was stated and immediately resolved; the body-category refusals were summarized rather than enacted as a sequence.
- **v2 result:** [yes / partial / no, with notes per beat]
- **Pass / fail:** pass if at least Beats 1, 4, and 6 are clearly identifiable; full pass if all six are audible.

---

## 7. Honorific count

Count occurrences of each honorific form in the v2 transcript:
- `ﷺ` (the glyph — should be zero, hosts speak the full English)
- "(peace be upon him)" / "peace be upon him"
- "(peace and blessings of Allah be upon him and his family)" / "peace and blessings of Allah be upon him"
- "(peace be upon them)" / "peace be upon them"

- **v2 target:** each form appears at most 1 time. Specifically: "peace be upon him" once (Imam Ali's first mention), "peace and blessings of Allah be upon him and his family" once (the Prophet in the Ibn Mas'ud hadith).
- **v1 baseline:** should already be deduped from earlier X6+X8 work — verify.
- **v2 result:** [count per form]
- **Pass / fail:** pass if each form ≤1.

---

## Verdict

After filling in all seven rows, score the v2 audio against v1:

**Verdict:** [dramatically better / marginally better / no change / worse]

- Dramatically better = 5-7 rows pass + listening confirms structural improvement (clear arc, sustained challenger friction, no mangle storm).
- Marginally better = 3-4 rows pass + listening confirms partial improvement (some progress on name mangling, partial arc).
- No change = ≤2 rows pass.
- Worse = the v2 transcript introduces new failure modes not present in v1.

**Each "no" / fail row becomes a new pipeline-debt entry.** For example:
- If row 1 fails (mangle count still high): the rotation discipline didn't bind NotebookLM strongly enough; new debt entry around the framing's name-discipline section's enforceability.
- If row 4 fails (no pushback): the R-CHALLENGER-FRICTION rule needs more aggressive scaffolding (perhaps explicit per-tension turn-skeleton in the framing).
- If row 2 fails (analogies proliferated): R-ANALOGY-CAP needs a stronger forbidden-list, or NotebookLM is generating analogies regardless of framing language.

**Promotion path.** If verdict is "dramatically better", copy `v2-revised/chapter.txt` → `chapters/ch07-soul-and-spirit-one-substance-or-two.txt` and `v2-revised/framing.md` → `_system/episode-drafts/EP07-soul-and-spirit-one-substance-or-two/00-framing.md`, regenerate the episode txt via the standard build step, and commit as the new EP07. Then mark F14 + F15 as resolved (or partially resolved per the row scores) in `_workspace/plan/pipeline-debt.md`.
