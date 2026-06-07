# Series Plan — Journey To The West Vol 1

**Book slug:** `journey-to-the-west-vol-1`
**Branch:** `journey-to-the-west-vol-1`
**Generated:** 2026-06-06T22:42Z
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
| 1 | Birth of the Stone Monkey | 7704 | extended | **narrative** | core | `chapters/ch01-birth-of-the-stone-monkey.txt` | `episodes/EP01-birth-of-the-stone-monkey.txt` (TBD post-0g) | "target a 30–45 minute conversation" | storyteller + curious_listener |
| 2 | The Secret Word at the Third Watch | 7621 | extended | **narrative** | core | `chapters/ch02-the-secret-word-at-the-third-watch.txt` | `episodes/EP02-the-secret-word-at-the-third-watch.txt` (TBD post-0g) | "target a 30–45 minute conversation" | storyteller + curious_listener |
| 3 | The Four Seas and a Thousand Mountains Bow in Submission | 7798 | extended | **narrative** | core | `chapters/ch03-four-seas-bow-in-submission.txt` | `episodes/EP03-four-seas-bow-in-submission.txt` (TBD post-0g) | "target a 30–45 minute conversation" | storyteller + curious_listener |
| 4 | The Heavenly Stable and the Great Sage Equal to Heaven | 7314 | extended | **narrative** | core | `chapters/ch04-the-heavenly-stable-and-the-great-sage.txt` | `episodes/EP04-the-heavenly-stable-and-the-great-sage.txt` (TBD post-0g) | "target a 30–45 minute conversation" | storyteller + curious_listener |
| 5 | The Great Sage Plunders the Peaches and Steals the Elixir | 7184 | extended | **narrative** | core | `chapters/ch05-the-great-sage-plunders-the-peaches.txt` | `episodes/EP05-the-great-sage-plunders-the-peaches.txt` (TBD post-0g) | "target a 30–45 minute conversation" | storyteller + curious_listener |

### Source-chapter → episode map

| source chapter | source title | episode(s) | split reason |
|---|---|---|---|
| 1 | The Stone Egg of Flower-Fruit Mountain and the Magical Monkey King | ch01-birth-of-the-stone-monkey.txt | fits extended tier (5,500–9,500w); single continuous narrative arc (cosmology → stone-monkey birth → coronation → mortality-awakening → quest → naming as Sun Wukong); no natural mid-chapter break |
| 2 | The Secret Word at the Third Watch | ch02-the-secret-word-at-the-third-watch.txt | single-arc chapter; one extended episode preserves the doctrinal-arsenal installation (Golden Elixir formula, Three Calamities, 72 transformations, Somersault Cloud, Body-Outside-the-Body) as one continuous transmission, with the return-home combat as the first test |
| 3 | The Four Seas and a Thousand Mountains Bow in Submission | ch03-four-seas-bow-in-submission.txt | single-arc chapter; one extended episode preserves the escalating-arming trajectory (bamboo spears → Aolai armory → As-You-Will cudgel + four-sea armor → ten-thousand-fathom display → strike from the Registers of Life and Death → twin memorials → Great White Planet's amnesty edict) as one continuous installation of weapon, armor, cosmology, and the first imperial notice |
| 4 | A Stable-Keeper's Title Cannot Content Him; The Great Sage Raises Heaven's Banner | ch04-the-heavenly-stable-and-the-great-sage.txt | single-arc chapter; one extended episode preserves the policy-failure-and-reformulation trajectory (Southern Gate audience → BanMaWen at the Imperial Stable → unranked-office discovery → revolt → four-word banner GREAT SAGE EQUAL TO HEAVEN → Mighty Magic Spirit's broken ax → Nezha's six arms matched and wounded → Great White Planet's second descent with the empty-title doctrine → Mansion of the Great Sage beside the Garden of Immortal Peaches) as one continuous installation of the title, the canonical Heavenly King Li Jing / Nezha adversaries, and the policy whose collapse will drive the rest of Volume 1 |
| 5 | The Great Sage Plunders the Peaches and Steals the Elixir; The Hosts of Heaven March to Seize the Monster | ch05-the-great-sage-plunders-the-peaches.txt | single-arc chapter; one extended episode preserves the policy-collapse trajectory (empty-title idleness → Peach Garden warden → secret peach-eating → seven robed maidens and body-fixing spell → Barefoot Immortal gulled → Jade Pool plundered with sleep-insects → wrong turn into Tushita Palace and five gourds of Nine-Cycle Golden Elixir → flight to Flower-Fruit Mountain → cascading reports → hundred-thousand-soldier muster with the heaven-and-earth net → Nine Luminaries beaten back → melee from the hour of the Dragon to sundown with cave-kings captured → thousand-and-a-hundred-Great-Sages finish → night-watch ringing the mountain) as one continuous installation of the havoc-in-Heaven triad and the canonical adversary roster that drives the rest of Volume 1 |

---

## Audit-trail-only sections (no human review)

### Audience (orchestrator config default)
A general adult listener meeting the *Journey to the West* — Wu Cheng'en's sixteenth-century Ming-dynasty fantastical novel — for the first time. No prior familiarity with Chinese literature, Daoist cosmology, or Buddhist-Daoist syncretism is required. The episode is the novel's opening chapter and serves as the listener's gateway into the cosmos, the geography, and above all the protagonist: the stone-born monkey who becomes the Handsome Monkey King and, by the chapter's close, Sun Wukong — Monkey Awakened to Emptiness. The listener should leave the episode with the felt shape of the world (the twelve-epoch cycle, the four continents, Flower-Fruit Mountain rising out of the Eastern Sea, the magic stone that catches sun and moon for an age and finally splits open), with the figure of the stone monkey vivid enough to recognize for the rest of the series (the bound through the waterfall onto the iron bridge, the leadership claim that follows, the three-hundred-year reign), and with the awakening that drives the whole novel: the sudden tears at a banquet, the recognition that King Yama works in secret on every life, the gibbon's naming of the three classes that escape death — Buddhas, Immortals, Holy Sages — and the resolve to find them. The voyage that follows (a pine-bough raft across the Eastern Sea, eight or nine years through the Southern Continent of Jambu, a second raft to the Western Continent of Cattle-Offering, a song heard in a forest, a woodcutter who is not the immortal but knows where the immortal lives) carries the listener to the Cave of the Slanting Moon and Three Stars, to the Patriarch Subodhi, and to the moment a stone-born creature is given a surname and a Dharma-name — Sun Wukong — that will travel with him through everything to come.

### Angle (orchestrator config default)
faithful_narrative

### Host dynamic (AI-selected per chapter)
| Chapter | Host dynamic | Rationale |
|---|---|---|
| `birth-of-the-stone-monkey` | storyteller + curious_listener | The storyteller voices the source's narration — the cosmology, the rhapsodies, the descriptive set-pieces, the master-disciple exchanges; the curious_listener voices the listener-on-the-couch's natural questions (why does the cosmology run in twelves? what is a *zhang*? why does the Patriarch drive him out at first? what does 'Awakened to Emptiness' mean as a name?). The host_dynamic from series-config is preserved; this chapter's split is the default series configuration with no per-chapter override needed.
 |
| `the-secret-word-at-the-third-watch` | storyteller + curious_listener | The storyteller voices the source's narration — the rhetorical set-pieces of the lecture-platform marvel, the third-watch verse, the oral formula of the Golden Elixir, the warnings of the Three Calamities, the descriptions of the Fiend King and the Source-Pit Mountain. The curious_listener voices the natural questions the source itself prompts: why does the Patriarch use riddles? what is the Golden Elixir tradition the chapter is drawing on? why exactly are there three calamities and why thunder/fire/wind? what is the *Body-Outside-the-Body* method actually proposing about the spirit and the eighty-four thousand hairs? The series-config host_dynamic carries over unchanged.
 |
| `four-seas-bow-in-submission` | storyteller + curious_listener | The storyteller voices the source's narration — the sand-flinging wind-raid rhapsody, the depths-of-the-sea-treasury scene, the ten-thousand-fathom transformation, the two memorials in their full bureaucratic ceremonial language, and the Great White Planet's consultative speech. The curious_listener voices the natural questions the source itself prompts: who are the Four Dragon Kings and the Ten Kings of the Underworld in the Chinese pantheon? what is the Heavenly-River-anchoring rod of the Great Yu? why is amnesty-and-recruitment offered rather than divine troops? The series-config host_dynamic carries over unchanged from Episodes 1 and 2.
 |
| `the-heavenly-stable-and-the-great-sage` | storyteller + curious_listener | The storyteller voices the source's narration — the rhapsody of the Numinous Empyrean Hall, the inventory of the thousand heavenly horses, the description of the armed Monkey King, the set-piece of Nezha's six weapons, the combat verse, and the Great White Planet's "empty title" pivot. The curious_listener voices the natural questions the source itself prompts: who is the Heavenly King Virūḍhaka and why does he bar the Southern Gate? why is "unranked" the lowest of the low rather than the highest? who is Nezha and what are the six weapons of his three-heads-and- six-arms transformation? what is an "office without emolument" and why does the Jade Emperor accept the elegance of it? The series-config host_dynamic carries over unchanged from Episodes 1, 2, and 3.
 |
| `the-great-sage-plunders-the-peaches` | storyteller + curious_listener | The storyteller voices the source's narration — the rhapsody of the Peach Garden, the inventory of three thousand six hundred trees, the description of the Jade Pool feast, the verse of the Barefoot Immortal's approach, the hundred-thousand-soldier muster verse, the great-melee verse, and the closing couplet. The curious_listener voices the natural questions the source itself prompts: who is Xu Jingyang and why does the Jade Emperor act on his warning? what is the difference between trees that ripen in three thousand, six thousand, and nine thousand years? who is the Queen Mother and why are the seven maidens robed in seven colors? what is a body-fixing spell, and why does it last a full day and night? who is the Barefoot Great Immortal and why is the Hall of Universal Brightness a credible cover? what is the Nine-Cycle Golden Elixir, and why is eating five gourds of it a calamity bigger than the sky? what are the eighteen frames of the heaven-and-earth net, and what is the hour of the Dragon? The series-config host_dynamic carries over unchanged from Episodes 1, 2, 3, and 4.
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

If everything looks correct: `python3 scripts/podcast/orchestrate_book.py --resume journey-to-the-west-vol-1`

If an episode's segmentation, title, format, or host_dynamic needs fixing: edit
the relevant `chapter-contracts/<slug>.yml` and `chapters/ch##[a-z]?-<slug>.txt`,
then re-invoke `--resume`. The orchestrator detects the change and re-validates.

If the tier choice is wrong: edit every `chapter-contracts/<slug>.yml` to
the desired `length_target`, then re-invoke `--resume`.

If you want to change unit mode (chapter ↔ section ↔ auto), reset Phase 0d:
  `python3 scripts/podcast/orchestrate_book.py --resume journey-to-the-west-vol-1 --retry-phase 0d`
(then edit `_system/orchestrator-state.json` `config.unit_mode` before resuming)
