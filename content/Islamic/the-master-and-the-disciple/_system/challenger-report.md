# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-07 19:23 (challenger v2.4)
**Scope:** per-chapter true-sources-of-knowledge (EP01)
**Iterations:** 1 (of 5 max — converged early; no new auto-fixes after framing block insertions)
**Content profile:** islamic_scholarly (default; series-config.yaml absent → applied full check catalog)
**Verdict:** SHIP-WITH-CAUTION

> The chapter is structurally clean for upload (within hard word band, no em-dash-blocking-build gate, no forbidden doctrinal phrases, citations carry translator + chapter-name + verse), and the framing has been hardened with the missing R-* clauses. Two P1 batches remain for author judgment: em-dash density in chapter prose, and a soft hadith attribution at line 15. No P0 blocks.

## Auto-fixes applied (iteration 1)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | N2 | _system/episode-drafts/EP01-true-sources-of-knowledge/00-framing.md:22-24 | Converted legacy passive `## Pronunciation` list (`- adab: substitute *comportment*`) to R-PRONUNCIATION-IMPERATIVE form (`Pronounce "comportment" as the English noun…`). 3 lines rewritten. |
| 1 | R3 | _system/episode-drafts/EP01-true-sources-of-knowledge/00-framing.md (Tone constraints) | Inserted R-CADENCE clause: short-to-medium sentences, thinking out loud. |
| 1 | R1 | _system/episode-drafts/EP01-true-sources-of-knowledge/00-framing.md (Tone constraints) | Inserted R-SURPRISE-MOVE clause: "plant at least one moment where one host introduces a passage the other has not led toward". |
| 1 | K1 + K2 | _system/episode-drafts/EP01-true-sources-of-knowledge/00-framing.md (Tone constraints) | Inserted R-NOINTERRUPT clause + named filler-interjection list (yeah / right / exactly / of course / absolutely). |
| 1 | R4 | _system/episode-drafts/EP01-true-sources-of-knowledge/00-framing.md (## Do not) | Inserted R-NOFORMAL clause: Firstly / Secondly / Furthermore / In conclusion / Moving on to / To summarize / Lastly. |
| 1 | R5 | _system/episode-drafts/EP01-true-sources-of-knowledge/00-framing.md (## Do not) | Inserted R-NOMODERNIZE permission paragraph (DO use modern-life practical analogies inside the source). |

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### B5: Em-dash density in chapter prose
- **File:** content/Islamic/the-master-and-the-disciple/chapters/ch01a-true-sources-of-knowledge.txt
- **Count:** 45 em-dashes across the chapter (lines 13, 15, 17, 23, 27, 33, 35, 37, 41, 43, 45, 47, 49, 51, 55, 57, 61, 63, 73, 81, 83, 85, 87, 91, 95, 99, 111, 121, 129, 131, 139, 143, 145, 153, 155, 157, 165, 168).
- **Why flagged not auto-fixed:** the deterministic auto-fix rule (`— → , `) would damage scholarly prose where many dashes carry parenthetical-aside weight (e.g., "the chosen ones — *the truly pious, the guardians, the protectors* — are the ones to unveil"). A blanket regex replace would produce comma-spliced run-ons across 45 sites.
- **Suggested fix:** author triage in one pass — convert genuine appositive dashes to commas, convert pause-break dashes to semicolons or sentence splits, retain at most ~3-5 where they carry irreplaceable rhetorical weight.

#### A1 + A4: Soft hadith attribution at line 15
- **File:** chapters/ch01a-true-sources-of-knowledge.txt:15
- **Context:** `*Sit before your food like a slave sits before its master* — a saying transmitted within the broad ethical literature of the canonical hadith collections compiled in the ninth century.`
- **Why flagged:** the saying is presented as Prophetic but cites no collection, book, number, or narrator. Per A1 (citation discipline) a hadith requires collection + book + number + narrator; per A4 (verbatim quote integrity) a softly-attributed hadith risks being a paraphrase circulating in ethical literature without canonical provenance.
- **Suggested fix:** either (a) trace to a canonical collection and add `(<Collection> <Book> #<N>, narrator <Name>)`, or (b) downgrade prose from quote to paraphrase ("the etiquette literature urges the believer to sit before food as a slave before its master"), removing the italic-quote framing.

#### J3 + Name discipline: "Imam Jaʿfar al-Ṣādiq" appears in contract show_notes/anchor_passages but NOT in the rendered chapter
- **File:** chapter-contracts/true-sources-of-knowledge.yml (lines 111, 285, 360)
- **Context:** The contract names "Imam Jaʿfar al-Ṣādiq" three times in the show_notes/anchor_passages/key_tensions blocks but the chapter prose correctly uses "the fifth Imam in our lineage (peace be upon him)" per framing's Name discipline.
- **Why flagged:** the contract is the authoring artifact that drives extract → bundle re-runs. If anyone re-extracts from this contract, the rendered chapter could regress to pairing leadership-title with personal name.
- **Suggested fix:** in the contract, replace "Imam Jaʿfar al-Ṣādiq" with "the fifth Imam of the lineage" wherever the alias would apply; keep the historical-identifier mention if any, but not paired with "Imam".

#### D6: Terminus-technicus check — Arabic terminology not preserved in chapter
- **File:** chapters/ch01a-true-sources-of-knowledge.txt
- **Context:** the contract's `tone_constraints` block lists ~30+ Arabic doctrinal terms with phonetic guides expected to surface in the chapter (`shukr`, `adab`, `ʿabd`, `daʿwa`, `balwā`, `hudā`, `taqwā`, `ẓāhir`, `bāṭin`, `taʾwīl`, `walāyah`, `ʿahd Allāh`, `taqiyya`, etc.). The chapter intentionally renders these in English (per framing's pronunciation block which says "Chapter is plain English; do NOT reintroduce Arabic"). This is a consistent author decision but it means the technical-vocabulary backbone of the source is invisible to the listener.
- **Why flagged:** correct per framing; surfaced as INFO because the design tradeoff (NotebookLM-safety vs. terminus-technicus preservation) is load-bearing and the architect should re-confirm it is intended for this book.
- **Suggested fix:** none required — verify the decision is intentional book-wide, and that the glossary.yml overlay carries the Arabic forms for the reader's "Show Arabic" toggle.

### P2 (advisory)

#### CS5: Chapter-set balance (book scope)
- **Context:** This pass is per-chapter scope. The Category CS book-wide check (chapter-set balance, title uniqueness, length-band fit across all 5 chapters) was NOT run in this invocation. Recommend running `python3 scripts/podcast/check_chapter_set.py content/Islamic/the-master-and-the-disciple` once before publish.

## Health metrics

| Chapter | Words | Heading sections | Citations (named) | Honorifics | Em-dashes |
|---|---|---|---|---|---|
| ch01a-true-sources-of-knowledge | 6,206 | 11 (## Movement headings) | 8 Quranic refs (Arberry, named chapter+verse); 3 *Peak of Eloquence* sayings (Reza translation, numbered); 2 historian refs (Daftary, Halm — full bibliographic) | 2 distinct figures, 1 expansion each (Prophet line 15; fifth Imam line 155) — passes O1 | 45 |

Word band: chapter 6,206 within hard band 500-12,000 (CHAPTER_WORD_MIN_HARD..CHAPTER_WORD_MAX_HARD); inside soft band 1,000-11,000. PASSES E1.

Framing: 795 words, within 150-3,700 word band and under the binding character cap. PASSES E1.

Citation discipline (A1): every Quranic quote names translator (Arberry 1955 *The Koran Interpreted*) + chapter-name + verse number. Every *Peak of Eloquence* quote names translator (Sayed Ali Reza, 1980) + Saying number. Two historian citations carry full bibliographic frame (Daftary 2007 pp. 99–104; Halm 1997 pp. 17–22). PASSES A1 (one P1 exception flagged above for the Prophetic hadith at line 15).

Doctrinal accuracy (T1-T3): chapter uses "Commander of the Faithful" + "fifth Imam in our lineage" — never pairs leadership-title with personal name of the Father of Imams. PASSES T1, T2, T3. The contract YAML carries personal-name pairings in show_notes/anchor_passages (flagged P1 above).

Meta-prose tells (B1-B6): no cross-episode references, no file-length self-references, no translator-apparatus prefixes, no invented dialogue. Framing's `## Do not` block lists "deep dive" / "wow" / "right?" / "mind blown" as forbidden tokens (these appearances are in a DENY list, not voiced content — correct). PASSES B1-B4, B6.

Inline phonetic (N1): zero `*Term* (PHO-NE-TIC; …)` parentheticals in the chapter. PASSES N1.

Welcome / closing-landing (H1-H3): framing's Opening directive includes "brief warm welcome" + previews ONE teaching; Three-part focus → Beat 3 closes with "End on a question". PASSES H1-H3.

Honorific discipline (O1, C3): Prophet honorific expanded once at line 15; fifth-Imam honorific expanded once at line 155. PASSES.

## Verdict justification

SHIP-WITH-CAUTION because:
1. No P0 blocks — chapter is upload-ready as the NotebookLM SOURCE, framing is upload-ready as the Customize prompt.
2. Framing gained the missing R-* steering clauses (R1 / R3 / R4 / R5 / K1 / K2 / N2) deterministically in this pass.
3. Three P1 items remain for author judgment before final ship: em-dash density (45), soft hadith attribution at line 15, contract-vs-chapter name-discipline drift in the contract YAML.

After the author addresses the P1 items, re-invoke the challenger for a clean SHIP-READY pass.

---

**Fixer pass note (2026-06-07):** B5 reduced 45 → 13 em-dashes (remaining are inside scriptural/italicized-speech quotes where author voice carries the weight). A1+A4 downgraded the line-15 Prophetic quote to paraphrase per option (b). J3 (contract YAML name-discipline) NOT fixed: chapter-contracts/true-sources-of-knowledge.yml is outside the fixer-pass allowed-edit scope and needs author edit. D6 confirmed intentional per framing's pronunciation block — no action required.
