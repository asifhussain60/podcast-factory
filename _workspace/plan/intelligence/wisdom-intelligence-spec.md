# Kashkole → Intelligence Pipeline: Implementation Recommendation
*For GitHub Copilot. Self-contained. Last updated: 2026-05-26.*

---

## What You Are Building

The **Kashkole corpus** — 122 chapters of Ismaili scholarly text (theology, taʾwīl, jurisprudence, ethics, cosmology) — has been translated and adapted into polished scholarly English. The goal is to feed it into the podcast-factory's **intelligence pipeline** so it becomes a queryable doctrinal knowledge base that enriches future book podcast productions.

This is NOT a podcast series. Kashkole = the substrate. Every future book the pipeline processes will query it for contextual depth.

**Full context document:** `_workspace/wisdom-brief.md` — read §18 first, then §§1–12 for corpus detail.

---

## Architecture You Are Extending

The intelligence pipeline lives in `scripts/podcast/knowledge/`. Three pieces, all scaffold-only (Wave 1 implementation pending):

```
Extractor  → pulls atoms from chapter text → _system/knowledge-atoms-scratch.jsonl
Librarian  → dedupes + merges atoms       → content/knowledge-base/{type}.jsonl
Augmenter  → queries library at authoring → top-K atoms injected into prompts
```

Atom schemas: `scripts/podcast/knowledge/_atom_schemas.py`
Current atom types: `quran`, `hadith` (Wave 1 only — scaffold, not implemented)
Current library: `content/knowledge-base/quran.jsonl`, `hadith.jsonl` (may be near-empty)

---

## What Needs to Be Built (Sequenced)

### Step 1 — Fix the 18 FAIL chapters (pre-requisite for everything)

Gate report at `_workspace/plan/wisdom-gate-report.md` lists 18 chapters with FAIL verdict. Re-adapt + re-challenge each:

```bash
VENV=/Users/asifhussain/PROJECTS/podcast-factory/_workspace/source-library/.venv/bin/python
$VENV -m tools.content_translator adapt-auto wisdom --binder {N} --chapter {M}
$VENV -m tools.content_translator challenge wisdom --binder {N} --chapter {M}
```

Only ingest chapters whose `wisdom-challenger-report.md` verdict is PASS or WARN. Skip FAILs.

---

### Step 2 — Extend `_atom_schemas.py` with the `doctrine` type

Add to `scripts/podcast/knowledge/_atom_schemas.py`:

```python
from typing import Literal

DoctrineGenre = Literal[
    "tawil",        # esoteric Quranic interpretation
    "theology",     # systematic doctrinal exposition
    "jurisprudence",# Islamic law (Daaim al-Islam basis)
    "ethics",       # moral philosophy, adab
    "cosmology",    # mabda wa maad, origin/return
    "narrative",    # prophetic stories, biographical
    "scholarly",    # treatises, academic essays
]

class DoctrineBody(TypedDict, total=False):
    tradition: Literal["ismaili"]
    genre: DoctrineGenre
    binder_id: int           # numeric ID from KASHKOLE DB
    binder_slug: str         # e.g. "tawheed-mubdi-taala"
    chapter_id: int
    chapter_slug: str
    section_ids: list[int]   # section IDs this chunk spans
    chunk_index: int         # 0-based within the chapter
    topic_tags: list[str]    # see binder→tag map below
    text_en: str             # ~500-word adapted English chunk
    quran_refs: list[str]    # ⟪quran S:A⟫ refs in this chunk

# Canonical ID:  doctrine:wisdom:<binder_id>:<chapter_id>:<chunk_index>
# Example:       doctrine:wisdom:24:650:0
# Dedup:         exact-match on canonical ID (no fuzzy needed)
```

Update `AtomType`:
```python
AtomType = Literal["quran", "hadith", "doctrine"]
```

---

### Step 3 — Build `wisdom_ingest_knowledge.py`

Create at: `_workspace/plan/_drivers/wisdom_ingest_knowledge.py`

This is a standalone batch driver — it does NOT go through `orchestrate_book.py`. Logic:

```
For each chapter directory under _workspace/source-library/extracted/wisdom/**/{chapter}/:

  1. Read bundle.yml → get binder_id, chapter_id, binder_slug, chapter_slug
  2. Read wisdom-challenger-report.md → check verdict. Skip if FAIL.
  3. Read adapted-extract.en.md

  LAYER 1 — Quran atoms:
    - Find all ⟪quran S:A⟫ markers
    - For each: extract surrounding paragraph (~150 words) as tafsir_note
    - Emit atom: type="quran", id="quran:S:A", source="wisdom/<binder>/<chapter>",
                 body.tafsir_note=<paragraph>
    - Write to per-chapter scratch JSONL: _system/knowledge-atoms-scratch.jsonl

  LAYER 1 — Hadith atoms:
    - Read adaptation-citations.jsonl
    - For entries where source_work matches a hadith collection: emit hadith atom

  LAYER 2 — Doctrine chunks:
    - Split adapted-extract.en.md on <!-- section N --> markers
    - Group consecutive sections into chunks of ≤600 words (never split mid-section)
    - For each chunk: emit doctrine atom with topic_tags from binder map (§18.7 in brief)
    - chunk_index is 0-based within the chapter

  4. Write all atoms to _system/knowledge-atoms-scratch.jsonl
  5. Call librarian.merge(scratch_path, "content/knowledge-base/")
```

Run with:
```bash
$VENV _workspace/plan/_drivers/wisdom_ingest_knowledge.py
$VENV _workspace/plan/_drivers/wisdom_ingest_knowledge.py --binder 24   # single binder
$VENV _workspace/plan/_drivers/wisdom_ingest_knowledge.py --dry-run      # counts only
```

---

### Step 4 — Implement `librarian.py` for the `doctrine` shard

Extend `scripts/podcast/knowledge/librarian.py` to handle the `doctrine` type:

- Dedup: exact-match on canonical ID (`doctrine:wisdom:<b>:<c>:<i>`)
- On collision: keep existing, append new source reference (same chapter = same atom)
- Output shard: `content/knowledge-base/doctrine.jsonl`
- Index: `content/knowledge-base/_index/doctrine-by-tag.json` — maps each topic tag to list of atom IDs (for fast retrieval)

---

### Step 5 — Extend `augmenter.py` for doctrine (Wave 2)

Extend `scripts/podcast/knowledge/augmenter.py`:

```python
def _get_doctrine_atoms(chapter_text: str, max_atoms: int = 3) -> list[Atom]:
    """
    Topic-tag matching (not citation regex — doctrine atoms have no inline citations).
    1. Extract topic signals from chapter_text:
       - Arabic terms in ⟪ar:…⟫ markers
       - Key theological terms (tawhid, wilaya, tawil, mabda, maad, aql, nafs, etc.)
    2. Load _index/doctrine-by-tag.json
    3. Score each candidate atom: len(intersection(chapter_tags, atom.topic_tags))
    4. Sort by score desc, take top max_atoms (cap at 3 for doctrine — ~300 tokens each)
    5. Filter: exclude atoms whose binder_slug matches current book_slug
    """
```

Injected prompt block format:
```
[PRIOR DOCTRINAL CONTEXT — Kashkole corpus]
Topic: {comma-separated topic_tags}
Source: Kashkole — {binder_slug}, chapter {chapter_slug}
---
{text_en, truncated cleanly at sentence boundary to fit token budget}
---
```

Keep default-disabled (`enable_knowledge_augmenter: false` in series-config) until A/B gate passes.

---

## Database Topic Type Classification (Primary Tagging Signal)

> **This is the canonical topic classification.** Every topic in the KASHKOLE database was manually tagged by the compiler with a `TopicTypeID` from the `Lookup_TopicTypes` table. This is more precise than binder-level inference — use it as the **primary** `topic_tags` source during ingestion. The full mapping is saved at `_workspace/source-library/topic-type-map.json`.

### Lookup_TopicTypes — Full Taxonomy

18 types, manually assigned per topic by the compiler of the corpus:

| TopicTypeID | English Name | Urdu Name | Doctrinal Tags to Apply |
|---|---|---|---|
| 0 | Unknown / Unclassified | نامعلوم | *(no tag — use binder fallback)* |
| 15 | Proof and Evidence | حجت و دلیل | `kalam, argumentation, theology` |
| 17 | Prophetic Hadith | حدیث نبوی | `hadith, sunnah` |
| 18 | Moral Advice and Ethics | نصیحت و اخلاقیات | `ethics, adab, nasihah` |
| 19 | Meaning of Quranic Verse | معنی آیت القرآن | `tawil, quran-exegesis, haqaiq` |
| 20 | Golden Sayings / Aphorisms | اقوال زریں | `aphorisms, wisdom, hikma` |
| 22 | Meaning of Daʿāʾim al-Ṭahāra | معنی دعامۃ الطھارۃ | `tawil, zahir-batin, jurisprudence, daaim` |
| 23 | Hadith Commentary | معنی الحدیث | `hadith, tawil, commentary` |
| 24 | Knowledge of ʿAlī | معرفت علی | `wilaya, ali, imamate` |
| 25 | Meaning of a Story | معنی الحکایۃ | `tawil, narrative, haqaiq` |
| 26 | Meaning of Sharīʿa Command (Taʾwīl) | معنی أمر الشریعۃ | `tawil, zahir-batin, jurisprudence` |
| 27 | Knowledge of the Esoteric (Bāṭin) | علم الباطنۃ | `batin, haqaiq, tawil, esoteric` |
| 29 | Rulings of Sharīʿa | أحکام الشریعۃ | `jurisprudence, sharia, fiqh, daaim` |
| 30 | Knowledge of the Ḥadd | معرفت الحد | `hudud, dawat, hierarchy` |
| 31 | Manqabat (Praise poem) | منقبت | `poetry, manqabat, wilaya` |
| 32 | Virtues / Faḍāʾil | فضائل | `fadail, praise, wilaya` |
| 33 | Religious Terminology | دینی اسطلاح | `terminology, definitions, glossary` |
| 34 | History | تاریخ | `history, biography, tarikh` |

### Distribution in the Corpus

| TopicTypeID | Count | Dominant binders |
|---|---|---|
| 0 (Unknown) | 138 | spread across all binders — use binder fallback tags |
| 26 (Taʾwīl of Sharīʿa) | 15 | Daʿāʾim binders (25, 26, 29) |
| 19 (Quranic Verse meaning) | 13 | Binder 8 (Kalimat Rabbani), 24 (Tawhīd) |
| 18 (Ethics/Advice) | 12 | Binder 27 (Ādāb), 35 (Wise Reminder) |
| 17 (Prophetic Hadith) | 14 | Binders 25, 26, 29 |
| 27 (Esoteric/Bāṭin) | 9 | Binders 1, 23 |
| 22 (Daʿāʾim al-Ṭahāra meaning) | 7 | Binder 25 |

### How to Use This in the Ingestion Driver

```python
# In wisdom_ingest_knowledge.py:

TOPIC_TYPE_TAGS = {
    0:  [],  # Unknown — fall back to binder tags
    15: ["kalam", "argumentation", "theology"],
    17: ["hadith", "sunnah"],
    18: ["ethics", "adab", "nasihah"],
    19: ["tawil", "quran-exegesis", "haqaiq"],
    20: ["aphorisms", "wisdom", "hikma"],
    22: ["tawil", "zahir-batin", "jurisprudence", "daaim"],
    23: ["hadith", "tawil", "commentary"],
    24: ["wilaya", "ali", "imamate"],
    25: ["tawil", "narrative", "haqaiq"],
    26: ["tawil", "zahir-batin", "jurisprudence"],
    27: ["batin", "haqaiq", "tawil", "esoteric"],
    29: ["jurisprudence", "sharia", "fiqh", "daaim"],
    30: ["hudud", "dawat", "hierarchy"],
    31: ["poetry", "manqabat", "wilaya"],
    32: ["fadail", "praise", "wilaya"],
    33: ["terminology", "definitions", "glossary"],
    34: ["history", "biography", "tarikh"],
}

# Load the pre-extracted mapping (no DB access needed):
import json
with open("_workspace/source-library/topic-type-map.json") as f:
    TYPE_MAP = json.load(f)

def get_topic_tags(topic_id: int, binder_tags: list[str]) -> list[str]:
    type_id = TYPE_MAP["topic_type_assignments"].get(str(topic_id))
    type_tags = TOPIC_TYPE_TAGS.get(type_id, []) if type_id is not None else []
    # For TypeID=0 (Unknown), fall back to binder-level tags
    return (type_tags + binder_tags) if type_tags else binder_tags
```

The JSON file at `_workspace/source-library/topic-type-map.json` contains both the taxonomy and all 223 per-topic assignments — **no database access needed** during ingestion.

---

## Ismaili Doctrinal Taxonomy (Cross-Binder)

These are the core intellectual categories that structure Ismaili thought. They cut **across** binders — a chapter on cosmology in binder 1 and a chapter on taʾwīl in binder 8 may both be deeply concerned with ʿaql, for instance. The Augmenter must match on these concepts, not just binder labels.

Use this taxonomy to assign `topic_tags` at chunk level (not just binder level). Multiple categories apply per chunk — assign all that fit.

### Taʾwīl — Esoteric Interpretation (تأویل)
The hermeneutical method that reads beneath the literal surface of Quran, hadith, and religious law to reveal the bāṭin (inner, hidden) meaning. Taʾwīl is not allegory — it is the disclosure of haqīqa (reality) concealed within ẓāhir (outward form). Every religious obligation has a ẓāhir (the act itself) and a bāṭin (its spiritual meaning). The Imām is the sole authoritative interpreter.

- **Primary binder:** 8 (Kalimat Rabbani ki Taweelat) — seven binders of Quranic word-by-word taʾwīl
- **Strong presence:** 34 (Quranic Studies), 1 (Sciences of Origin/Return), 23 (Scholarly Treatises)
- **Cross-binder tag:** `tawil`
- **Related tags:** `batin, zahir, haqiqa, quran-exegesis, esoteric`

### Ḥaqāʾiq — The Esoteric Realities (حقائق)
The body of Ismaili doctrinal truths transmitted through the Imām's authority. Ḥaqāʾiq is the term for the totality of esoteric knowledge — what taʾwīl reveals, what the dāʿī teaches, what the mustajibs (initiates) receive. Closely related to taʾwīl but the broader category: taʾwīl is the method, ḥaqāʾiq is the content.

- **Primary binder:** 1 (Sciences of Origin/Return) — chapters titled with "haqaiq" explicitly
- **Strong presence:** 23 (Scholarly Treatises), 8 (Taʾwīl), 24 (Tawhīd)
- **Cross-binder tag:** `haqaiq`
- **Related tags:** `tawil, ilm, batin, ismaili-doctrine`

### Mabdaʾ wa Maʿād — Origin and Return (مبدأ و معاد)
The foundational cosmological narrative of Ismaili philosophy. **Mabdaʾ** (origin) = the emanation from God through the hierarchy: First Intellect (ʿAql al-Awwal) → Universal Soul (Nafs al-Kullīya) → Seven Intellects → celestial spheres → elemental world. **Maʿād** (return) = the soul's eschatological journey back through the hierarchy to its source. This framework underlies all Ismaili cosmology, ethics, and soteriology — the purpose of religion is to facilitate the return.

- **Primary binder:** 1 (Uloom Mabda wa Maad) — named after this concept; 12 chapters
- **Present in:** 24 (Tawhīd), 23 (Scholarly Treatises), 7 (Sciences)
- **Cross-binder tag:** `mabda-maad`
- **Related tags:** `cosmology, aql, nafs, origin-return, eschatology, emanation`

### ʿAql wa Nafs — Intellect and Soul (عقل و نفس)
The two primary hypostases (emanations) in Ismaili cosmology, derived from Neoplatonic philosophy and Islamicized through the Fatimid daʿwa. **ʿAql** (Universal Intellect) = the first creation; perfect, complete, the model of all being. **Nafs** (Universal Soul) = the second emanation; incomplete, seeking return to ʿAql. The human individual intellect (ʿaql al-juzʾī) participates in the Universal Intellect through initiation and knowledge. The Imām is the ʿAql of his age.

- **Primary binder:** 1 — dedicated chapters: Aql al-Awwal, Saat Uqool (Seven Intellects), Nufus wa Aqsamuha
- **Present in:** 23, 24, 8, 32 (Ghazālī)
- **Cross-binder tag:** `aql-nafs`
- **Related tags:** `aql, nafs, cosmology, intellect, soul, hypostases, mabda-maad`

### Ẓāhir wa Bāṭin — Exoteric and Esoteric (ظاهر و باطن)
The paired opposition that structures all Ismaili religious thought. **Ẓāhir** = the outward, literal, exoteric dimension: sharīʿa, ritual, the text as written. **Bāṭin** = the inward, hidden, esoteric dimension: ḥaqīqa, taʾwīl, the meaning behind the form. The sharīʿa is the shell; the ḥaqīqa is the kernel. Both are obligatory — the bāṭin does not cancel the ẓāhir. This tension appears in virtually every binder.

- **Explicit chapters:** 23 (chapter: "Ẓāhir wa Bāṭin ka Izdiwāj" — Marriage of Exoteric and Esoteric)
- **Cross-binder tag:** `zahir-batin`
- **Related tags:** `sharia, haqiqa, tawil, batin, exoteric, esoteric`

### Wilāya — Sacred Authority of the Imām (ولایة)
The doctrine of the Imām's divinely sanctioned authority (wilāya) — the living, authoritative guide who holds the keys to taʾwīl and ḥaqāʾiq in every age. Wilāya is both a juridical category (Daʿāʾim al-Islām opens with it as the first pillar of Islam) and a cosmological one (the Imām = ʿAql of his epoch). Recognition of the Imām (walāya) is the precondition of all other religious practice.

- **Primary binder:** 19 (Daʿāʾim al-Islām: Wilāya) — juridical treatment
- **Strong presence:** 6 (Imam ʿAlī), 12 (Duʿāt Lives), 24 (Tawhīd — Imām as locus of divine self-disclosure)
- **Cross-binder tag:** `wilaya`
- **Related tags:** `imamate, imam, authority, dawat, duat, wali`

### Ḥudūd — The Hierarchy of the Daʿwa (حدود)
The ranked hierarchy of the Ismaili religious organization (daʿwa): from the Imām down through Nāʾib, Bāb, Ḥujja, Dāʿī, Maʾdhūn, Mustajib. Each rank (ḥadd, pl. ḥudūd) corresponds to a level of initiation and knowledge. The ḥudūd are also cosmic — they map onto the hypostases (ʿAql, Nafs, etc.). Understanding the hierarchy is inseparable from understanding Ismaili cosmology.

- **Primary binders:** 19 (Daʿāʾim: Wilāya), 12 (Duʿāt Lives)
- **Present in:** 1, 23, 24
- **Cross-binder tag:** `hudud`
- **Related tags:** `dawat, duat, dai, hujja, bab, hierarchy, initiation`

### Nāṭiq, Asās, Imām — The Prophetic Hierarchy (ناطق، أساس، إمام)
The three roles that together constitute spiritual authority in each prophetic cycle. **Nāṭiq** (Speaker) = the law-giving Prophet who reveals a new sharīʿa (Adam, Noah, Abraham, Moses, Jesus, Muḥammad — seven Nāṭiqs). **Asās** (Foundation) = the silent, inner partner who receives the bāṭin from the Nāṭiq (e.g., ʿAlī for Muḥammad). **Imām** = the Asās's successors who maintain the bāṭin between Nāṭiqs. Every Kashkole text on prophecy, cosmology, or authority implicitly draws on this tripartite structure.

- **Primary binders:** 18 (Prophet Stories), 6 (Imam ʿAlī), 19 (Wilāya)
- **Present in:** 1, 23, 24, 8
- **Cross-binder tag:** `natiq-asas-imam`
- **Related tags:** `nubuwwa, imamate, prophecy, silsila, cycle`

### Tawḥīd — Divine Oneness (Ismaili sense) (توحید)
Ismaili Tawḥīd is radically apophatic: God (Mubdiʿ) absolutely transcends all attributes, names, and categories — including "existence" and "one." To say "God exists" already limits God. The correct statement is tanzīh (absolute transcendence): God is not even "one" in the numeric sense, because that would imply duality. The ʿAql al-Awwal is the first being, not God. This distinguishes Ismaili theology sharply from Muʿtazilī and Ashʿarī kalām.

- **Primary binder:** 24 (Tawhīd Mubdiʿ Taʿālā) — seven chapters of systematic exposition
- **Present in:** 1, 23, 8
- **Cross-binder tag:** `tawhid`
- **Related tags:** `tanzih, mubdi, transcendence, apophatic, theology, kalam`

### Daʿwa — The Ismaili Mission (دعوت)
The Ismaili religious organization and its propagation activity. The daʿwa (literally "call" or "summons") refers both to the institutional hierarchy and to the act of inviting initiates toward esoteric knowledge. Deeply intertwined with history, biography, and jurisprudence across the corpus.

- **Primary binders:** 12 (Duʿāt Lives), 19 (Wilāya), 27 (Ādāb)
- **Cross-binder tag:** `dawat`
- **Related tags:** `dai, mustajib, hudud, initiation, ismaili-history`

---

## Binder → Topic Tag Map (Revised with Doctrinal Taxonomy)

The tags below include both the binder-level genre label and the cross-binder doctrinal category tags from the taxonomy above. Assign ALL applicable tags at chunk level — a chunk in binder 1 on the First Intellect gets `aql-nafs`, `mabda-maad`, `cosmology`, and `haqaiq`.

| Binder ID | Slug | Doctrinal Categories | Genre Tags |
|---|---|---|---|
| 35 | the-wise-reminder | `zahir-batin, tawil` | `wisdom, spiritual-guidance, ismaili-ethics` |
| 32 | ghazali-kimiya-as-saadah | `aql-nafs, zahir-batin` | `ghazali, ethics, spiritual-discipline, nafs` |
| 36 | islam-iman-ihsan | `wilaya, zahir-batin` | `five-pillars, iman, ihsan, ismaili-practice` |
| 18 | qurani-qisas-al-anbiya | `natiq-asas-imam, haqaiq` | `prophets, quran-narrative, nubuwwa` |
| 25 | daaim-al-islam-taharat | `zahir-batin, hudud` | `tahara, ritual-purity, jurisprudence, daaim` |
| 27 | adab-wa-akhlaq-hasana | `zahir-batin, dawat` | `ethics, adab, moral-conduct, community` |
| 29 | daaim-al-islam-as-sawm | `zahir-batin, hudud` | `sawm, fasting, jurisprudence, daaim` |
| 1 | uloom-mabda-wa-maad | `mabda-maad, aql-nafs, haqaiq, tawhid` | `cosmology, origin-return, emanation` |
| 24 | tawheed-mubdi-taala | `tawhid, haqaiq, natiq-asas-imam` | `divine-oneness, tanzih, theology, kalam` |
| 26 | daaim-al-islam-salawat | `zahir-batin, hudud` | `salat, prayer, jurisprudence, daaim` |
| 19 | daaim-al-islam-wilayat | `wilaya, hudud, dawat` | `imamate, authority, daaim` |
| 8 | kalimat-rabbani-ki-taweelat | `tawil, haqaiq, zahir-batin` | `quran-exegesis, divine-words, esoteric` |
| 23 | muntakhab-ilmi-mazameen | `zahir-batin, aql-nafs, haqaiq, mabda-maad` | `scholarship, treatise, theology, philosophy` |
| 34 | quranic-studies | `tawil, zahir-batin` | `quran, tafsir, basmala, fatiha, arabic-grammar` |
| 6 | ali-ibn-abi-talib | `wilaya, natiq-asas-imam, hudud` | `ali, imamate, khutba, nahjul-balagha` |
| 12 | daat-aur-seerah | `dawat, hudud, wilaya` | `duat, history, biography` |
| 5 | muntakhab-ashaar | `wilaya, dawat` | `poetry, devotional, marsiya` |

**Important:** Ingest ALL binders into the knowledge base — including those excluded from podcast production (34, 6, 12, 5). The podcast-scope exclusions were about audience suitability. For the knowledge base, their doctrinal content is valuable regardless.

**Chunk-level tagging rule:** Do not inherit only the binder tags. Read the section headings and opening paragraph of each chunk. Assign doctrinal category tags wherever the concept appears — e.g. a chunk in binder 27 (Ādāb) that discusses the spiritual station of the dāʿī should also receive `dawat`, `hudud`, `wilaya`.

---

## Key File Locations

```
scripts/podcast/knowledge/
  _atom_schemas.py          ← extend with DoctrineBody (Step 2)
  extractor.py              ← Wave 1 scaffold; Kashkole bypasses this (standalone driver)
  librarian.py              ← implement doctrine shard merge (Step 4)
  augmenter.py              ← extend with topic-tag matching (Step 5)

content/knowledge-base/
  quran.jsonl               ← existing shard
  hadith.jsonl              ← existing shard
  doctrine.jsonl            ← new shard (Step 4 output)
  _index/
    doctrine-by-tag.json    ← new index (Step 4 output)

_workspace/source-library/extracted/wisdom/
  {NN}-{binder-slug}/
    {NN}-{chapter-slug}/
      bundle.yml
      _system/source/text/
        adapted-extract.en.md         ← PRIMARY SOURCE for ingestion
        adaptation-citations.jsonl    ← hadith atom source
        wisdom-challenger-report.md ← verdict filter (PASS/WARN = ingest, FAIL = skip)

_workspace/plan/
  wisdom-gate-report.md   ← lists the 18 FAIL chapters
  wisdom-podcast-scope.yaml

_workspace/wisdom-brief.md  ← full context document (read §18)
```

---

## Corpus State at Time of Writing (2026-05-26)

| Verdict | Count | Action |
|---|---|---|
| PASS | 9 | Ingest immediately |
| WARN | 66 | Ingest (flag `needs_review: true` on flagged atoms) |
| FAIL | 18 | Re-adapt + re-challenge first (Step 1) |
| Unchallenged (adapted only) | 26 | Run Phase 3 challenge first, then ingest |
| Stuck at translated | 3 | Resume Phase 2, then Phase 3, then ingest |
| **Total** | **122** | |

The 18 FAILs and 29 unchallenged chapters must complete their pipeline phase before ingestion. The 75 PASS+WARN chapters are ready now once the schema and driver exist.

---

## What "Done" Looks Like

After Steps 1–4 complete and the driver runs successfully:

```
content/knowledge-base/doctrine.jsonl   — 500–800 atoms (estimate)
content/knowledge-base/quran.jsonl      — enriched with Kashkole tafsir_notes
content/knowledge-base/hadith.jsonl     — enriched with Kashkole citations
content/knowledge-base/_index/doctrine-by-tag.json — topic index for fast lookup
```

The Augmenter (Step 5) is the payoff: future books touching Tawhīd, taʾwīl, jurisprudence, or cosmology will automatically receive relevant Kashkole passages as prior doctrinal context during authoring — without any manual curation.
