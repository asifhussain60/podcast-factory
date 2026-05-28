# Kashkole Knowledge Corpus — Three Databases

All three SQL Server databases live on the home server at `192.168.1.158`.
The SQL dump files are stored here locally for reference but are gitignored
(they are 15 MB, 29 MB, and 724 MB respectively).
**What is committed:** this README, the query files at `scripts/kashkole/queries/`,
the extracted samples at `extracted/`, and the `topic-type-map.json` schema index.

---

## Connection details

| Profile  | Server          | Database       | Use for                |
|----------|-----------------|----------------|------------------------|
| AHHOME   | 192.168.1.158   | KQUR           | Quran + etymology + hadith |
| AHHOME   | 192.168.1.158   | KASHKOLE       | Urdu/English knowledge topics |
| AHHOME   | 192.168.1.158   | KSESSIONS_DEV  | Delivered lecture sessions |

Open queries via the VS Code MSSQL extension (`ms-mssql.mssql`). The
AHHOME connection profile is already saved. Select the correct database
from the status bar or add `USE <DB>;` at the top of each query file.

---

## Database 1: KQUR (15 MB)

**What it is:** A structured Quran reference database with English translations,
Arabic etymology (roots → derivatives), and a hadith collection with narrator chains.

**Key tables:**

| Table | Contents |
|---|---|
| `QuranAyats` | 6,236 ayahs with Arabic unicode, two English translations (Pickthall + Asad), Urdu, phonetic |
| `QuranSurahs` | 114 surahs with English names and meanings |
| `Roots` | Arabic root words with English/Arabic meanings and transliteration |
| `Derivatives` | Forms derived from each root — grammar tag, definition, English meaning |
| `Ahadees` | Hadith with Arabic + English text, narrator, category, reference |
| `AhadeesSubjectCategories` | Thematic categories for hadith |
| `Narrators` | Narrator metadata (Arabic + English name) |

**Primary use in the intelligence pipeline:**
- Augmentation phase: inject canonical verse text + translation when a chapter cites a Quran ayah
- Style rewrite: resolve Arabic terms inline — Root → Derivative → MeaningEnglish
- Enrichment: cross-reference chapter themes to relevant ayahs via thematic search

**Query files:**
- `kqur-01-inventory.sql` — counts + surah list
- `kqur-02-ayat-lookup.sql` — retrieve specific verse(s) by surah + ayat number
- `kqur-03-word-etymology.sql` — look up root + all derivatives by English keyword
- `kqur-04-thematic-search.sql` — keyword search across both English translations

---

## Database 2: KASHKOLE (724 MB — bulk is binary image blobs; text content is much smaller)

**What it is:** The master Urdu-unicode knowledge management system — Asif's curated
collection of Ismaili/Islamic theological topics, organized as Binders (books)
→ Chapters → Topics → Content. Topics carry the full rendered unicode text (Arabic +
Urdu + English mixed), linked Quran ayat cross-references, glossary terms, and flashcards.

**Key tables:**

| Table | Contents |
|---|---|
| `Binders` | Book-level containers (the "shelves") |
| `BinderChapters` | Chapter membership within a binder |
| `Chapters` | Named chapters with descriptions |
| `ChapterTopics` | Topic membership within a chapter |
| `Topics` | Master topic registry — name (Urdu), English name, type, flags (IsEnglish, IsArabic, HasSimpleVersion) |
| `TopicDataUnicode` | The actual Unicode content per topic (nvarchar max) — this is the primary text corpus |
| `TopicAyats` | Quran ayahs linked to each topic (surah + ayat numbers) |
| `TopicFlashcards` | Q&A flashcards per topic |
| `TopicGlossaries` | Glossary term → topic links |
| `Glossary` | Standalone glossary with definitions |
| `DeeniTermGroup` / `DeeniTermGroupElements` | Taxonomy of religious/technical terms |
| `TopicAnnotations` | User annotations per topic |

> **Note on size:** The 724 MB is almost entirely from `TopicData.TopicImage` (binary image blobs, `[image]` type column). The `TopicDataUnicode` text content extracts to a fraction of that. A pure-text SQLite mirror is feasible and would be small enough for offline use.

**Primary use in the intelligence pipeline:**
- Source material for future book/series generation: Binders = potential series, Chapters = seasons, Topics = episodes
- Thematic enrichment: find all topics matching a chapter's theological theme
- Glossary: canonical definitions of Deeni terms for inline glossary injection

**Query files:**
- `kashkole-01-inventory.sql` — counts + binder list
- `kashkole-02-topic-search.sql` — keyword search by English topic name
- `kashkole-03-get-topic.sql` — full content + cross-refs for a specific topic ID

---

## Database 3: KSESSIONS_DEV (29 MB)

**What it is:** Asif's delivered lecture sessions in English, organized as
Groups → Categories → Sessions → SessionTranscripts. SessionTranscripts contains
HTML-formatted content with structured CSS classes marking esoteric content,
Quran widgets, hadith blocks, poetry, and privileged material.

**Key tables:**

| Table | Contents |
|---|---|
| `Groups` | Top-level series (e.g. Wise Reminder, Asaas Al-Taveel, Ikhwan As-Safa) |
| `Categories` | Sub-categories within a group |
| `Sessions` | Individual sessions with name, date, category |
| `SessionTranscripts` | The full HTML content per session (343 rows; 109 with substantive content) |

**CSS class taxonomy (protected — never treat as noise):**

| Class | Content type |
|---|---|
| `esotericBlock`, `esotericData`, `esoteric-header` | Esoteric / ta'wil interpretation |
| `previligedBlock`, `previligedData` | Privileged inner-circle content |
| `quranWidget`, `quran-ayats`, `ayah-arabic` | Quranic verses |
| `poetry-section`, `poetry-couplet` | Poetry |
| `hadees-widget`, `ks-ahadees-container` | Hadith |
| `anecdote`, `example` | Teaching anecdotes |

**Group map:**

| GroupID | Name | Sessions |
|---|---|---|
| 3 | Wise Reminder | 44 |
| 4 | Zarbul Hikam | — |
| 6 | Kitab Rahat Al-Aql | — |
| 7 | Spiritual Ethos Of Ali | — |
| 12 | Master and the Disciple | — |
| 17 | Ikhwan As-Safa (Brethren Of Purity) | — |
| 18 | Asaas Al-Taveel | 32 |
| 20 | RELIGIOUS BOOKS | — |

**Style corpus for I0b rewrite pass (confirmed):**
- G3 Wise Reminder (44 sessions)
- G17 Ikhwan As-Safa, Category 51 Arithmetic only (14 sessions)
- G18 Asaas Al-Taveel (32 sessions)
- Session ID 2346 "Necessity Of Imam" (Isbat al-Imamah)

**Query files:**
- `01-inventory.sql` — groups + categories + session counts
- `02-style-corpus-sessions.sql` — sessions used as style training corpus
- `03-get-transcript.sql` — retrieve full HTML for a single session
- `04-search-by-name.sql` — search sessions by name keyword

---

## Intelligence pipeline integration (forward plan)

See `_workspace/plan/refactor/plan.md` Wave I steps I0a, I0b, I2 for the
formal plan entries. Summary:

| Step | DB | How it's used |
|---|---|---|
| I0a (annotation) | KSessions | Noise type baseline from delivered sessions |
| I0b (style rewrite) | KSessions | Style corpus extraction for Asif's teaching voice |
| I2 (noise router) | All 3 | Protected content class list informs "never strip" rules |
| I3 (tradition KB) | KQUR + Kashkole | Batch extraction → atoms into SQLite knowledge base |
| Enrichment (Phase 0e) | KQUR | Canonical verse text + translation injection |
| Future authoring | Kashkole | Binders → series generation; Topics → episode seeds |

**MCP server plan (proposed — NOT STARTED):**
A "Source Library" MCP server wrapping all three databases is planned to give
Claude live query access during authoring: `quran_lookup`, `kashkole_topic_search`,
`ksessions_style_fetch`. The server targets the home MSSQL instance initially,
with a SQLite-mirror offline extension path once the text content is extracted.
See the plan entry (to be added to Wave I or as a new Wave J) for the formal spec.
