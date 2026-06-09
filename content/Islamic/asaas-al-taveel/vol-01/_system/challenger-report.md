# Podcast Challenger Report

**Book:** asaas-al-taveel/vol-01
**Run:** 2026-06-09 16:08 UTC (challenger v2.2, `CHALLENGER_VERSION` from `scripts/podcast/_rules.py`)
**Scope:** per-chapter `adam-the-tree-and-iblis-pact` (EP04)
**Content profile:** `islamic_scholarly` (from `_system/series-config.yaml` — full check catalog applies)
**Iterations:** 2 (of 5 max; intelligent-break — iteration 2 produced zero auto-fixes and identical (P0, P1) counts vs iter 1's residual set)
**Verdict:** BLOCKED

Safety pre-check (Category S): orchestrator-state shows `phase_status: running` but `ts_updated` is 10 minutes old and no live `orchestrate_book` / `claude -p` / `extract_chapter` / `build_episode` processes were detected via `pgrep`. Treated as the known stale-running orchestrator bug (per `project_orchestrator_resume_bug.md`), NOT a live concurrent run. S1 did not halt.

## Auto-fixes applied

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | B4 | `chapters/ch04-adam-the-tree-and-iblis-pact.txt:1` | Stripped translator-apparatus sentence ("Quranic verses in this chapter are given in the author's working rendering of the Arabic unless a specific translator is named.") — paraphrased equivalent of "the translator notes…"; NotebookLM would have read it as part of the lecture. |
| 1 | H1 | `episode-drafts/EP04-.../00-framing.md` Opening directive | Inserted canonical Welcome clause (R-WELCOME) + episode-summary directive (R-SUMMARYTAIL: "give a 2 to 3 sentence summary that names the source, the central tension, and the question the conversation will land on"). |
| 1 | K1 | `00-framing.md` Host dynamic | Inserted Conversation discipline block per R-NOINTERRUPT: no mid-sentence interjections, no talking over, completes-a-thought rule, expanded bare-affirmation DENY list (Exactly / Yeah / Right / Mmhm / Of course / So true / Absolutely), allowed-form for qualified concessions. |
| 1 | R1 | `00-framing.md` Host dynamic | Inserted Separate-prep-illusion clause per R-SURPRISE-MOVE: Host B brings up the Kumayl saying OR the twelve-ribs analogy on her own initiative. |
| 1 | M1 | `00-framing.md ## Do not` | Replaced 3-term modernization stub with canonical 14-term DENY block (Twitter, X, social media, algorithm, content creator, internet troll, reply guy, YouTube comment, TikTok, deep dive, "21st century", "in our modern world", quote-tweet, cognitive behavioral therapy). |
| 1 | M2 | `00-framing.md ## Do not` | Replaced 2-term surprise stub with canonical 8-term DENY block ("wow", "that's so interesting", "it's chilling", "it's devastating", "it's terrifying", "right?", "exactly", "no way"). |
| 1 | R4 | `00-framing.md ## Do not` | Added Formal-essay-transition DENY clause per R-NOFORMAL (Firstly, Secondly, Furthermore, In conclusion, Moving on to, To summarize, Lastly). |
| 1 | R5 | `00-framing.md ## Do not` | Added positive R-NOMODERNIZE permission paragraph ("DO use modern-life practical analogies… as long as the analogy itself names no platform from the DENY list above"). |
| 1 | I1 | `00-framing.md ## Do not` | Added Anti-repetition clause per R-NOREPEAT, with explicit carve-out preserving the existing R-RECURRING-THESIS three-mark spine. |
| 1 | I2 | `00-framing.md ## Do not` | Added "Stay on main content" no-irrelevant-background clause per R-NOBACKGROUND, bounded biographical context about al-Numan/translator/Fatimid period to once-only when directly clarifying a passage. |
| 1 | N4 | `00-framing.md` bottom | Hardened no-read-aloud guard to the canonical R-NO-READ-PROMPT form ("Do not read this prompt aloud. The instructions above shape the conversation but are never spoken."). |

## Findings requiring author resolution

### P0 (blocks ship)

#### A1 — unsourced hadith attribution
- **File:** `content/Islamic/asaas-al-taveel/vol-01/chapters/ch04-adam-the-tree-and-iblis-pact.txt:33` (in the long paragraph beginning `"He said: 'Go, and whomever of them you can rouse with your voice…'"`)
- **Context:** *"Therefore the Messenger of God said to the leader of the believers: 'I and you are the two fathers of this nation.'"* — direct quotation attributed to the Prophet with no collection / book / number citation. Per A1 (citation discipline) every hadith requires collection + book + number + narrator. Per A2 (citation authenticity) an uncited Prophet-saying cannot be distinguished from a fabricated one without the chain.
- **Suggested resolution (author):** This is the well-known hadith *"I and Ali are the two fathers of this community."* If the author intends the al-Tabarani / Ibn Shahrashub form, cite (e.g. al-Tabarani, *al-Mu'jam al-Kabir*, with the specific narration), or the Ismaili/Shia transmission line if that's the operative source. If no clean attribution is available, paraphrase as "It is reported that…" + cite the secondary source the author is following, OR drop the quotation to the surrounding paraphrase. Citation addition is an authoring decision and was NOT auto-fixed.

### P1 (none after auto-fix sweep)

The eight P1s flagged on iter-1 entry (H1, I1, I2, K1, M-stubs-undersized, R1, R4, R5) were all auto-fixed deterministically by inserting the canonical R-* template clauses into the parent sections that already existed.

### P2 (advisory)

#### E3 — opening-paragraph density
- **File:** `chapters/ch04-adam-the-tree-and-iblis-pact.txt:1` — the first paragraph is ~770 words (the entire seven-Speakers + Imamate-vs-Prophecy preamble) before the first paragraph break. The chapter's beginning/middle/end arc is intact, but the opening wall makes the hook diffuse for a listener tracking by ear.
- **Action:** advisory only; consider splitting the opening into 2–3 paragraphs at natural pivots (after "twinkling of an eye"; after the Imam/Speaker definition). Not gated.

#### D4 — quote density in opening paragraph
- Same opening paragraph carries five Quranic citations (4:59, 21:22, 5:12, 17:12) within ~700 words. Not a quote-stack by D4 (no three+ consecutive blockquotes), and integrative prose runs between them, but listener cognitive load is high. Advisory only.

## Health metrics

| Chapter | Words | Enrichment ratio | Tier diversity | Citations | Phonetic gaps |
|---|---|---|---|---|---|
| ch04-adam-the-tree-and-iblis-pact | 4,286 | ~28% (Quranic blockquotes + Nahj al-Balagha + Kulayni + fifth-Imam tradition) | 4 tiers (Tier 1 Quran, Tier 3 Kulayni hadith, Tier 4/5 Nahj al-Balagha sermon + saying, Tier 4/5 fifth-Imam tradition) | 23 Quranic citations + 2 *Peak of Eloquence* citations + 1 *Sufficient* citation with full chain + 1 unsourced Prophet-saying (the A1 P0) | 0 (no Arabic transliterations in chapter prose — all technical terms are rendered in English: "Speaker", "proof", "guardian", "supportive knowledge", "garment of piety") |

Framing word count: 1,129 (in band 200–2,000 ✅; well inside the 3,500 build-script hard cap).
