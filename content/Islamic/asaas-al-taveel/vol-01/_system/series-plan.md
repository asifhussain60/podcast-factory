# Series Plan — Asaas Al Taveel Vol 01

**Book slug:** `vol-01`
**Branch:** `Islamic/asaas-al-taveel`
**Generated:** 2026-06-09T08:55Z
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
| 1 | What Ismaili Interpretation Is | 6320 | extended | **deep_dive** | core | `chapters/ch01-what-ismaili-interpretation-is.txt` | `episodes/EP01-what-ismaili-interpretation-is.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 2 | The Call to Inner Meaning | 5838 | extended | **deep_dive** | core | `chapters/ch02-the-call-to-inner-meaning.txt` | `episodes/EP02-the-call-to-inner-meaning.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 3 | The Four Limits of the Shahada | 6107 | extended | **deep_dive** | core | `chapters/ch03-the-four-limits-of-the-shahada.txt` | `episodes/EP03-the-four-limits-of-the-shahada.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 4 | Adam, the Tree, and the Pact of Iblis | 6463 | extended | **deep_dive** | core | `chapters/ch04-adam-the-tree-and-iblis-pact.txt` | `episodes/EP04-adam-the-tree-and-iblis-pact.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 5 | The Two Parties and the Line to Noah | 6265 | extended | **deep_dive** | core | `chapters/ch05-two-parties-and-the-line-to-noah.txt` | `episodes/EP05-two-parties-and-the-line-to-noah.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |

### Source-chapter → episode map

| source chapter | source title | episode(s) | split reason |
|---|---|---|---|
| 1 | Editor's Introduction (Arif Tamir, 1960) | ch01-what-ismaili-interpretation-is.txt | one-to-one mapping: the editor's introduction is a single continuous expository sweep laying down the basic Ismaili interpretive vocabulary (ta'wil vs tafsir, al-Natiq vs al-Asas, Da'a'im al-Islam vs Asas al-Ta'wil) that the six following Speaker-Prophet chapters use without re-definition; the slice carries one episode at the extended tier with no internal seam justifying a split |
| 2 | Author's Introduction and the Chapter on Faith (al-Nu'man) | ch02-the-call-to-inner-meaning.txt | merged two short adjacent source sections (Author's Introduction ~2,999 words + Chapter on Faith ~2,116 words = 5,115 source words) into one episode because they share one continuous arc in al-Nu'man's voice — the introduction frames why the inner-counterpart book had to be written and stages the pedagogy (suckling parable, Sadiqi "seven faces" warrant, naming of Asas al-Ta'wil as foundation-of-the-hidden paralleling Da'a'im al-Islam as foundation-of-the-apparent), and the Faith chapter opens the actual doctrinal work at the shahada because al-Nu'man's structural thesis is that the testimony at its first utterance already contained the whole sacred law including walaya; merged 5,115 source words land at 5,649 chapter words inside the extended tier band; no internal seam justifies a split since both sections together form the one-arc entrance to the book |
| 3 | Exposition of the Testimony of Divine Oneness | ch03-the-four-limits-of-the-shahada.txt | one_episode_single_arc |
| 4 | Chapter One: Adam and Idris (closing into Chapter Two opening) | ch04a-adam-the-tree-and-iblis-pact.txt, ch05b-two-parties-and-the-line-to-noah.txt | split_on_doctrinal_seam_at_repentance |

---

## Audit-trail-only sections (no human review)

### Audience (orchestrator config default)
Thoughtful adult readers approaching the Ismaili science of inner interpretation (ta'wil) for the first time through al-Nu'man ibn Hayyun's Asas al-Ta'wil — listening for the basic vocabulary they will need to walk into the six Speaker-Prophet chapters that follow, and for the editor Arif Tamir's own framing of why this 10th-century Fatimid manuscript was held in private custody for a thousand years before its 1960 Beirut printing.

### Angle (orchestrator config default)
faithful_exposition

### Host dynamic (AI-selected per chapter)
| Chapter | Host dynamic | Rationale |
|---|---|---|
| `what-ismaili-interpretation-is` | curious_mind + scholar_companion |  |
| `the-call-to-inner-meaning` | curious_mind + scholar_companion | The curious_mind voices the listener who is meeting the author's project for the first time and asking the obvious questions (why two books? why start with milk? what does it mean that the shahada contained everything?); the scholar_companion supplies the textual evidence — the Qur'anic verses al-Nu'man cites, the Ja'far al-Sadiq sayings he relies on, the editor's footnote tradition that frames the manuscript.
 |
| `the-four-limits-of-the-shahada` | curious_mind + scholar_companion | The curious_mind voices the listener encountering the four-limits diagram for the first time and asking the obvious questions (why four words = four limits? what does "Pen" mean if not a reed? how does the count get from four to seven to twelve to nineteen?); the scholar_companion supplies the textual scaffolding — the creation hadith, the Qur'anic citations al-Nu'man threads through the architecture, the al-Sadiq sayings on Islam-inside- faith and faith-as-action, and the editor's footnoted glosses on the Ismaili technical vocabulary (Harams, al-Bab, al-Abdal, du'at of the jaza'ir).
 |
| `adam-the-tree-and-iblis-pact` | curious_mind + scholar_companion | The curious_mind voices the listener encountering the inner reading of Adam's story for the first time and asking the obvious questions (why isn't this just the Genesis story? what does "the tree is the Master of the Resurrection" actually mean? why is Eve called Adam's hujja?); the scholar_companion supplies the textual scaffolding — the Qur'anic verses al-Nu'man threads through, the al-Sadiq hadith from the Father of Imams about the angels' inner thought, the language-Arab examples on what "speech" of God means, and the doctrinal framing of al-ta'yid, the four-limits architecture already laid in chapter three, and the Sahib al-Qiyama pivot at the heart of the chapter.
 |
| `two-parties-and-the-line-to-noah` | curious_mind + scholar_companion | The curious_mind asks the questions a listener arriving from the fall would ask (so wait — Adam is still the caliph after the fall? what actually happened to the wheat-tree story I grew up with? why is the lineage so detailed all of a sudden?); the scholar_ companion supplies the Qur'anic strings that name the two parties, the named converts (Ka'b al-Ahbar, Abdullah ibn Salam) al-Nu'man traces the apocrypha back to, the five-upper-and-five-lower-limits chain from the Prophetic hadith on Jibril's transmission, and the Genesis-style chronology from Adam's descent down to the year of the flood that the editor's note provides.
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

If everything looks correct: `python3 scripts/podcast/orchestrate_book.py --resume vol-01`

If an episode's segmentation, title, format, or host_dynamic needs fixing: edit
the relevant `chapter-contracts/<slug>.yml` and `chapters/ch##[a-z]?-<slug>.txt`,
then re-invoke `--resume`. The orchestrator detects the change and re-validates.

If the tier choice is wrong: edit every `chapter-contracts/<slug>.yml` to
the desired `length_target`, then re-invoke `--resume`.

If you want to change unit mode (chapter ↔ section ↔ auto), reset Phase 0d:
  `python3 scripts/podcast/orchestrate_book.py --resume vol-01 --retry-phase 0d`
(then edit `_system/orchestrator-state.json` `config.unit_mode` before resuming)
