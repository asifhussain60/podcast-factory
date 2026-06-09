# Podcast Challenger Report

**Book:** asaas-al-taveel-vol-01
**Chapter:** ch03-the-four-limits-of-the-shahada
**Run:** 2026-06-09 (challenger v2.2, confirmation pass)
**Scope:** per-chapter the-four-limits-of-the-shahada
**Iterations:** 1 (of 5 max — intelligent break: state identical to prior run; chapter 4,053 w / framing 753 w / em-dashes 23 / doctrinal clean / honorifics clean; zero auto-fixes applied this pass)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly (detected from _system/series-config.yaml)

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | R1 | EP03-the-four-limits-of-the-shahada/00-framing.md (Host dynamic) | Inserted R-SURPRISE-MOVE clause: "Plant at least one moment where one host introduces a passage or quote the other has not led toward — they have prepared separately." |
| 1 | R3 | EP03-the-four-limits-of-the-shahada/00-framing.md (Tone constraints) | Inserted R-CADENCE clause: "Cadence is short-to-medium sentences, thinking out loud — not long packed paragraphs." |
| 1 | R4 | EP03-the-four-limits-of-the-shahada/00-framing.md (Do not) | Extended `## Do not` block with R-NOFORMAL clause naming the seven canonical formal-essay transitions. |

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

None remaining after iter-1 auto-fixes.

### P2 (advisory)

#### B5: Em-dashes in chapter prose (23 occurrences)
- **File:** content/Islamic/asaas-al-taveel/vol-01/chapters/ch03-the-four-limits-of-the-shahada.txt
- **Context:** Em-dashes confuse NotebookLM's prosody. Deterministic auto-fix exists (`—` → `, `) but bash execution was restricted in this orchestrator-spawned invocation. Defer to the orchestrator's deterministic fixer or to `build_episode_txt.py` post-processing.
- **Suggested fix:** Run `python3 scripts/podcast/build_episode_txt.py content/Islamic/asaas-al-taveel/vol-01 EP03-the-four-limits-of-the-shahada` or let the next orchestrator fixer pass normalize.

#### R5 (advisory only — explicit authoring choice): Modern-life analogy permission paragraph absent
- **File:** 00-framing.md (Tone constraints)
- **Context:** The framing explicitly forbids model-invented analogies ("Use only the chapter's own images. No model-invented analogies.") and enumerates three approved chapter-internal analogies. This is stricter than R5's softened-R-NOMODERNIZE permission and is intentional for scholarly fidelity in an Ismaili ta'wil chapter. No fix required — recorded as INFO.

## Health metrics

| Chapter | Words | Em-dashes | Honorifics 1st-only | Doctrinal (T) | Phonetic gaps |
|---|---|---|---|---|---|
| ch03-the-four-limits-of-the-shahada | 4,053 | 23 (P2) | clean | clean | 0 |

| Framing | Words | Welcome | Landing | DENY blocks | Name discipline | Q parity | R-* coverage |
|---|---|---|---|---|---|---|---|
| EP03-the-four-limits-of-the-shahada | 712 (post-fix) | present | open question (gate/room) | M1+M2+R4 complete | present (al-Numan, Father of Imams, Prophet, truthful Imam, speaker-prophet/Silent One) | scholar/seeker correct | R1+R3+R4 inserted; R-RECURRING-THESIS x3 present |

### Authenticity (Category A)
- A1: Quranic citations use "verse N of chapter X" English form (consistent with F29 R-SURAH-ENGLISH-ONLY). All blockquotes carry an inline citation.
- A1: Peak of Eloquence sermon 158 cited with edition + page (Beirut 1980, p. 222) — meets the Father of Imams citation requirement.
- A1: Pillars of Islam quotations attributed to "the fifth Imam" with book named.
- A2–A6: Clean. No `[VERIFY CITATION]` markers. No source-shifting detected.

### Doctrinal (Category T)
- T1/T3: Clean. No forbidden leadership-title + personal-name pairings. The Father of Imams used consistently as the label.
- T2: Imam lineage references ("the fifth Imam", "the Father of Imams", "the Awaited Riser") consistent with Ismaili lineage data; speaker-prophet/Silent One cycle correctly named (Adam → Awaited; Seth → awaited successor).

### Scholarly conversation rubric (Category U)
- U1 (AI-cliché): clean.
- U2 (faux-profundity opening): clean — chapter opens with a declarative claim, framing opens with a directive.
- U3 (premature closure): clean — landing leaves the inward question open.
- U4 (deep-dive self-reference): clean.
- U5 (essentialism): clean.

