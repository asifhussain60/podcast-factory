# Series Plan — The Master And The Disciple

**Book slug:** `the-master-and-the-disciple`
**Branch:** `Islamic/the-master-and-the-disciple`
**Generated:** 2026-06-07T22:09Z
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
| — | — | — | All episodes flagged `core`. No essentiality concerns. |

### Episode list

Columns:
- **Format** — `deep_dive` (Mentor+Student exposition) | `debate` (named voices clash + arbiter) | `narrative` (historical/biographical) | `interview` (Q&A)
- **Essential** — `core` | `optional` | `bonus` | `skip` (see Essentiality recommendations above)
- **Upload** — file to drop in NotebookLM's *Sources* panel
- **Customize** — file whose contents go in NotebookLM's *Customize* box (written by Phase 0g)
- **Length cue** — what to declare in the customize prompt's opening directive
- **Hosts** — host pairing for NotebookLM's customize prompt

| # | Title | Words | Tier | Format | Essential | Upload (NotebookLM source) | Customize | Length cue | Hosts |
|---|---|---|---|---|---|---|---|---|---|
| 1 | The True Sources of Knowledge | 6349 | extended | **deep_dive** | core | `chapters/ch01a-true-sources-of-knowledge.txt` | `episodes/EP01-true-sources-of-knowledge.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 2 | Spiritual Symbols and the Architecture of Creation | 6279 | extended | **deep_dive** | core | `chapters/ch02b-spiritual-symbols-and-the-architecture-of-creation.txt` | `episodes/EP02-spiritual-symbols-and-the-architecture-of-creation.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 3 | Knowledge versus Action | 5813 | extended | **deep_dive** | core | `chapters/ch03a-knowledge-versus-action.txt` | `episodes/EP03-knowledge-versus-action.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 4 | The Disciple Becomes Master | 6726 | extended | **narrative** | core | `chapters/ch04b-the-disciple-becomes-master.txt` | `episodes/EP04-the-disciple-becomes-master.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Narrator + Companion |
| 5 | Unity, Justice, and the Living Witness | 6729 | extended | **debate** | core | `chapters/ch05-unity-justice-and-the-living-witness.txt` | `episodes/EP05-unity-justice-and-the-living-witness.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Advocate + Arbiter |

### Source-chapter → episode map

| source chapter | source title | episode(s) | split reason |
|---|---|---|---|
| 1 | The True Sources of Knowledge and the Architecture of Creation | ch01a-true-sources-of-knowledge.txt, ch02b-spiritual-symbols-and-the-architecture-of-creation.txt | SPLIT into 2 sections: Part One (~4,330w, narrative arc — three thanks, scholar's search, design-of-creation sermon, etiquette of learning, covenant of allegiance) becomes ep1; Part Two (~3,161w, cosmological scaffolding — root principles, seven-and-twelve schema, Bismillah seal, spiritual hierarchy mirrored in heavens/earth, Air as loftiest symbol, the Instance beyond) becomes ep2. The 7,801w source exceeds the 6,000w/episode ceiling, so a single-episode rendering is impossible; each part lands inside the extended-tier band individually. The split also honors the source's own structural seam — Part One ends on the oath of allegiance, Part Two opens on "Having taken the covenant, the disciple is taught the architecture of creation." |
| 2 | Knowledge versus Action and the Disciple Becomes Master | ch03a-knowledge-versus-action.txt, ch04b-the-disciple-becomes-master.txt | SPLIT into 2 sections: Part Three (Knowledge versus Action, ~3,268w in source) covers the three-level zahir/batin/batin-al-batin teaching (spine of the book per MISSING 7), the hawl/quwwa esoteric unfolding, the Yusuf and king's-vision readings, the fasiq/kafir/mu'min verdict on the union of inner and outer, divine justice in inner faculties, and the disciple's five-portion purification of possessions ending on his collapse into 'ishq. Part Four (The Disciple Becomes Master, ~3,319w in source) covers the seven-day rebirth/naming ceremony, the esoteric Tawaf as gravitational binding to the Imam, the six parting counsels, the conversion of al-Bakhtari by the forty-years syllogism, the arrival of Abu Malik (Ka'b al-Ahbar), the kasra/makasir cup-emptying with the 'ilm/ma'rifa distinction, the follow-the-moon restoration, and the description of religion as the rope from heaven to earth — opening the way for episode 5. Split is required by the 6000w/episode ceiling: 6,587w / 1 episode = 6,587w/episode exceeds ceiling. Each authored section lands inside the band at 5,584w and 5,505w respectively. |
| 3 | Unity, Justice, and the Living Witness | ch05-unity-justice-and-the-living-witness.txt | Source Part Five stands alone as a single tight theological syllogism-and-diagnosis arc (unity of Allah beyond names → syllogism of divine justice → necessity of a living Ḥujja → conspiracy formula → unbroken chain with no fatra → concealment typology → path of return → seal as model). At 2,969 source words it falls below the extended tier lower bound; splitting would fracture the syllogism, merging forward would cut the climactic Salih–Abu-Malik debate seam. Accept the single under-band source as one episode brought to 5,980 words through faithful reflective commentary in the established voice. |

---

## Audit-trail-only sections (no human review)

### Audience (orchestrator config default)
Thoughtful adult readers approaching *Kitāb al-ʿĀlim wa al-Ghulām* — *The Book of the Master and the Disciple* — for the first time, who know it as the timeless story of a seeker's quest for true knowledge and the process through which he gradually achieved it. The book is by Sayyidinā Jaʿfar ibn Manṣūr al-Yaman (sai-yi-DEE-nah Jaʿa-far ibn al-man-SOOR al-Ya-man), a very high-ranking *dāʿī* (daa-ee) and a *bāb al-abwāb* — a master of *taʾwīl* (tah-WEEL), esoteric interpretation — who guides the reader to the path of the friends of Allah (al-LAH), the chosen people who possess the spiritual knowledge that makes them spiritually eternal. Episode one walks the opening narrative arc that establishes WHY this knowledge must be transmitted through a chain of intermediaries at all. A nameless group of the faithful and a group of *duʿāt al-dīn* (dua'at ad-deen) approach one of their scholars to ask three things at once: how to express gratitude for the call, the knowledge, and the practice. The Master answers with the three-stage spiritual path — *balwā* (BAL-wah) → *hudā* (hu-DAH) → *taqwā* (tak-WAH) — and then narrates the story of a Persian seeker who, after his thirst for knowledge led him through mirage after mirage, was found by a teacher and made into one of the great scholars of *Sīnāʾ* (SEE-nigh); how that scholar, hearing his own master repeat *the most excellent of deeds is giving life to the dead*, set out across Arab and non-Arab lands looking for a worthy disciple; how at the far reaches of *al-Jazīra* (al-ja-zee-rah) he found a group of seekers discussing religion without guidance; how the youngest of them — best in character, his intellect complete and his heart awakened by reflection — followed him to his inn; how the Master delivered the great glorification of Allah, the design-of-creation sermon that names *ẓāhir* (ZAA-hir) and *bāṭin* (BAA-tin) as a cosmic preservation principle rather than a textual trick; how the etiquette of seeking knowledge maps onto the Qurʾanic triad of hearing, sight, and heart; and how, after the boy's period of trial, the Master imposed five conditions and took the *ʿahd sharīf* — the noble oath of allegiance — that turns ordinary religious action sacred. The episode ends where the disciple's tears do, on the night he knew with certainty that he had become a member of the *Ḥizb Allāh* (HIZB ahl-LAH), the party of Allah.

### Angle (orchestrator config default)
faithful_exposition

### Host dynamic (AI-selected per chapter)
| Chapter | Host dynamic | Rationale |
|---|---|---|
| `true-sources-of-knowledge` | curious_mind + scholar_companion |  |
| `spiritual-symbols-and-the-architecture-of-creation` | curious_mind + scholar_companion |  |
| `knowledge-versus-action` | curious_mind + scholar_companion |  |
| `the-disciple-becomes-master` | narrator + companion |  |
| `unity-justice-and-the-living-witness` | advocate + arbiter | Two voices: advocate (Ṣāliḥ) carries the source's case for the chain through demolition → syllogism → conspiracy → *fatra* refutation → concealment typology → path of return; arbiter (Abu Malik) presses the opposing community's strongest counter-arguments, concedes step by step as the syllogism advances, and at the close turns to Allah in repentance. The arbiter's concession carries the resolution.
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

If everything looks correct: `python3 scripts/podcast/orchestrate_book.py --resume the-master-and-the-disciple`

If an episode's segmentation, title, format, or host_dynamic needs fixing: edit
the relevant `chapter-contracts/<slug>.yml` and `chapters/ch##[a-z]?-<slug>.txt`,
then re-invoke `--resume`. The orchestrator detects the change and re-validates.

If the tier choice is wrong: edit every `chapter-contracts/<slug>.yml` to
the desired `length_target`, then re-invoke `--resume`.

If you want to change unit mode (chapter ↔ section ↔ auto), reset Phase 0d:
  `python3 scripts/podcast/orchestrate_book.py --resume the-master-and-the-disciple --retry-phase 0d`
(then edit `_system/orchestrator-state.json` `config.unit_mode` before resuming)
