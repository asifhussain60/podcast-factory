# Series Plan — Degrees of Excellence

**Book slug:** `degrees-of-excellence`
**Branch:** `Islamic/degrees-of-excellence`
**Generated:** 2026-07-31T15:46Z
**Orchestrator:** v1.2
**Unit mode:** `auto`
**Status:** AWAITING HUMAN APPROVAL

---

## Human-reviewed sections

### Length tier (AI recommendation)

**Tier:** `extended`
**Rationale:** All chapters target the same length tier — series is balanced.

### Essentiality recommendations

Episodes the LLM flagged as **optional**, **bonus**, or **skip** during Phase 0d
content analysis. CORE episodes are not listed (the default; cannot be removed
without breaking the arc). To act on a `skip` recommendation, delete the
contract + chapter file before resuming.

| # | Slug | Essential? | Why |
|---|---|---|---|
| 1 | `the-fatimid-world-and-al-naysaburi` | **optional** | This is the translator's contextual overview of the world, the author, and the book's structure; a listener who skips straight to the treatise episodes still gets the full doctrine, so it is genuine framing rather than load-bearing argument.
 |

### Episode list

Columns:
- **Format** — `deep_dive` (Mentor+Student exposition) | `debate` (named voices clash + arbiter) | `narrative` (historical/biographical) | `interview` (Q&A)
- **Essential** — `core` | `optional` | `bonus` | `skip` (see Essentiality recommendations above)
- **Upload** — file to drop in NotebookLM's *Sources* panel
- **Customize** — file whose contents go in NotebookLM's *Customize* box (written by Phase 0g)
- **Length cue** — what to declare in the customize prompt's opening directive
- **Hosts** — host pairing for NotebookLM's customize prompt

#### Session 2 — Introduction: The Fatimid World, the Author, and the Theory of Degrees of Excellence · 2 episode(s)

| # | Title | Words | Tier | Format | Essential | Upload (NotebookLM source) | Customize | Length cue | Hosts |
|---|---|---|---|---|---|---|---|---|---|
| 1 | The Fatimid World and al-Naysaburi | 5972 | extended | **deep_dive** | optional | `chapters/ch01a-the-fatimid-world-and-al-naysaburi.txt` | `episodes/EP01-the-fatimid-world-and-al-naysaburi.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 2 | Degrees of Excellence Explained | 5944 | extended | **deep_dive** | core | `chapters/ch02b-the-theory-of-degrees-of-excellence-explained.txt` | `episodes/EP02-the-theory-of-degrees-of-excellence-explained.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |

#### Session 4 — The Treatise: Affirming the Imamate · 6 episode(s)

| # | Title | Words | Tier | Format | Essential | Upload (NotebookLM source) | Customize | Length cue | Hosts |
|---|---|---|---|---|---|---|---|---|---|
| 3 | The Imamate, Pole of Religion | 6019 | extended | **deep_dive** | core | `chapters/ch03a-the-imamate-pole-and-foundation-of-religion.txt` | `episodes/EP03-the-imamate-pole-and-foundation-of-religion.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 4 | The Peak of Every Kind | 6057 | extended | **deep_dive** | core | `chapters/ch04b-degrees-of-excellence-the-peak-of-every-kind.txt` | `episodes/EP04-degrees-of-excellence-the-peak-of-every-kind.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 5 | The Imam's Authority | 6629 | extended | **deep_dive** | core | `chapters/ch05c-the-imam-and-the-authority-over-sacred-law.txt` | `episodes/EP05-the-imam-and-the-authority-over-sacred-law.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 6 | Worship and Law Without the Imam | 5985 | extended | **deep_dive** | core | `chapters/ch06d-worship-alms-and-war-void-without-the-imam.txt` | `episodes/EP06-worship-alms-and-war-void-without-the-imam.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 7 | Prophets, Symbols, and the Caliphs | 6083 | extended | **deep_dive** | core | `chapters/ch07e-prophets-as-symbols-and-the-first-caliphs.txt` | `episodes/EP07-prophets-as-symbols-and-the-first-caliphs.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 8 | The Imam Who Mirrors God | 5794 | extended | **deep_dive** | core | `chapters/ch08f-the-virtues-of-ali-the-imam-who-mirrors-god.txt` | `episodes/EP08-the-virtues-of-ali-the-imam-who-mirrors-god.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |

### Source-chapter → episode map

| source chapter | source title | episode(s) | split reason |
|---|---|---|---|
| 1 | Front Matter, Preface and Acknowledgements | (none — editorial front matter / apparatus, F4-excluded, essential=skip) | Title pages, publisher/series boilerplate, table of contents, dedication, and the translator's Preface and Acknowledgements. Translator-authored paratext that speaks of the book in the third person and describes the editing process; excluded from the episode array under F4/F23. The one substantive thread (imamate as pole of religion; the degrees-of-excellence theory) is carried as real teaching in the Introduction (sc 2) and the treatise (sc 4), so nothing teachable is lost. Flagged skip for Asif to confirm at 0f. |
| 2 | Introduction: The Fatimid World, the Author, and the Theory of Degrees of Excellence | ch01a-the-fatimid-world-and-al-naysaburi.txt, ch02b-the-theory-of-degrees-of-excellence-explained.txt | The translator's scholarly Introduction is genuine listener framing (not manuscript apparatus), kept as one arc and split at its strongest thematic seam. 8,553 words and five distinct teachings force two episodes (word floor ceil(8553/6000)=2; concept floor ceil(5/3)=2). Ep1 (source 221-318) sets the Fatimid intellectual world, the author and his works, and the seven-section shape and novel method of the treatise — deep_dive, essential=optional (contextual framing). Ep2 (source 319-520) carries the recurring themes (cycles, ever-present imam, mission ranks, the philosophers reclaimed, the physician-of-souls defense) and the centerpiece theory of degrees of excellence — deep_dive, essential=core. The philological manuscript description and translation notes were split off into the adjacent skip unit (sc 3). |
| 3 | Description of the Arabic Manuscripts; Notes on the Translation | (none — editorial apparatus / philological notes, F4-excluded, essential=skip) | Manuscript history (ten variants held by the Institute of Ismaili Studies, five collated — alif, ba, ta, tha, jim — with shelf marks, colophons, copyists and physical condition) plus the translator's methodology (omitted benedictions and polemics, supplied punctuation/diacritics/section-numbering, and the rendering choices for ithbat and tafadul). Translator-authored paratext that speaks of the book in the third person as a published object and documents the editing process; excluded from the episode array under F4/F23 (thesis_relevance out-of-scope). The one interpretive thread — the semantic range of tafadul — is already taught as the degrees-of-excellence theory in the Introduction (sc 2, ep 2) and the treatise (sc 4), so nothing teachable is lost. Flagged skip for Asif to confirm at 0f. |
| 4 | Book on Affirming the Imamate (Kitab ithbat al-imama) - the treatise | ch03a-the-imamate-pole-and-foundation-of-religion.txt, ch04b-degrees-of-excellence-the-peak-of-every-kind.txt, ch05c-the-imam-and-the-authority-over-sacred-law.txt, ch06d-worship-alms-and-war-void-without-the-imam.txt, ch07e-prophets-as-symbols-and-the-first-caliphs.txt, ch08f-the-virtues-of-ali-the-imam-who-mirrors-god.txt | The treatise itself (source lines 567-1453, the scholarly rendering, NOT the duplicate second translation later in the file), kept whole and partitioned into six episodes. 24,102 words and roughly twelve distinct doctrinal units force at least five episodes (word floor ceil(24102/6000)=5; concept floor ceil(12/3)=4); split into six so each lands under the 6,000 upper bound and holds one coherent teaching cluster of at most three concepts, cutting at the author's own section seams and paragraph-numbered movements. Ep3 [1]-[16] opens the treatise: the imamate as the pole and foundation of religion, its rational necessity, and the two-witnesses creation-parallel that grounds everything after. Ep4 [17]-[30] is the concrete ladder of degrees of excellence — fire, sun, gold, ruby, wheat, the date palm, the antidotes and their poisons, the noblest animals — climbing to humankind and its summit, kept whole so no exemplar straddles a boundary. Ep5 [31]-[49] develops what the summit authorizes: the ownership of creation, the ladder of spirits, the argument from absolute wisdom, and the necessity that the leader be the best. Ep6 [50]-[67] shows worship, alms, holy war, the prescribed penalties, and judgeship void without the imam, closing on the refutation of the usurpers' foundations. Ep7 [68]-[75] traces the ever-present, designated imam through the prophetic cycles (Adam, Noah, Abraham, Moses, Jesus, Muhammad) and refutes the first caliphs by the three virtues. Ep8 [79]-[91] culminates in the virtues of the Commander of the Faithful, Ali b. Abi Talib, the imam who mirrors God's dealing with creation, and the closing supplication (paragraphs [76]-[78] are absent from the source, which jumps [75] to [79]). All six were authored in the extended band (5,517-5,677 words) by unpacking the source's own compressed argument, not by importing outside material (Phase 0e's task). The opening dedication to the ruler and the closing manuscript-submission are book-object provenance and, per the NOISE RULE, were compressed rather than reconstructed as content. |
| 5 | Select Bibliography, Indexes, and a Second Translation of the Treatise | — (no episodes) | Editorial apparatus + redundant second translation; excluded per F4/F23/R-NO-DOCTRINE-REPEAT. Bibliography (lines 1-480) and General + Quranic indexes (lines 481-752, 1410-1956) are backmatter apparatus with no source doctrine. The Second Translation of the Treatise (lines 753-1409) re-renders al-Naysaburi's Kitab ithbat al-imama already taught in full across ch01a-ch08f — every doctrine is on the de-dup list, so re-teaching it whole is a defect. Closes with manuscript colophons (book-object provenance = noise). Global plan pre-assigned episode_count: 0. Operator-discretion apparatus only. |

---

## Audit-trail-only sections (no human review)

### Audience (orchestrator config default)
Thoughtful general listeners arriving at a work of medieval Islamic theology with no background assumed. They want the doorway to the whole series: who al-Naysaburi was, what world produced him, and what his book sets out to prove. They are not here for manuscript history or scholarly apparatus; they want the human and intellectual context that makes the argument of the later episodes land — why a Shi'i empire staked itself on the imamate, why proving that doctrine by reason (not scripture alone) was a daring new move, and what the seven-part shape of the treatise is.

### Angle (orchestrator config default)
faithful_exposition

### Host dynamic (AI-selected per chapter)
| Chapter | Host dynamic | Rationale |
|---|---|---|
| `the-fatimid-world-and-al-naysaburi` | curious_mind + scholar_companion | The curious_mind voices the newcomer's orienting questions (why was a Shi'i empire so remarkable? what made proving the imamate by reason new? how is the book built?); the scholar_companion supplies the historical scaffolding — the Ismaili century, the reason-versus-revelation debate, al-Naysaburi's Nishapur formation and his surviving works, and the seven-section method.
 |
| `the-theory-of-degrees-of-excellence-explained` | curious_mind + scholar_companion | The curious_mind presses the questions a first-time listener would ask (why should a fact about gold tell us anything about the imam? why two figures per cycle? how does the ladder actually reach a human conclusion?); the scholar_companion supplies the doctrinal scaffolding — the natiq/samit pairs, the symbol-and-symbolized hinge, the ten categories, the four elements, the outermost sphere and Universal Intellect, and the closing man-as-pinnacle passage.
 |
| `the-imamate-pole-and-foundation-of-religion` | curious_mind + scholar_companion | The curious_mind presses the newcomer's questions (why would the imam outrank the messenger who brings the revelation? how could the natural world testify to a religious office?); the scholar_companion supplies the doctrine — the imamate as pole (qutb) and foundation (asas al-din), the ever-present imam against the intermittent messenger, and the twin testimony of the horizons and the souls.
 |
| `degrees-of-excellence-the-peak-of-every-kind` | curious_mind + scholar_companion | The curious_mind keeps asking the honest skeptic's question — why should a fact about gold or a ruby tell us anything about a human office? — while the scholar_companion walks the cascade specimen by specimen, drawing out why each is the peak of its kind and how the criteria quietly assemble the portrait of the imam.
 |
| `the-imam-and-the-authority-over-sacred-law` | curious_mind + scholar_companion | The curious_mind voices the discomfort a modern listener feels at the strongest claims (what does it mean that everything belongs to the imam? that rejecting him is like an animal refusing its master?); the scholar_companion supplies the grounding — the ownership of creation and the meaning of fay', the ladder of spirits crowned by the creative spirit, the argument from absolute wisdom, and the logic that the leader cannot be the one who is led.
 |
| `worship-alms-and-war-void-without-the-imam` | curious_mind + scholar_companion | The curious_mind asks how a rite as ordinary as facing the qibla could be an argument about leadership, and why the usurpers' position should collapse; the scholar_companion supplies the chain — the etymology of imam and qibla, the congregational multiplier, the guarantor, the alms that only the imam may collect, the banner of holy war, and the penalties reserved to lawful authority.
 |
| `prophets-as-symbols-and-the-first-caliphs` | curious_mind + scholar_companion | The curious_mind asks why a change of qibla should carry an argument about succession, and whether the refutation of the caliphs is fair; the scholar_companion supplies the frame — the lesson of Adam and the angels, Noah's ark, the returning direction of prayer, and the measure of knowledge, holy struggle, and piety by which al-Naysaburi weighs the claimants.
 |
| `the-virtues-of-ali-the-imam-who-mirrors-god` | curious_mind + scholar_companion | The curious_mind voices the modern reader's unease at the highest claims (how can it be praise that a man treats the faithless as well as the faithful? what keeps this from divinizing him?); the scholar_companion supplies the doctrine — the perfector who gathers the whole line, the mirroring of God's impartial bounty and concealed means, and the middle path between reduction and the exaggerators that names him the Universal Vicegerent.
 |

---

## NotebookLM input checklist (per-episode workflow)

After Phase 0g writes the per-episode customize prompts, for each episode:

1. **Open NotebookLM** → "+ New notebook" (or use existing per-book notebook)
2. **Sources panel** → "+ Add source" → "Upload from file" → select the file
   listed in the **Upload** column of the Episode list
3. **Customize panel** (top right) → "Customize" → paste the entire contents of
   the **Customize** file
4. The customize prompt already declares: length cue, host pairing, format
   (deep_dive vs debate), focus areas, pronunciation block, tone constraints
5. **Generate** → ~10–15 min for NotebookLM to render audio
6. **Download** the MP3 → save at `audio/EP##-<slug>.mp3`
7. **Transcribe** via `python3 scripts/podcast/transcribe_episode.py`
   → drops at `transcripts/EP##-<slug>.transcript.txt`
8. **Audit** via `python3 scripts/podcast/audit_transcript.py <BOOK_DIR> EP##-<slug>`
   — catches Arabic pronunciation drift, missing phonetic cues, fabricated quotes
9. If audit flags issues: edit `pronunciation.md` overrides → re-paste customize
   prompt → re-generate

---

## Next step

Review the **Length tier**, **Essentiality recommendations**, **Episode list**,
and (if shown) **Source-chapter → episode map**.

If everything looks correct: `python3 scripts/podcast/orchestrate_book.py --resume degrees-of-excellence`

If an episode's segmentation, title, format, or host_dynamic needs fixing: edit
the relevant `chapter-contracts/<slug>.yml` and `chapters/ch##[a-z]?-<slug>.txt`,
then re-invoke `--resume`. The orchestrator detects the change and re-validates.

If the tier choice is wrong: edit every `chapter-contracts/<slug>.yml` to
the desired `length_target`, then re-invoke `--resume`.

If you want to change unit mode (chapter ↔ section ↔ auto), reset Phase 0d:
  `python3 scripts/podcast/orchestrate_book.py --resume degrees-of-excellence --retry-phase 0d`
(then edit `_system/orchestrator-state.json` `config.unit_mode` before resuming)
