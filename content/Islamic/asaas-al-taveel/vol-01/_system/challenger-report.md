# Podcast Challenger Report

**Book:** asaas-al-taveel-vol-01
**Chapter:** ch02-the-call-to-inner-meaning
**Run:** 2026-06-09 (challenger v2.2)
**Scope:** per-chapter the-call-to-inner-meaning
**Iterations:** 1 (of 5 max — intelligent break: zero auto-fixes applied; remaining findings are minor authoring nudges)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly (detected from _system/series-config.yaml)

## Auto-fixes applied (iteration-by-iteration)

None applied this run. The chapter and framing are in strong shape; the framing now carries the full R-* clause set that was absent in the prior report. B5 (em-dashes) is normally an auto-fix but bash execution is restricted in this invocation — surfaced as P2 for the orchestrator's deterministic fixer / build script to handle.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R1: Separate-prep illusion clause missing in Host dynamic
- **File:** content/Islamic/asaas-al-taveel/vol-01/_system/episode-drafts/EP02-the-call-to-inner-meaning/00-framing.md (Host dynamic, lines 26–28)
- **Context:** Host dynamic block does not include the R-SURPRISE-MOVE directive ("plant at least one moment where one host introduces a passage the other has not led toward"). Without it, the conversation feels lock-step.
- **Suggested fix:** Append a line to Host dynamic: "Plant at least one moment where one host introduces a passage or quote the other has not led toward — they have prepared separately."

#### R3: Cadence directive missing from Tone constraints
- **File:** 00-framing.md (Tone constraints, lines 30–31)
- **Context:** Tone section does not name short-to-medium sentence rhythm / "thinking out loud" cadence (R-CADENCE). Without it, NotebookLM tends toward long packed sentences.
- **Suggested fix:** Add to Tone constraints: "Cadence is short-to-medium sentences, thinking out loud — not long packed paragraphs."

### P2 (advisory)

#### B5: Em-dashes in chapter prose (7 occurrences)
- **File:** content/Islamic/asaas-al-taveel/vol-01/chapters/ch02-the-call-to-inner-meaning.txt (lines 5, 21, 33, 41, 55, 59, 61)
- **Context:** Em-dashes confuse NotebookLM's prosody. Deterministic auto-fix exists (`—` → `, `) but bash execution was restricted in this invocation.
- **Suggested fix:** Run `python3 scripts/podcast/build_episode_txt.py content/Islamic/asaas-al-taveel/vol-01 EP02-the-call-to-inner-meaning` or let the orchestrator fixer normalize.

## Health metrics

| Chapter | Words | Em-dashes | Honorifics 1st-only | Doctrinal (T) | Phonetic gaps |
|---|---|---|---|---|---|
| ch02-the-call-to-inner-meaning | 4,483 | 7 (P2) | clean | clean | 0 |

| Framing | Words | Welcome | Landing | DENY blocks | Name discipline | Q parity |
|---|---|---|---|---|---|---|
| EP02-the-call-to-inner-meaning | 652 | present | open question | M+S+formal complete | present | scholar/seeker correct |

## Category dispatch

- A (Authenticity): clean — every Quranic quote carries `(Quran X:Y)`; al-Nu'man's *Pillars of Islam* citations name book + chapter; *Nahj al-Balagha* citation names compiler + translator.
- B (Meta-prose): clean except B5 (P2).
- C/N (Phonetics): chapter is phonetic-out; framing uses correct `term: phonetic` format per F20/F29 lock.
- D (Enrichment): multi-tier (Quran, hadith, *Pillars of Islam*, *Nahj al-Balagha*, Asad, Corbin) — clean.
- E (Articulation): word count in band; one-sentence summarizable; BME arc clean.
- F (Framing): four-part structure present.
- H (Welcome/Landing): clean.
- I (Anti-repetition / no-background): clean.
- J (Name discipline): clean.
- K (Interruption / filler): R-NOINTERRUPT + named fillers present.
- M (Modernize/Surprise DENY): clean, both halves of R-NOMODERNIZE present.
- O (Honorific/Abbreviation): clean.
- Q (Host parity): scholar/seeker pair correct.
- R (Conversation choreography): R1 + R3 missing (P1 above); R4 (R-NOFORMAL) and R5 (analogy permission) present.
- T (Doctrinal): clean — no forbidden naming pairings; Ja'far al-Sadiq correctly identified as fifth Imam; Father of Imams referenced by title only.
- U (Scholarly-conversation): clean — no AI clichés in voiced text; DENY block covers them.
- V (Interest): hook present (opening salutation reframed as structural claim), challenge-defeat arc present (steelman + refutation in Beat 3), modern-relevance signal present (analogy permission opens it), no strawman.
